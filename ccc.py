#!/usr/bin/env python3
"""Cloudflight Coding Contest runner.

    python ccc.py new 2                  create levels/level2 (copies level1's solution)
    python ccc.py unpack ~/Downloads/level2.zip [2]
    python ccc.py run [2] [--force] [--only example] [--solution NAME]
    python ccc.py zip [2]                package source code for upload

Each level lives in levels/levelN/:
    problem.md    the level statement (pasted from the contest site)
    solution.py   defines solve(text) -> str | iterable of lines
    data/         the contest zip: inputs (CCC's in_*.txt, or *.in), the example's
                  expected output (out_*.txt / *.out) and the statement PDF
    out/          generated outputs to upload, named like the expected ones (out_*.txt)
    candidates/   one NAME.py per agent (see team.py); --solution NAME runs one,
                  writing to runs/NAME/ instead of out/
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import resource
import importlib.util
import re
import shutil
import subprocess
import sys
import time
import traceback
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LEVELS = ROOT / "levels"
TEMPLATE = LEVELS / "_template" / "solution.py"
SUBMISSIONS = ROOT / "submissions"


def level_dir(n: int) -> Path:
    return LEVELS / f"level{n}"


def existing_levels() -> list[int]:
    nums = []
    for p in LEVELS.glob("level*"):
        m = re.fullmatch(r"level(\d+)", p.name)
        if m and p.is_dir():
            nums.append(int(m.group(1)))
    return sorted(nums)


def resolve_level(n: int | None) -> int:
    if n is not None:
        return n
    levels = existing_levels()
    if not levels:
        sys.exit("No levels yet. Run: ./ccc new 1")
    return levels[-1]


# --- file naming: CCC zips hold in_level-1_1-small.txt / out_level-1_0-example.txt ---

def input_files(data: Path) -> list:
    """The level's inputs, example first: CCC's in_*.txt, or *.in."""
    return sorted(set(data.glob("in_*.txt")) | set(data.glob("*.in")), key=sort_key)


def output_name(inp: Path) -> str:
    """File name of the answer to an input (the file you upload)."""
    return "out_" + inp.name[3:] if inp.name.startswith("in_") else inp.with_suffix(".out").name


def expected_output(inp: Path) -> Path:
    """Where the contest's own answer would be (only the example has one)."""
    return inp.parent / output_name(inp)


PLACEHOLDER = "<!-- paste the statement here -->"


def pdf_text(pdf: Path) -> str:
    """Statement text from a level PDF, via macOS PDFKit (built in; no install)."""
    script = """
ObjC.import("PDFKit");
function run(argv) {
  var doc = $.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath(argv[0]));
  if (!doc || doc.isNil()) return "";
  var pages = [];
  for (var i = 0; i < doc.pageCount; i++) pages.push(ObjC.unwrap(doc.pageAtIndex(i).string) || "");
  return pages.join("\f");
}"""
    try:
        r = subprocess.run(["osascript", "-l", "JavaScript", "-e", script, str(pdf)],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired):
        return ""
    pages = []
    for i, page in enumerate(r.stdout.split("\f"), 1):
        out, prev = [], None
        for line in page.splitlines():
            line = line.strip()
            # drop the recurring footer/branding and repeated headings
            if not line or "#WeLoveSoftware" in line or "cloudflight.io/career" in line or line == prev:
                continue
            out.append(line)
            prev = line
        if out:
            pages.append(f"--- page {i} ---\n" + "\n".join(out))
    return "\n\n".join(pages)


def pdf_pages(pdf: Path, out_dir: Path) -> int:
    """Render every PDF page to out_dir/page-N.png (tables and figures keep their layout)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    script = """
ObjC.import("PDFKit"); ObjC.import("AppKit");
function run(argv) {
  var doc = $.PDFDocument.alloc.initWithURL($.NSURL.fileURLWithPath(argv[0]));
  if (!doc || doc.isNil()) return 0;
  for (var i = 0; i < doc.pageCount; i++) {
    var page = doc.pageAtIndex(i);
    var b = page.boundsForBox(0);
    var img = page.thumbnailOfSizeForBox($.NSMakeSize(b.size.width, b.size.height), 0);
    var rep = $.NSBitmapImageRep.imageRepWithData(img.TIFFRepresentation);
    rep.representationUsingTypeProperties(4, $({})).writeToFileAtomically(argv[1] + "/page-" + (i + 1) + ".png", true);
  }
  return doc.pageCount;
}"""
    try:
        r = subprocess.run(["osascript", "-l", "JavaScript", "-e", script, str(pdf), str(out_dir)],
                           capture_output=True, text=True, timeout=120)
        return int((r.stdout or "0").strip() or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return 0


def statement_from_pdf(d: Path) -> bool:
    """Fill problem.md from the level PDF if the statement wasn't written yet."""
    problem = d / "problem.md"
    if problem.exists() and PLACEHOLDER not in problem.read_text():
        return False
    pdfs = sorted((d / "data").glob("*.pdf"))
    if not pdfs:
        return False
    text = pdf_text(pdfs[0])
    if not text.strip():
        return False
    problem.write_text(f"# {d.name.replace('level', 'Level ')}\n\n"
                       f"Extracted automatically from data/{pdfs[0].name}. Tables and figures may have "
                       f"lost their layout: if something is unclear, look at the PDF itself.\n\n{text}\n")
    return True


# --- validator: judge validity instead of exact equality ---------------------------
# Many later levels accept any valid answer (e.g. "does not require an optimal solution").
# levels/levelN/validator.py then defines
#     check(input_text, output_text) -> (ok, message) or (ok, message, score)
#     SCORE = None | "min" | "max"      (which score is better, if there is one)
# It is only trusted after its self-test passed (validator.ok holds its mtime).

def load_validator(d: Path):
    f = d / "validator.py"
    if not f.exists():
        return None
    spec = importlib.util.spec_from_file_location(f"validator_{d.name}", f)
    mod = importlib.util.module_from_spec(spec)
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec.loader.exec_module(mod)
    return mod


def call_check(v, inp: str, out: str) -> tuple:
    """(ok, message, score) from a validator, whatever shape it returns."""
    r = v.check(inp, out)
    if isinstance(r, bool):
        return r, "", None
    r = tuple(r)
    return bool(r[0]), str(r[1]) if len(r) > 1 else "", r[2] if len(r) > 2 else None


def validator_ready(d: Path) -> bool:
    f, ok = d / "validator.py", d / "validator.ok"
    return f.exists() and ok.exists() and ok.read_text().strip() == str(f.stat().st_mtime_ns)


def _mutations(expected: str) -> list:
    """Clearly broken versions of a correct answer; a validator must reject them all."""
    out = [("an empty answer", "")]
    lines_ = [l for l in expected.rstrip("\n").split("\n")]
    if sum(1 for l in lines_ if l.strip()) >= 2:
        keep = list(lines_)
        while keep and not keep[-1].strip():
            keep.pop()
        out.append(("the answer without its last line", "\n".join(keep[:-1]) + "\n"))
    m = re.search(r"-?\d+", expected)
    if m:
        out.append(("the answer with a number replaced by 'x'", expected[:m.start()] + "x" + expected[m.end():]))
    return out


def validator_selftest(d: Path) -> tuple:
    """(ok, report lines). On success validator.ok is written, so the validator is used."""
    report, ok = [], True
    try:
        v = load_validator(d)
    except Exception as e:
        return False, [f"  validator.py doesn't load: {type(e).__name__}: {e}"]
    if v is None or not hasattr(v, "check"):
        return False, ["  validator.py with a check(input_text, output_text) function is missing"]
    examples = [p for p in input_files(d / "data") if expected_output(p).exists()]
    if not examples:
        return False, ["  no example with an expected output to test against"]
    for ex in examples:
        inp, exp = ex.read_text(), expected_output(ex).read_text()
        try:
            good, msg, score = call_check(v, inp, exp)
        except Exception as e:
            good, msg, score = False, f"crashed: {type(e).__name__}: {e}", None
        report.append(f"  {'ok  ' if good else 'FAIL'} accepts the official answer for {ex.name}"
                      + ("" if good else f"  ({msg})") + (f"  score={score}" if score is not None else ""))
        ok &= good
        for label, bad in _mutations(exp):
            try:
                rejected = not call_check(v, inp, bad)[0]
                why = ""
            except Exception as e:
                rejected, why = True, f" (by crashing: {type(e).__name__}; better return (False, reason))"
            report.append(f"  {'ok  ' if rejected else 'FAIL'} rejects {label}{why}")
            ok &= rejected
    flag = d / "validator.ok"
    if ok:
        flag.write_text(str((d / "validator.py").stat().st_mtime_ns))
    elif flag.exists():
        flag.unlink()
    return ok, report


def cmd_validate(args: argparse.Namespace) -> None:
    n = resolve_level(args.level)
    ok, report = validator_selftest(level_dir(n))
    print(f"Validator self-test for level {n}:")
    print("\n".join(report))
    print("READY: outputs are now judged by this validator." if ok else "NOT READY: fix validator.py.")
    sys.exit(0 if ok else 1)


# --- new -------------------------------------------------------------------

def cmd_new(args: argparse.Namespace) -> None:
    n = args.level if args.level is not None else (existing_levels() or [0])[-1] + 1
    d = level_dir(n)
    if (d / "solution.py").exists():
        sys.exit(f"{d.relative_to(ROOT)} already exists")
    (d / "data").mkdir(parents=True, exist_ok=True)
    (d / "candidates").mkdir(exist_ok=True)
    if not (d / "problem.md").exists():
        (d / "problem.md").write_text(f"# Level {n}\n\n{PLACEHOLDER}\n")
    prev = level_dir(n - 1) / "solution.py"
    src = prev if prev.exists() and not args.blank else TEMPLATE
    shutil.copy(src, d / "solution.py")
    print(f"Created {d.relative_to(ROOT)}/solution.py (from {src.relative_to(ROOT)})")


# --- unpack ----------------------------------------------------------------

def cmd_unpack(args: argparse.Namespace) -> None:
    zpath = Path(args.zip).expanduser()
    n = args.level
    if n is None:
        m = re.search(r"level[_ -]?(\d+)", zpath.name, re.I)
        if not m:
            sys.exit("Can't infer level from zip name; pass it explicitly")
        n = int(m.group(1))
    d = level_dir(n)
    if not (d / "solution.py").exists():
        cmd_new(argparse.Namespace(level=n, blank=False))
    data = d / "data"
    data.mkdir(parents=True, exist_ok=True)
    count = 0
    with zipfile.ZipFile(zpath) as zf:
        for info in zf.infolist():
            name = Path(info.filename).name  # flatten; ignores any path components
            if info.is_dir() or not name or name.startswith((".", "__MACOSX")):
                continue
            (data / name).write_bytes(zf.read(info))
            count += 1
    print(f"Extracted {count} files into {data.relative_to(ROOT)}")
    pdfs = sorted(data.glob("*.pdf"))
    if pdfs:
        pages = pdf_pages(pdfs[0], d / "pages")
        print(f"Rendered {pages} statement page(s) to {(d / 'pages').relative_to(ROOT)}/")
    if statement_from_pdf(d):
        print(f"Statement taken from the PDF into {(d / 'problem.md').relative_to(ROOT)}")


# --- run -------------------------------------------------------------------

def load_solution(path: Path):
    if not path.exists():
        sys.exit(f"Missing {path.relative_to(ROOT)}")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(f"solution_{path.stem}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def to_text(result) -> str:
    if result is None:
        return ""
    if isinstance(result, str):
        text = result
    else:
        text = "\n".join(str(x) for x in result)
    return text.rstrip("\n") + "\n"


def normalize(text: str) -> list[str]:
    return [line.rstrip() for line in text.strip().splitlines()]


def sort_key(p: Path):
    # example first, then numeric order (level1_2 before level1_10)
    nums = [int(x) for x in re.findall(r"\d+", p.stem)]
    return (0 if "example" in p.stem else 1, nums, p.name)


def _cpu() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime + r.ru_stime


def run_file(mod, path: Path) -> tuple[str | None, float]:
    """Runs solve() on one input; the time is CPU seconds, which is what the judge limits."""
    text = path.read_text()
    start = _cpu()
    try:
        out = to_text(mod.solve(text))
    except Exception:
        traceback.print_exc()
        return None, _cpu() - start
    return out, _cpu() - start


def time_limit() -> int:
    try:
        return int(json.loads((ROOT / "agents.json").read_text()).get("eval_timeout_s", 300))
    except (OSError, ValueError, AttributeError):
        return 300


def _slow(dt: float) -> str:
    lim = time_limit()
    return f"  TOO SLOW: over the judge's {lim} s CPU limit" if dt > lim else ""


def cmd_run(args: argparse.Namespace) -> None:
    # The judge runs PyPy; under CPython a big input takes many times longer and misleads.
    pypy = shutil.which("pypy3")
    if sys.implementation.name != "pypy" and pypy and not os.environ.get("CCC_CPYTHON"):
        print("  (running under PyPy, like the judge; set CCC_CPYTHON=1 to use this Python)", flush=True)
        os.execv(pypy, [pypy, "-u", str(Path(__file__).resolve()), *sys.argv[1:]])
    n = resolve_level(args.level)
    d = level_dir(n)
    inputs = input_files(d / "data")
    if args.only:
        inputs = [p for p in inputs if args.only in p.stem]
    if not inputs:
        sys.exit(f"No inputs (in_*.txt or *.in) in {(d / 'data').relative_to(ROOT)}")

    if args.solution:
        mod = load_solution(d / "candidates" / f"{args.solution}.py")
        out_dir = d / "runs" / args.solution
    else:
        mod = load_solution(d / "solution.py")
        out_dir = d / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    failed = False

    validator = load_validator(d) if validator_ready(d) else None
    if validator:
        print(f"  (judged by levels/level{n}/validator.py: any VALID answer counts)")
    for path in inputs:
        out, dt = run_file(mod, path)
        if out is None:
            print(f"  CRASH  {path.name}  ({dt:.2f}s)")
            failed = True
            if not args.force:
                break
            continue
        expected_path = expected_output(path)
        verdict = None
        if validator:
            try:
                verdict = call_check(validator, path.read_text(), out)
            except Exception as e:
                verdict = (False, f"validator crashed: {type(e).__name__}: {e}", None)
        if expected_path.exists() and validator and verdict[0]:
            same = normalize(out) == normalize(expected_path.read_text())
            print(f"  PASS   {path.name}  ({dt:.2f}s)  valid{'' if same else ', differs from the sample answer'}"
                  + (f"  score={verdict[2]}" if verdict[2] is not None else ""))
            continue
        if expected_path.exists() and validator:
            print(f"  FAIL   {path.name}  ({dt:.2f}s)  INVALID: {verdict[1]}")
            failed = True
            if not args.force:
                print("Stopping (use --force to run remaining inputs anyway)")
                break
            continue
        if expected_path.exists():
            expected = expected_path.read_text()
            if normalize(out) == normalize(expected):
                print(f"  PASS   {path.name}  ({dt:.2f}s)")
            else:
                print(f"  FAIL   {path.name}  ({dt:.2f}s)")
                diff = difflib.unified_diff(
                    normalize(expected), normalize(out), "expected", "got", lineterm="", n=1
                )
                for i, line in enumerate(diff):
                    if i >= 40:
                        print("    ... (diff truncated)")
                        break
                    print("    " + line)
                failed = True
                if not args.force:
                    print("Stopping (use --force to run remaining inputs anyway)")
                    break
            # don't write an output for files that already have an expected one
            continue
        (out_dir / output_name(path)).write_text(out)
        note = ""
        if verdict is not None:
            note = ("  VALID" + (f" score={verdict[2]}" if verdict[2] is not None else "")) if verdict[0] \
                else f"  INVALID: {verdict[1]}"
            failed |= not verdict[0]
        print(f"  WROTE  {path.name} -> {out_dir.relative_to(d)}/{output_name(path)}  ({dt:.2f}s CPU){note}"
              + _slow(dt))
        failed |= dt > time_limit()

    if failed:
        sys.exit(1)


# --- zip -------------------------------------------------------------------

def write_code_zip(n: int, target: Path) -> int:
    """Zip the code a level's solution needs (runner, solution, common/); returns the file count."""
    files = [ROOT / "ccc.py", level_dir(n) / "solution.py"]
    files += sorted((ROOT / "common").glob("*.py"))
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            zf.write(f, f.relative_to(ROOT))
    return len(files)


def cmd_zip(args: argparse.Namespace) -> None:
    n = resolve_level(args.level)
    SUBMISSIONS.mkdir(exist_ok=True)
    target = SUBMISSIONS / f"level{n}_code.zip"
    count = write_code_zip(n, target)
    print(f"Wrote {target.relative_to(ROOT)} ({count} files)")


def main() -> None:
    p = argparse.ArgumentParser(description="CCC helper")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("new", help="create a level folder")
    s.add_argument("level", type=int, nargs="?")
    s.add_argument("--blank", action="store_true", help="use template instead of previous level")
    s.set_defaults(func=cmd_new)

    s = sub.add_parser("unpack", help="extract a level zip into levels/levelN/data")
    s.add_argument("zip")
    s.add_argument("level", type=int, nargs="?")
    s.set_defaults(func=cmd_unpack)

    s = sub.add_parser("run", help="run solution on all inputs (example first)")
    s.add_argument("level", type=int, nargs="?")
    s.add_argument("--force", action="store_true", help="keep going after a failure")
    s.add_argument("--only", help="only inputs whose name contains this string")
    s.add_argument("--solution", help="run candidates/NAME.py instead of solution.py")
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("validate", help="self-test levels/levelN/validator.py")
    s.add_argument("level", type=int, nargs="?")
    s.set_defaults(func=cmd_validate)

    s = sub.add_parser("zip", help="package source code for upload")
    s.add_argument("level", type=int, nargs="?")
    s.set_defaults(func=cmd_zip)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
