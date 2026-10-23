"""Exact palindromic walks (large agent 2): SAT (satcyc.Model) for a walk of n configs s_1..s_n such that the
forward chain s_1..s_n from empty matter submits exactly on s_n and the backward chain s_n..s_1 submits exactly
on s_1.  Bouncing on the walk (repeating the turning config once) then costs n lines per copy.
Program = travel to s_1 (emitters off, toggled on at the end) + bounce, cut after `count` submissions; the
travel prefix can later be improved by run-in tools.
Usage: python3 l2_palsat.py <name> <i> <n> [tmo_ms] [span]   (prints the program on stdout or NONE/UNKNOWN)"""
import sys

import satcyc
import z3sat
from harness import LEVEL, cases, valid
from l2sim import Model as Fast

WAIT = '- - - - - -'


def palwalk(r, pat, n, tmo, span=None, nowait=False):
    md = satcyc.Model(r, pat, span)
    s = [md.config() for _ in range(n)]
    for t in range(n - 1):
        md.trans(s[t], s[t + 1])
    for chain in (list(range(n)), list(range(n - 1, -1, -1))):
        if nowait:
            chain = chain[1:]
        M = None
        Ss = []
        for t in chain:
            M, S = md.tick(s[t], M)
            Ss.append(S)
        md.add([Ss[-1]])
        for S in Ss[:-1]:
            md.add([-S])
    res = z3sat.solve(md.nv, md.cl, tmo)
    if res is None or res == 'unknown':
        return res
    return [md.decode(res, c) for c in s]


def travel(r, cfg0):
    """lines from the initial state so that config cfg0 (list of (offset, act)) fires on the last line."""
    need = [abs(o) + a for o, a in cfg0]
    m = max(max(need), 1)
    pre = [['-'] * 6 for _ in range(m)]
    for e, (o, a) in enumerate(cfg0):
        start = m - need[e]
        for k in range(abs(o)):
            pre[start + k][e] = 'F' if o > 0 else 'B'
        if a:
            pre[m - 1][e] = 'T'
    return [' '.join(l) for l in pre]


def assemble(r, pat, count, walk, nowait=False):
    """walk: decoded configs [(offset, act)]*6 per step."""
    moves = satcyc.lines_between(walk)  # n-1 lines s_k -> s_{k+1}
    back = satcyc.lines_between(walk[::-1])
    prog = travel(r, walk[0]) + moves
    fm = Fast(r, pat)
    k = 0
    while True:
        cf = fm.configs(prog)
        sub = fm.subs(cf)
        if len(sub) >= count:
            return prog[:sub[count - 1] + 1]
        if k > count + 2:
            return None
        prog += ([] if nowait else [WAIT]) + (back if k % 2 == 0 else moves)
        k += 1


def main():
    name, i, n = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
    tmo = int(sys.argv[4]) if len(sys.argv) > 4 else 60000
    span = int(sys.argv[5]) if len(sys.argv) > 5 else None
    nowait = len(sys.argv) > 6 and sys.argv[6] == '1'
    cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % name)).read_text()))
    r, pat, count = cs[i]
    res = palwalk(r, pat, n, tmo, span, nowait)
    if res is None:
        print('NONE')
        return
    if res == 'unknown':
        print('UNKNOWN')
        return
    prog = assemble(r, pat, count, res, nowait)
    if prog and valid(r, pat, count, prog):
        print('\n'.join(prog))
    else:
        print('WALK', res, file=sys.stderr)
        print('INVALID')


if __name__ == '__main__':
    main()
