"""Count>=2 patterns: seed copy 2 with the reversed copy-1 configurations (see rev_e.py), cut the reversed run
when copy 2 has reached given fractions of the pattern, and finish with a beam from that exact state.
Usage: python3 revbeam_e.py <input-name> <width> <fractions e.g. 0.6,0.8,0.9> [--w 100,1,0.3,0.5] [--only i,j]
       [--seeds 1] [--bin beam_e]"""
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from harness import HERE, LEVEL, cases, load_best, save_best, valid, run_job
from levels.level6.candidates.astra import board, ring, DIRS, NB
from resuf_e import opt, sub_ticks
from rev_e import candidates


def progress(r, pat, prog):
    """per line: number of pattern cells that are matter after the line (after a submission: 0)."""
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
    for line in prog:
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
        pm = sum(g[y][x] == 'M' for y, x in pcells)
        if pm == len(pcells) and not any(g[y][x] == 'M' for y, x in halo):
            for y, x in pcells:
                g[y][x] = 'O'
            pm = 0
        out.append(pm)
    return out, len(pcells)


def main():
    args = sys.argv[1:]
    only = opt(args, '--only', None)
    seeds = opt(args, '--seeds', '1').split(',')
    weights = opt(args, '--w', '100,1,0.3,0.5').split(',')
    binary = opt(args, '--bin', 'beam_e')
    name, width, fracs = args[0], args[1], [float(x) for x in args[2].split(',')]
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    before = sum(map(len, best))
    idxs = [int(x) for x in only.split(',')] if only else list(range(len(cs)))
    tmp = tempfile.mkdtemp()
    jobs = []
    for i in idxs:
        r, pat, count = cs[i]
        if count < 2:
            continue
        L = len(best[i])
        t1 = sub_ticks(r, pat, best[i])[0]
        cuts = set()
        for cand in candidates(best[i], t1):
            pr, NPc = progress(r, pat, cand)
            for f in fracs:
                for t in range(t1, len(cand)):
                    if pr[t] >= f * NPc:
                        cuts.add(tuple(cand[:t]))
                        break
        for pre in cuts:
            t = len(pre)
            if t >= L - 1:
                continue
            path = os.path.join(tmp, '%d_%d_%d.txt' % (i, t, len(jobs)))
            with open(path, 'w') as f:
                f.write('\n'.join(pre) + '\n')
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
