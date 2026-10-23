"""Segment re-optimisation with both junctions fixed: for submissions j < j2 = j+m of the best program, search
(retbeam) a path from (c_j, empty matter) that submits m copies, the last exactly at c_j2, in fewer than
t_j2 - t_j ticks; splice prog[:t_j] + path + prog[t_j2:]. j = -1 means the initial state (prefix).
Usage: python3 segopt.py <name> <width> [--only i,j] [--M 1,2,3] [--w ...] [--seed s] [--mincount 2]"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from harness import LEVEL, cases, load_best, save_best, valid
from retcyc import sim, run_retbeam


def main():
    args = sys.argv[1:]

    def opt(name, default):
        if name in args:
            k = args.index(name)
            v = args[k + 1]
            del args[k:k + 2]
            return v
        return default
    only = opt('--only', None)
    Ms = [int(x) for x in opt('--M', '1,2,3').split(',')]
    seed = opt('--seed', '1')
    weights = opt('--w', '100,1,0.3,0.5,1').split(',')
    mincount = int(opt('--mincount', '2'))
    os.environ['PERPID'] = '0'
    name, width = args[0], int(args[1])
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    idxs = [int(x) for x in only.split(',')] if only else [i for i in range(len(cs)) if cs[i][2] >= mincount]

    def job(i):
        r, pat, count = cs[i]
        gain = 0
        for m in Ms:
            j = -1
            while True:
                prog = best[i]
                subs = sim(r, pat, prog)
                pts = [(0, (tuple(e * r for e in range(6)), 0))] + [(t, (p, a)) for t, p, a in subs[:count]]
                # pts[k] = state after k submissions; segment k -> k+m
                k = j + 1
                if k + m >= len(pts):
                    break
                (ta, ca), (tb, cb) = pts[k], pts[k + m]
                if tb - ta - 1 < m:
                    j += 1
                    continue
                pid, path = run_retbeam(inp, i, width, seed, tb - ta - 1, m, [(ca[0], ca[1], cb[0], cb[1])], weights)
                if pid is not None:
                    cand = prog[:ta] + path + prog[tb:]
                    s2 = sim(r, pat, cand)
                    if len(s2) >= count:
                        cand = cand[:s2[count - 1][0]]
                    if len(cand) < len(prog) and valid(r, pat, count, cand):
                        gain += len(prog) - len(cand)
                        print('pattern %d: %d -> %d (segment %d+%d)' % (i, len(prog), len(cand), k, m), flush=True)
                        best[i] = cand
                        save_best(name, best)
                        continue  # retry the same segment start on the new program
                j += 1
        return i, gain

    tot = 0
    with ThreadPoolExecutor(int(os.environ.get('JOBS', '2'))) as ex:
        for i, g in ex.map(job, idxs):
            tot += g
            if g:
                print('pattern %d best %d (gain %d)' % (i, len(best[i]), g), flush=True)
    print('total gain', tot)


if __name__ == '__main__':
    main()
