"""Suffix re-optimisation with more cut types, seeds and weights (enormous agent).
Usage: python3 resuf_e.py <input-name> <width> <cuts> [--seeds 1,2] [--w 3,1,0.3,0.5] [--only i,j] [--top N]
cuts: 'dN' (N lines before the end), 'fX' (fraction X), 'sK' (K lines after the first submission tick; K may be
negative), 'tK' (exactly K lines kept).  Jobs are ordered by program length (longest first); --top keeps only the
N longest programs.  Every worker goes through harness.run_job (JOB_TIMEOUT)."""
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from harness import HERE, LEVEL, cases, load_best, save_best, valid, run_job
from levels.level6.candidates.astra import board, ring, DIRS, NB


def sub_ticks(r, pat, prog):
    """1-based line numbers on which a submission happens."""
    g = board(r)
    h, w = 2 * r + 1, 4 * r + 1
    rg = ring(r)
    m = len(rg)
    pcells = [(y, x) for y in range(h) for x in range(w) if pat[y][x] == 'M']
    pset = set(pcells)
    halo = {(y + dy, x + dx) for y, x in pcells for dy, dx in NB
            if (y + dy, x + dx) not in pset and 0 <= y + dy < h and 0 <= x + dx < w}
    pos = [0, r, 2 * r, 3 * r, 4 * r, 5 * r]
    act = [False] * 6
    out = []
    for t, line in enumerate(prog, 1):
        for e, ins in enumerate(line.split()):
            if ins == 'F':
                pos[e] = (pos[e] + 1) % m
            elif ins == 'B':
                pos[e] = (pos[e] - 1) % m
            elif ins == 'T':
                act[e] = not act[e]
        cnt = {}
        for e in range(6):
            if not act[e]:
                continue
            dy, dx = DIRS[e]
            y, x = rg[pos[e]]
            y += dy
            x += dx
            while 0 <= y < h and 0 <= x < w and g[y][x] in 'OM':
                cnt[(y, x)] = cnt.get((y, x), 0) + 1
                y += dy
                x += dx
        for (y, x), k in cnt.items():
            if k == 2:
                g[y][x] = 'M'
            elif k >= 3:
                g[y][x] = 'O'
        if all(g[y][x] == 'M' for y, x in pcells) and not any(g[y][x] == 'M' for y, x in halo):
            for y, x in pcells:
                g[y][x] = 'O'
            out.append(t)
    return out


def opt(args, flag, default):
    if flag in args:
        i = args.index(flag)
        v = args[i + 1]
        del args[i:i + 2]
        return v
    return default


def main():
    args = sys.argv[1:]
    only = opt(args, '--only', None)
    seeds = opt(args, '--seeds', '1').split(',')
    weights = opt(args, '--w', '3,1,0.3,0.5').split(',')
    top = int(opt(args, '--top', '0'))
    binary = opt(args, '--bin', 'beam_p')
    name, width, cuts = args[0], args[1], args[2].split(',')
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    before = sum(map(len, best))
    idxs = [int(x) for x in only.split(',')] if only else list(range(len(cs)))
    idxs.sort(key=lambda i: -len(best[i]))
    if top:
        idxs = idxs[:top]
    tmp = tempfile.mkdtemp()
    jobs = []
    for i in idxs:
        r, pat, count = cs[i]
        L = len(best[i])
        st = None
        ts = set()
        for c in cuts:
            if c[0] == 'd':
                t = L - int(c[1:])
            elif c[0] == 'f':
                t = int(L * float(c[1:]))
            elif c[0] == 't':
                t = int(c[1:])
            else:
                if count < 2:
                    continue
                if st is None:
                    st = sub_ticks(r, pat, best[i])
                t = st[0] + int(c[1:])
            if 0 < t < L - 1:
                ts.add(t)
        for t in sorted(ts):
            path = os.path.join(tmp, '%d_%d.txt' % (i, t))
            with open(path, 'w') as f:
                f.write('\n'.join(best[i][:t]) + '\n')
            for s in seeds:
                jobs.append((i, t, path, L, s))

    def job(arg):
        i, t, path, L, s = arg
        env = dict(os.environ, PREFIX=path)
        out = run_job([str(HERE / binary), str(inp), str(i), width, s] + weights + [str(L - t)],
                      capture_output=True, text=True, env=env).stdout.split('\n')
        return i, t, s, [l for l in out if l.strip() and l != 'NONE']

    print('%d jobs' % len(jobs), flush=True)
    with ThreadPoolExecutor(int(os.environ.get('JOBS', 3))) as ex:
        for i, t, s, prog in ex.map(job, jobs):
            r, pat, count = cs[i]
            if prog and len(prog) < len(best[i]) and valid(r, pat, count, prog):
                print('pattern %d (cut %d seed %s): %d -> %d' % (i, t, s, len(best[i]), len(prog)), flush=True)
                best[i] = prog
                save_best(name, best)
    save_best(name, best)
    print('%s: %d -> %d' % (name, before, sum(map(len, best))), flush=True)


if __name__ == '__main__':
    main()
