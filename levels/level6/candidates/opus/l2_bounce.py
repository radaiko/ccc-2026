"""Bounce search (large agent 2): after reaching config C_hi of the best program (a submission tick), walk the
best program's config path back and forth inside a window [lo, hi], turning around at every submission (and
optionally waiting one tick at a window end).  Moves are reversible, so every step is one legal line.
Tries every submission tick as hi and every lo below it; keeps the shortest valid program.
Usage: python3 l2_bounce.py <name> [--only i,j] [--save 1]"""
import sys

from harness import LEVEL, cases, load_best, save_best, valid
from l2sim import Model

WAIT = '- - - - - -'


def bounce(md, cfgs, prog, count, hi, lo, M0, ndone, maxlen, waitmode):
    """prog[:hi+1] already simulated: matter M0 after tick hi, ndone submissions. Walk from index hi."""
    out = list(prog[:hi + 1])
    M = M0
    cur = hi
    d = -1
    stuck = 0
    while ndone < count:
        if len(out) >= maxlen:
            return None
        nxt = cur + d
        if nxt < lo or nxt > hi:
            # window end without submission: wait (repeat config) once, then turn
            if waitmode and stuck == 0:
                out.append(WAIT)
                M, s = md.step(M, cfgs[cur])
                stuck = 1
                if s:
                    ndone += 1
                    d = -d
                    stuck = 0
                continue
            d = -d
            stuck += 1
            if stuck > 2:
                return None
            continue
        ln = md.line(cfgs[cur], cfgs[nxt])
        out.append(ln)
        cur = nxt
        M, s = md.step(M, cfgs[cur])
        if s:
            ndone += 1
            d = -d
            stuck = 0
    return out


def main():
    args = sys.argv[1:]
    only = None
    if '--only' in args:
        k = args.index('--only')
        only = [int(x) for x in args[k + 1].split(',')]
        del args[k:k + 2]
    name = args[0]
    cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % name)).read_text()))
    best = load_best(name)
    before = sum(map(len, best))
    for i in (only if only is not None else range(len(cs))):
        r, pat, count = cs[i]
        if count < 2:
            continue
        prog = best[i]
        md = Model(r, pat)
        cfgs = md.configs(prog)
        # matter after each tick
        Ms = []
        M = 0
        nd = 0
        subs = []
        for t, c in enumerate(cfgs):
            M, s = md.step(M, c)
            if s:
                nd += 1
                subs.append(t)
            Ms.append((M, nd))
        if len(subs) < count:
            continue
        bestc = None
        for hi in subs[:count - 1]:
            M0, nd0 = Ms[hi]
            for lo in range(0, hi):
                for wm in (0, 1):
                    lim = len(bestc) if bestc else len(prog)
                    c = bounce(md, cfgs, prog, count, hi, lo, M0, nd0, lim, wm)
                    if c and (bestc is None or len(c) < len(bestc)):
                        bestc = c
        if bestc and len(bestc) < len(prog) and valid(r, pat, count, bestc):
            print('pattern %d: %d -> %d' % (i, len(prog), len(bestc)), flush=True)
            best[i] = bestc
            save_best(name, best)
    save_best(name, best)
    print('%s: %d -> %d' % (name, before, sum(map(len, best))), flush=True)


if __name__ == '__main__':
    main()
