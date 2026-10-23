"""Prefix re-optimisation with a fixed junction: for submission j of the best program (tick t_j, config c_j),
search from the initial state a path that submits j+1 copies, the last exactly at c_j, in < t_j ticks
(retbeam with start = initial configuration, target = c_j), then splice path + prog[t_j:].
Usage: python3 retpre.py <name> <width> [--only i,j] [--J 4] [--w WH,W1,W2,WL,WR] [--seed s]"""
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
    J = int(opt('--J', '4'))
    seed = opt('--seed', '1')
    weights = opt('--w', '100,1,0.3,0.5,1').split(',')
    os.environ['PERPID'] = '0'
    name, width = args[0], int(args[1])
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    idxs = [int(x) for x in only.split(',')] if only else range(len(cs))

    def job(i):
        r, pat, count = cs[i]
        log = []
        prog = load_best(name)[i]
        if len(prog) < len(best[i]):
            best[i] = prog
        prog = best[i]
        subs = sim(r, pat, prog)
        init = (tuple(e * r for e in range(6)), 0)
        found = None
        for j in range(min(J, count)):
            t, pos, am = subs[j]
            pid, path = run_retbeam(inp, i, width, seed, t - 1, j + 1, [(init[0], init[1], pos, am)], weights)
            if pid is None:
                log.append('j%d t%d:-' % (j, t))
                continue
            cand = path + prog[t:]
            s2 = sim(r, pat, cand)
            if len(s2) >= count:
                cand = cand[:s2[count - 1][0]]
            log.append('j%d t%d:%d' % (j, t, len(path)))
            if valid(r, pat, count, cand) and (found is None or len(cand) < len(found)):
                found = cand
        return i, found, log

    with ThreadPoolExecutor(int(os.environ.get('JOBS', '2'))) as ex:
        for i, found, log in ex.map(job, idxs):
            r, pat, count = cs[i]
            if found and len(found) < len(best[i]):
                print('pattern %d: %d -> %d' % (i, len(best[i]), len(found)), flush=True)
                best[i] = found
                save_best(name, best)
            print('pattern %d best %d: %s' % (i, len(best[i]), ' '.join(log)), flush=True)


if __name__ == '__main__':
    main()
