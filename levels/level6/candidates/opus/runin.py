"""Run-in (first copy + cycle entry) optimisation for patterns whose repeat rate is already optimal (large agent).
Per pattern: f = first submission tick, rest = L - f, rate = rest/(count-1).
 1. exact SAT check whether ANY submission can happen at a tick < f (one query, OR over the submission vars);
    UNSAT => the run-in is optimal (given the rate) and the pattern is skipped.
 2. otherwise exact joint SAT (satcyc.prog_with_prefix): prefix of T0 < f ticks + K-tick cycle closing on the
    prefix's last config (K = rate, m = 1; non-integer rates: smallest m with integer K), T0 decreasing.
    count == 1: satcyc.prefix_to(T0, None).
Usage: python3 runin.py <name> <idx,..|@file> [timeout_ms]   (JOBS parallel, results saved via save_best)"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from harness import LEVEL, cases, load_best, save_best, valid
import satcyc
import z3sat
from resuffixL import sub_ticks


def any_sub_before(r, pat, T):
    md = satcyc.Model(r, pat)
    start = md.fixed_start()
    pre = [md.config() for _ in range(T)]
    prev, M, Ss = start, None, []
    for t in range(T):
        md.trans(prev, pre[t])
        M, S = md.tick(pre[t], M)
        Ss.append(S)
        prev = pre[t]
    md.add(Ss)
    return md


def joint(r, pat, count, K, m, T0, j, tmo):
    """prefix of T0 lines with >= j submissions, the last on line T0, + (K,m)-cycle closing on its last config."""
    md = satcyc.Model(r, pat)
    md.sym = False
    start = md.fixed_start()
    pre = [md.config() for _ in range(T0)]
    prev, M, Ss = start, None, []
    for t in range(T0):
        md.trans(prev, pre[t])
        M, S = md.tick(pre[t], M)
        Ss.append(S)
        prev = pre[t]
    md.add([Ss[-1]])
    if j > 1:
        satcyc.atleast(md, Ss[:-1], j - 1)
    cs = [md.config() for _ in range(K - 1)] + [pre[-1]]
    prev, M, S2s = pre[-1], None, []
    for t in range(K):
        md.trans(prev, cs[t])
        M, S2 = md.tick(cs[t], M)
        S2s.append(S2)
        prev = cs[t]
    md.add([S2s[-1]])
    satcyc.atleast(md, S2s[:-1], m - 1)
    res = z3sat.solve(md.nv, md.cl, tmo)
    if res is None or res == 'unknown':
        return res
    st = md.decode(res, start)
    pc = [md.decode(res, c) for c in pre]
    prog = satcyc.lines_between([st] + pc)
    cc = [md.decode(res, c) for c in cs]
    cl = satcyc.lines_between([pc[-1]] + cc)
    reps = (count + m - 1) // m + 1
    return satcyc.truncate(r, pat, count, prog + cl * reps)


def work(i, r, pat, count, prog, tmo):
    L = len(prog)
    st = sub_ticks(r, pat, prog)
    f = st[0]
    if f <= 1:
        return i, None, 'f=%d' % f
    md = any_sub_before(r, pat, f - 1)
    res = z3sat.solve(md.nv, md.cl, tmo)
    if res is None:
        return i, None, 'optimal first (f=%d)' % f
    if res == 'unknown':
        return i, None, 'check unknown (f=%d)' % f
    msgs = ['first<%d possible' % f]
    bestp = None
    if count == 1:
        T0 = f - 1
        while T0 >= 1:
            p = satcyc.prefix_to(r, pat, T0, None, tmo)
            if p is None or p == 'unknown':
                msgs.append('T0=%d %s' % (T0, 'UNSAT' if p is None else 'unknown'))
                if p == 'unknown':
                    break
            else:
                p = satcyc.truncate(r, pat, count, p)
                if p and (bestp is None or len(p) < len(bestp)):
                    bestp = p
            T0 -= 1
        return i, bestp, ' '.join(msgs)
    rest = L - f
    m = 1
    while (rest * m) % (count - 1) and m < 4:
        m += 1
    if (rest * m) % (count - 1):
        return i, None, 'rate %s/%d not handled' % (rest, count - 1)
    K0, m0 = rest * m // (count - 1), m
    JMAX = int(os.environ.get('JMAX', '2'))
    MMUL = int(os.environ.get('MMUL', '2'))
    for (j, K, m) in [(j, K0 * q, m0 * q) for q in range(1, MMUL + 1) for j in range(1, min(JMAX, count) + 1)]:
        # total = T0 + rest after the j-th copy; need T0 + (count - j) * K / m < L
        hi = f - 1 + (j - 1) * K // m
        for T0 in range(hi, 0, -1):
            cur = len(bestp) if bestp else L
            p = joint(r, pat, count, K, m, T0, j, tmo)
            if p == 'unknown':
                msgs.append('j=%d T0=%d unknown' % (j, T0))
                break
            if p is None:
                continue
            msgs.append('j=%d K=%d m=%d T0=%d len %d' % (j, K, m, T0, len(p)))
            if len(p) < cur:
                bestp = p
    return i, bestp, ' '.join(msgs)


def main():
    name, sel = sys.argv[1], sys.argv[2]
    tmo = int(sys.argv[3]) if len(sys.argv) > 3 else 60000
    if sel.startswith('@'):
        sel = open(sel[1:]).read().strip()
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    idxs = [int(x) for x in sel.split(',')]
    saved = 0
    with ThreadPoolExecutor(int(os.environ.get('JOBS', 2))) as ex:
        futs = [ex.submit(work, i, *cs[i], best[i], tmo) for i in idxs]
        for fu in futs:
            i, p, msg = fu.result()
            print('pattern %d: %s' % (i, msg), flush=True)
            r, pat, count = cs[i]
            if p and valid(r, pat, count, p):
                cur = load_best(name)[i]
                if len(p) < len(cur):
                    saved += len(cur) - len(p)
                    print('pattern %d: %d -> %d' % (i, len(cur), len(p)), flush=True)
                    b = load_best(name)
                    b[i] = p
                    save_best(name, b)
            elif p:
                print('INVALID', i, flush=True)
    print('saved', saved)


if __name__ == '__main__':
    main()
