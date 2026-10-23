"""Exact window re-solve (large agent 2): for a window of w ticks of the best program that ends at a
submission tick b, fix the config and matter at the window start (tick b-w) and the config at b (free for the
last submission), and ask SAT (satcyc.Model, Z3) for a path of T < w ticks that submits exactly on its last
tick (no earlier submission). Splice prog[:b-w] + path + prog[b:].
Usage: python3 l2_win.py <name> <wmax> [--only i,j] [--tmo ms] [--mincount 1] [--sub all|last]"""
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from harness import LEVEL, cases, load_best, save_best, valid
import satcyc
import z3sat
from l2sim import Model as Fast


def offsets(r, cfg):
    pos, act = cfg
    m = 6 * r
    return [(((pos[e] - e * r + 3 * r) % m) - 3 * r, bool(act >> e & 1)) for e in range(6)]


def solve_window(r, pat, Za, Ma_cells, Zb, T, tmo, slack=2):
    """Za/Zb: lists of (offset, active). Ma_cells: set of cell coords that are matter at the window start.
    Returns lines / None (unsat) / 'unknown'."""
    allo = [abs(o) for o, a in Za + (Zb or [])]
    span = min(max(max(allo) + slack, r), 3 * r - 1)
    if max(allo) > span:
        return 'unknown'
    md = satcyc.Model(r, pat, span)

    def fix(cfg, Z):
        for e in range(6):
            pos, act = cfg[e]
            o, a = Z[e]
            md.add([pos[md.offs.index(o)]])
            md.add([act if a else -act])
    st = md.config()
    fix(st, Za)
    M = []
    for c in md.cells:
        v = md.var()
        md.add([v] if c in Ma_cells else [-v])
        M.append(v)
    cs = [md.config() for _ in range(T)]
    if Zb is not None:
        fix(cs[-1], Zb)
    prev = st
    Ss = []
    for t in range(T):
        md.trans(prev, cs[t])
        M, S = md.tick(cs[t], M)
        Ss.append(S)
        prev = cs[t]
    md.add([Ss[-1]])
    for S in Ss[:-1]:
        md.add([-S])
    res = z3sat.solve(md.nv, md.cl, tmo)
    if res is None or res == 'unknown':
        return res
    return satcyc.lines_between([md.decode(res, st)] + [md.decode(res, c) for c in cs])


def matter_cells(fm, M):
    return {fm.cells[k] for k in range(len(fm.cells)) if M >> k & 1}


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
    tmo = int(opt('--tmo', '20000'))
    mincount = int(opt('--mincount', '1'))
    subsel = opt('--sub', 'all')
    name, wmax = args[0], int(args[1])
    cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % name)).read_text()))
    best = load_best(name)
    before = sum(map(len, best))
    idxs = [int(x) for x in only.split(',')] if only else list(range(len(cs)))
    idxs = [i for i in idxs if cs[i][2] >= mincount]
    idxs.sort(key=lambda i: -len(best[i]))

    def job(i):
        r, pat, count = cs[i]
        log = []
        k = 0
        while True:
            prog = load_best(name)[i]
            if len(prog) < len(best[i]):
                best[i] = prog
            prog = best[i]
            fm = Fast(r, pat)
            cfgs = fm.configs(prog)
            # matter after each tick (index t = after line t); -1 = start
            Ms = []
            M = 0
            subs = []
            for t, c in enumerate(cfgs):
                M, s = fm.step(M, c)
                Ms.append(M)
                if s:
                    subs.append(t)
            subs = subs[:count]
            order = list(range(len(subs)))
            if subsel == 'last':
                order = order[-1:]
            changed = False
            for j in order[::-1]:
                b = subs[j]
                lo = subs[j - 1] if j > 0 else -1
                a = max(lo, b - wmax)
                wlen = b - a
                if wlen < 2:
                    continue
                Za = offsets(r, cfgs[a]) if a >= 0 else [(0, False)] * 6
                Zb = None if j == count - 1 else offsets(r, cfgs[b])
                Ma = matter_cells(fm, Ms[a]) if a >= 0 else set()
                if a == lo and a >= 0:
                    Ma = matter_cells(fm, Ms[a])
                t0 = time.time()
                res = solve_window(r, pat, Za, Ma, Zb, wlen - 1, tmo)
                dt = time.time() - t0
                if isinstance(res, list):
                    # try even shorter
                    T = wlen - 1
                    while T > 1:
                        r2 = solve_window(r, pat, Za, Ma, Zb, T - 1, tmo)
                        if not isinstance(r2, list):
                            break
                        res = r2
                        T -= 1
                    head = prog[:a + 1]
                    tail = prog[b + 1:] if Zb is not None else []
                    cand = head + res + tail
                    if valid(r, pat, count, cand) and len(cand) < len(prog):
                        log.append('sub%d w%d: -%d' % (j, wlen, len(prog) - len(cand)))
                        best[i] = cand
                        save_best(name, best)
                        changed = True
                        break
                    else:
                        log.append('sub%d w%d: SAT but invalid splice' % (j, wlen))
                else:
                    log.append('sub%d w%d %s %.1fs' % (j, wlen, 'U' if res is None else '?', dt))
            k += 1
            if not changed or k > 20:
                break
        return i, log

    with ThreadPoolExecutor(int(os.environ.get('JOBS', '2'))) as ex:
        for i, log in ex.map(job, idxs):
            print('pattern %d (%d): %s' % (i, len(best[i]), ' '.join(log)), flush=True)
    save_best(name, best)
    print('%s: %d -> %d' % (name, before, sum(map(len, best))), flush=True)


if __name__ == '__main__':
    main()
