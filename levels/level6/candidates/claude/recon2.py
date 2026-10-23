"""Disambiguate reconstructed readings using every historical version of an output file.

For each pattern index: candidates = readings (R, P) from the latest version (first submission
of P = a connected component, last tick submits). A reading survives if every distinct historical
program for that index submits >= 1; count = min over versions of the submissions.
"""
import sys, glob, os
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recon

MASKS = {}
def masks(R):
    if R not in MASKS:
        g = recon.geom(R)
        MASKS[R] = [[sum(1 << k for k in g.ray[i][t]) for t in range(6)] for i in range(len(g.perimeter))]
    return MASKS[R]

def bsim(R, prog, P, H):
    g = recon.geom(R)
    ray = masks(R)
    plen = len(g.perimeter)
    idx = [t * g.edge for t in range(6)]
    act = [False] * 6
    grid = 0
    subs = 0
    for line in prog:
        for t in range(6):
            c = line[t]
            if c == 'F':
                idx[t] = (idx[t] + 1) % plen
            elif c == 'B':
                idx[t] = (idx[t] - 1) % plen
            elif c == 'T':
                act[t] = not act[t]
        s0 = s1 = s2 = 0
        for t in range(6):
            if act[t]:
                L = ray[idx[t]][t]
                s2 |= s1 & L
                s1 |= s0 & L
                s0 |= L
        grid = (grid | (s1 & ~s2)) & ~s2
        if grid & P == P and not grid & H:
            grid &= ~P
            subs += 1
    return subs

def tomask(C):
    return sum(1 << k for k in C)

def work(args):
    name, pi, prog, versions = args
    cs = recon.candidates(prog, recon.RADII[name])
    out = []
    for R, C, n, t in cs:
        g = recon.geom(R)
        P = tomask(C)
        H = tomask(recon.halo_of(g, C))
        mn = n
        for v in versions:
            s = bsim(R, v, P, H)
            mn = min(mn, s)
            if mn == 0:
                break
        out.append((R, sorted(C), n, t, mn))
    return pi, out

if __name__ == '__main__':
    name = sys.argv[1]
    here = os.path.dirname(os.path.abspath(__file__))
    files = sorted(glob.glob(os.path.join(here, 'hist', name + '.*.txt')), key=lambda f: int(f.split('.')[-2]))
    latest = recon.parse_out(open(sys.argv[2]).read())
    vers = [recon.parse_out(open(f).read()) for f in files]
    vers = [v for v in vers if len(v) == len(latest)]
    jobs = []
    for pi, prog in enumerate(latest):
        uniq = {tuple(map(tuple, v[pi])) for v in vers} - {tuple(map(tuple, prog))}
        jobs.append((name, pi, prog, [list(map(list, u)) for u in uniq]))
    import json
    res = {}
    with Pool(4) as pool:
        for pi, out in pool.imap_unordered(work, jobs):
            res[pi] = out
    json.dump({str(k): v for k, v in sorted(res.items())}, open(os.path.join(here, 'cands_%s.json' % name), 'w'))
    amb = 0
    for pi in range(len(latest)):
        surv = [(R, len(C), n, mn) for R, C, n, t, mn in res[pi] if mn > 0]
        if len(surv) != 1:
            amb += 1
            print(pi, 'nver', len(jobs[pi][3]), surv)
    print(name, 'ambiguous', amb, 'of', len(latest))
