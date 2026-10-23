"""Coverage-model SAT for cycles (large agent 2).
Restriction to CLEAN configurations (no halo cell hit exactly twice, no pattern cell hit 3+ times): then the
matter painted is order independent and a copy is complete as soon as the union of the 2-hit cells of the fired
configurations covers P.  Much smaller than the matter model of satcyc (no matter variables per tick).
  pal n      : walk s_1..s_n covering P (bounce with one wait per turn: n lines per copy)
  cyc K m    : closed walk of K configs split into m arcs (sizes as equal as possible), each arc covers P
               (K/m lines per copy).
Assembly: run-in = beamL with TARGET = an arc's last config and CNTOVR=1 (first copy ends exactly there),
then the cycle from the next arc, cut after count submissions.
Usage: python3 l2_covsat.py <name> <i> pal <n> [tmo] | cyc <K> <m> [tmo]"""
import itertools
import os
import sys

import satcyc
import z3sat
from harness import HERE, LEVEL, cases, valid, run_job
from l2sim import Model as Fast

WAIT = '- - - - - -'


def clean_cover_model(r, pat, K, closed, arcs, span=None, pal=False):
    """arcs: list of index lists (config indices) that must each cover P."""
    md = satcyc.Model(r, pat, span)
    np_ = len(md.P)
    cs = [md.config() for _ in range(K)]
    for t in range(K - 1):
        md.trans(cs[t], cs[t + 1])
    if closed:
        md.trans(cs[K - 1], cs[0])
    two = []  # two[t][c] for P cells
    for t in range(K):
        F = md.fire(cs[t])
        row = []
        for ci in range(len(md.cells)):
            ins = [F[e][md.cellline[ci][e]] for e in range(6)]
            ins = [x for x in ins if x is not None]
            if ci < np_:
                for tr in itertools.combinations(ins, 3):
                    md.add([-tr[0], -tr[1], -tr[2]])
                if len(ins) < 2:
                    row.append(None)
                    continue
                v = md.var()
                for x in ins:
                    md.add([-v] + [y for y in ins if y is not x])
                row.append(v)
            else:
                for a, b in itertools.combinations(ins, 2):
                    md.add([-a, -b] + [y for y in ins if y is not a and y is not b])
        two.append(row)
    for arc in arcs:
        for ci in range(np_):
            md.add([two[t][ci] for t in arc if two[t][ci] is not None])
    return md, cs


def arcs_for(K, m):
    out = []
    a = 0
    for j in range(m):
        sz = K // m + (1 if j < K % m else 0)
        out.append(list(range(a, a + sz)))
        a += sz
    return out


def solve_cyc(r, pat, K, m, tmo, span=None):
    md, cs = clean_cover_model(r, pat, K, True, arcs_for(K, m), span)
    res = z3sat.solve(md.nv, md.cl, tmo)
    if res is None or res == 'unknown':
        return res
    return [md.decode(res, c) for c in cs]


def solve_pal(r, pat, n, tmo, span=None):
    md, cs = clean_cover_model(r, pat, n, False, [list(range(n))], span)
    res = z3sat.solve(md.nv, md.cl, tmo)
    if res is None or res == 'unknown':
        return res
    return [md.decode(res, c) for c in cs]


def ringcfg(r, cfg):
    m = 6 * r
    pos = [(e * r + o) % m for e, (o, a) in enumerate(cfg)]
    am = sum(1 << e for e, (o, a) in enumerate(cfg) if a)
    return pos, am


def travel(r, cfg0):
    need = [abs(o) + a for o, a in cfg0]
    mm = max(max(need), 1)
    pre = [['-'] * 6 for _ in range(mm)]
    for e, (o, a) in enumerate(cfg0):
        start = mm - need[e]
        for k in range(abs(o)):
            pre[start + k][e] = 'F' if o > 0 else 'B'
        if a:
            pre[mm - 1][e] = 'T'
    return [' '.join(l) for l in pre]


def finish(r, pat, count, prefix, seq_lines):
    """prefix + repeated seq_lines until count submissions; truncated."""
    fm = Fast(r, pat)
    prog = list(prefix)
    for k in range(count + 3):
        sub = fm.subs(fm.configs(prog))
        if len(sub) >= count:
            return prog[:sub[count - 1] + 1]
        prog += seq_lines
    sub = fm.subs(fm.configs(prog))
    return prog[:sub[count - 1] + 1] if len(sub) >= count else None


def runin(inp, i, r, tgt_cfg, limit, width='2000', weights=('100', '1', '0.3', '0.5')):
    pos, am = ringcfg(r, tgt_cfg)
    env = dict(os.environ, CNTOVR='1', TARGET='%s,%d' % (','.join(map(str, pos)), am))
    env.setdefault('WTM', '1')
    env.pop('PREFIX', None)
    if limit < 2:
        return None
    out = run_job([str(HERE / 'beamL'), str(inp), str(i), width, '1'] + list(weights) + [str(limit)],
                  capture_output=True, text=True, env=env).stdout.split('\n')
    pre = [l for l in out if l.strip() and l != 'NONE']
    return pre or None


def programs_cyc(inp, i, r, pat, count, cyc, m, limit, width='2000'):
    """cyc: decoded configs of a closed walk with m arcs; yields candidate programs."""
    K = len(cyc)
    arcs = arcs_for(K, m)
    out = []
    for j, arc in enumerate(arcs):
        end = arc[-1]
        rot = cyc[end + 1:] + cyc[:end + 1]  # configs after the arc end, cyclically, ending at the arc end
        lines = satcyc.lines_between([cyc[end]] + rot)
        trav = travel(r, cyc[end])
        # naive: travel to the arc start - simpler: travel to cyc[end] firing, then cycle
        c = finish(r, pat, count, trav, lines)
        if c:
            out.append(c)
        pre = runin(inp, i, r, cyc[end], limit, width)
        if pre:
            c = finish(r, pat, count, pre, lines)
            if c:
                out.append(c)
    return [c for c in out if valid(r, pat, count, c)]


def programs_pal(inp, i, r, pat, count, walk, limit, width='2000'):
    fwd = satcyc.lines_between(walk)
    back = satcyc.lines_between(walk[::-1])
    out = []
    for at_end in (True, False):
        tgt = walk[-1] if at_end else walk[0]
        seq = [WAIT] + (back if at_end else fwd) + [WAIT] + (fwd if at_end else back)
        for pre in (travel(r, walk[0]) + fwd if at_end else None, runin(inp, i, r, tgt, limit, width)):
            if pre:
                c = finish(r, pat, count, pre, seq)
                if c:
                    out.append(c)
    return [c for c in out if valid(r, pat, count, c)]


def main():
    name, i, mode = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    r, pat, count = list(cases(inp.read_text()))[i]
    from harness import load_best
    L = len(load_best(name)[i])
    if mode == 'pal':
        n = int(sys.argv[4])
        tmo = int(sys.argv[5]) if len(sys.argv) > 5 else 60000
        w = solve_pal(r, pat, n, tmo)
        print('pal', n, 'UNSAT' if w is None else 'UNKNOWN' if w == 'unknown' else 'SAT', file=sys.stderr)
        if isinstance(w, list):
            ps = programs_pal(inp, i, r, pat, count, w, L - 1)
            print('programs', sorted(map(len, ps)), 'best', L, file=sys.stderr)
    else:
        K, m = int(sys.argv[4]), int(sys.argv[5])
        tmo = int(sys.argv[6]) if len(sys.argv) > 6 else 60000
        w = solve_cyc(r, pat, K, m, tmo)
        print('cyc', K, m, 'UNSAT' if w is None else 'UNKNOWN' if w == 'unknown' else 'SAT', file=sys.stderr)
        if isinstance(w, list):
            ps = programs_cyc(inp, i, r, pat, count, w, m, L - 1)
            print('programs', sorted(map(len, ps)), 'best', L, file=sys.stderr)


if __name__ == '__main__':
    main()
