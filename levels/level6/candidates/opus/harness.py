"""Run the C++ optimizer over patterns in parallel, verify, keep the best per pattern.

Best programs are stored in runs/opus/best_<input>.json (list of programs, one per pattern)
and written as upload files to runs/opus/out_level-6_<input>.txt.
Usage: python3 harness.py <input-name> <width> [seed] [extra beam args...] [--only i,j,..]
"""
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
LEVEL = HERE.parents[1]
sys.path.insert(0, str(LEVEL.parents[1]))
from levels.level6.candidates.astra import cases, simulate  # noqa: E402

RUNS = LEVEL / 'runs' / 'opus'
# Hard wall-clock limit per worker process (seconds); a job that exceeds it is killed and skipped.
JOB_TIMEOUT = float(os.environ.get('JOB_TIMEOUT', '600'))


def run_job(cmd, **kw):
    """subprocess.run with the job timeout; returns empty stdout when the job was killed."""
    limit = kw.pop('timeout', JOB_TIMEOUT)
    try:
        return subprocess.run(cmd, timeout=limit, **kw)
    except subprocess.TimeoutExpired:
        print('TIMEOUT (killed after %.0fs): %s' % (limit, ' '.join(map(str, cmd[:4]))), flush=True)
        return subprocess.CompletedProcess(cmd, -9, stdout='', stderr='')
RUNS.mkdir(parents=True, exist_ok=True)


def load_best(name):
    """Own best, merged with every other run directory (other agents keep improving)."""
    path = RUNS / ('best_%s.json' % name)
    best = json.loads(path.read_text()) if path.exists() else None
    # output2/ = results pushed to the branch by the other team's agent (pulled into the commit worktree)
    extra = [LEVEL / 'output', LEVEL / 'output2', Path('/private/tmp/claude-501/-Users-laurenzwurdinger-Documents-dev-CodingContest/5e9e1394-2f05-4762-ad31-a81358130714/scratchpad/wt/levels/level6/output2')]
    for d in sorted((LEVEL / 'runs').iterdir()) + extra:
        f = d / ('out_level-6_%s.txt' % name)
        if d == RUNS or not f.exists():
            continue
        progs = [b.splitlines() for b in re.split(r'\n\s*\n', f.read_text().strip())]
        if best is None:
            best = progs
        elif len(progs) == len(best):
            external = d.name == 'output2'
            cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % name)).read_text())) if external else None
            for i, p in enumerate(progs):
                if len(p) < len(best[i]):
                    # programs from the other team's folder are simulated before they are trusted
                    if external and not valid(*cs[i], p):
                        continue
                    best[i] = p
    return best


def save_best(name, best):
    """Merge with the file on disk (other harness processes may have saved meanwhile)."""
    import fcntl
    with open(RUNS / ('.lock_%s' % name), 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        path = RUNS / ('best_%s.json' % name)
        if path.exists():
            disk = json.loads(path.read_text())
            for i, p in enumerate(disk):
                if len(p) < len(best[i]):
                    best[i] = p
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(best))
        tmp.replace(path)
    (RUNS / ('out_level-6_%s.txt' % name)).write_text('\n\n'.join('\n'.join(p) for p in best) + '\n')


def valid(r, pat, count, prog):
    return simulate(r, pat, [l.split() for l in prog]) >= count


def main():
    args = sys.argv[1:]
    only = None
    verbose = '-v' in args
    if verbose:
        args.remove('-v')
    binary = 'beam'
    if '--bin' in args:
        i = args.index('--bin')
        binary = args[i + 1]
        del args[i:i + 2]
    if '--only' in args:
        i = args.index('--only')
        only = [int(x) for x in args[i + 1].split(',')]
        del args[i:i + 2]
    name, width = args[0], args[1]
    seed = args[2] if len(args) > 2 else '1'
    extra = args[3:]
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    before = sum(map(len, best))
    idxs = only if only is not None else range(len(cs))

    def job(i):
        bound = [str(len(best[i]))] if binary == 'cycle' else []
        out = run_job([str(HERE / binary), str(inp), str(i), width, seed] + extra + bound,
                             capture_output=True, text=True).stdout.split('\n')
        prog = [l for l in out if l.strip() and l != 'NONE']
        return i, prog

    improved = 0
    with ThreadPoolExecutor(int(os.environ.get('JOBS', os.cpu_count()))) as ex:
        for i, prog in ex.map(job, idxs):
            r, pat, count = cs[i]
            if not prog:
                continue
            if not valid(r, pat, count, prog):
                print('INVALID', i, len(prog), flush=True)
                continue
            if verbose:
                print('pattern %d: best %d beam %d' % (i, len(best[i]), len(prog)), flush=True)
            if len(prog) < len(best[i]):
                improved += len(best[i]) - len(prog)
                print('pattern %d: %d -> %d' % (i, len(best[i]), len(prog)), flush=True)
                best[i] = prog
                save_best(name, best)
    save_best(name, best)
    print('%s: %d -> %d (saved %d)' % (name, before, sum(map(len, best)), improved))


if __name__ == '__main__':
    main()
