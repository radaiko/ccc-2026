"""Suffix re-optimisation with configurable binary/weights (large agent).
Usage: python3 resuffixL.py <input-name> <width> <cuts> [--only i,j] [--bin beamL] [--w 100,1,0.3,0.5] [--seed S]
cuts: comma list of 'dN' (N lines before end), 'fX' (fraction), 'sN' (N lines before EVERY submission tick),
'aN' (N lines after every submission tick, i.e. re-plan from the copy boundary)."""
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from harness import HERE, LEVEL, cases, load_best, save_best, valid, run_job
sys.path.insert(0, str(LEVEL.parents[1]))
from levels.level6.candidates.astra import board, ring, DIRS, NB  # noqa: E402


def sub_ticks(r, pat, prog):
    g = board(r); h, w = 2 * r + 1, 4 * r + 1; rg = ring(r); m = len(rg)
    pc = [(y, x) for y in range(h) for x in range(w) if pat[y][x] == 'M']; ps = set(pc)
    halo = {(y + dy, x + dx) for y, x in pc for dy, dx in NB if (y + dy, x + dx) not in ps
            and 0 <= y + dy < h and 0 <= x + dx < w}
    pos = [0, r, 2 * r, 3 * r, 4 * r, 5 * r]; act = [False] * 6; ticks = []
    for t, line in enumerate(prog):
        line = line.split()
        for e, ins in enumerate(line):
            if ins == 'F': pos[e] = (pos[e] + 1) % m
            elif ins == 'B': pos[e] = (pos[e] - 1) % m
            elif ins == 'T': act[e] = not act[e]
        cnt = {}
        for e in range(6):
            if not act[e]: continue
            dy, dx = DIRS[e]; y, x = rg[pos[e]]; y += dy; x += dx
            while 0 <= y < h and 0 <= x < w and g[y][x] in 'OM':
                cnt[(y, x)] = cnt.get((y, x), 0) + 1; y += dy; x += dx
        for (y, x), k in cnt.items():
            if k == 2: g[y][x] = 'M'
            elif k >= 3: g[y][x] = 'O'
        if all(g[y][x] == 'M' for y, x in pc) and not any(g[y][x] == 'M' for y, x in halo):
            for y, x in pc: g[y][x] = 'O'
            ticks.append(t + 1)
    return ticks


def opt(args, flag, default):
    if flag in args:
        i = args.index(flag); v = args[i + 1]; del args[i:i + 2]; return v
    return default


def main():
    args = sys.argv[1:]
    only = opt(args, '--only', None)
    only = [int(x) for x in only.split(',')] if only else None
    binary = opt(args, '--bin', 'beamL')
    weights = opt(args, '--w', '100,1,0.3,0.5').split(',')
    seed = opt(args, '--seed', '1')
    name, width, cuts = args[0], args[1], args[2].split(',')
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    before = sum(map(len, best))
    tmp = tempfile.mkdtemp()
    jobs = []
    for i in (only if only is not None else range(len(cs))):
        L = len(best[i])
        r, pat, count = cs[i]
        st = sub_ticks(r, pat, best[i]) if any(c[0] in 'sa' for c in cuts) else []
        ts = set()
        for c in cuts:
            if c[0] == 'd': ts.add(L - int(c[1:]))
            elif c[0] == 'f': ts.add(int(L * float(c[1:])))
            elif c[0] == 's': ts.update(t - int(c[1:]) for t in st[:count])
            elif c[0] == 'a': ts.update(t + int(c[1:]) for t in st[:count - 1])
        for t in sorted(ts):
            if not 0 < t < L - 1: continue
            path = os.path.join(tmp, '%d_%d.txt' % (i, t))
            with open(path, 'w') as f:
                f.write('\n'.join(best[i][:t]) + '\n')
            jobs.append((i, t, path, L))
    # biggest programs first
    jobs.sort(key=lambda j: -(j[3] - j[1]))
    print('%d jobs' % len(jobs), flush=True)

    def job(arg):
        i, t, path, L = arg
        env = dict(os.environ, PREFIX=path)
        out = run_job([str(HERE / binary), str(inp), str(i), width, seed] + weights + [str(L - t - 1)],
                      capture_output=True, text=True, env=env).stdout.split('\n')
        return i, t, [l for l in out if l.strip() and l != 'NONE']

    with ThreadPoolExecutor(int(os.environ.get('JOBS', 3))) as ex:
        for i, t, prog in ex.map(job, jobs):
            r, pat, count = cs[i]
            if prog and len(prog) < len(best[i]) and valid(r, pat, count, prog):
                print('pattern %d (cut %d): %d -> %d' % (i, t, len(best[i]), len(prog)), flush=True)
                best[i] = prog
                save_best(name, best)
    save_best(name, best)
    print('%s: %d -> %d' % (name, before, sum(map(len, best))))


if __name__ == '__main__':
    main()
