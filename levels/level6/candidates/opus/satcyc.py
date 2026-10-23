"""Exact k-tick cycle search (and prefix + cycle programs) via SAT (Z3's SAT core through ctypes).

Model: each emitter has a position offset o in -R..R around its corner (positions further away never fire,
any trajectory can be clamped to this range) and an active bit. Per tick an emitter either stays, moves +-1,
or toggles (then its position is unchanged). Only cells of P and its halo H are modelled. Per cell and tick:
G2 = >=2 hits, G3 = >=3 hits; pre-submission matter N = !G3 & (Mprev | G2); S = all P in N and no H in N;
M = N & !S on P, M = N on H. Everything is exact simulation, so programs are valid by construction
(they are re-verified by simulation anyway).

Usage:
  satcyc.py <input> <idx> cycle <k>                 -> pure k-cycle from empty matter (prints SAT/UNSAT)
  satcyc.py <input> <idx> prog <k> <T0max> [T0min]  -> shortest prefix T0 (first submission at T0, ending in
                                                       the cycle start config) + k-cycle; prints the program
"""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from levels.level6.candidates.astra import cases, board, ring, DIRS, NB, simulate  # noqa: E402
import z3sat  # noqa: E402


class Model:
    def __init__(self, r, pat):
        self.r = r
        self.nv = 0
        self.cl = []
        g = board(r)
        h, w = 2 * r + 1, 4 * r + 1
        rg = ring(r)
        m = len(rg)
        self.m = m
        pc = [(y, x) for y in range(h) for x in range(w) if pat[y][x] == 'M']
        ps = set(pc)
        halo = set()
        for y, x in pc:
            for dy, dx in NB:
                q = (y + dy, x + dx)
                if q not in ps and 0 <= q[0] < h and 0 <= q[1] < w and g[q[0]][q[1]] == 'O':
                    halo.add(q)
        self.P = pc
        self.H = sorted(halo)
        self.cells = self.P + self.H
        idx = {c: i for i, c in enumerate(self.cells)}
        # line of emitter e at offset o: which modelled cells it hits
        self.offs = list(range(-r, r + 1))
        self.hit = [[[] for _ in self.offs] for _ in range(6)]  # hit[e][oi] = cell indices
        self.cellline = [[None] * 6 for _ in self.cells]  # cellline[c][e] = oi
        for e in range(6):
            for oi, o in enumerate(self.offs):
                y, x = rg[(e * r + o) % m]
                dy, dx = DIRS[e]
                y += dy
                x += dx
                while 0 <= y < h and 0 <= x < w and g[y][x] in 'OM':
                    if (y, x) in idx:
                        ci = idx[(y, x)]
                        self.hit[e][oi].append(ci)
                        assert self.cellline[ci][e] is None
                        self.cellline[ci][e] = oi
                    y += dy
                    x += dx
        for ci in range(len(self.cells)):
            assert all(v is not None for v in self.cellline[ci]), 'cell not on a line'

    def var(self):
        self.nv += 1
        return self.nv

    def add(self, c):
        self.cl.append(c)

    def amo(self, xs):
        # sequential counter
        n = len(xs)
        if n <= 1:
            return
        s = [self.var() for _ in range(n - 1)]
        self.add([-xs[0], s[0]])
        for i in range(1, n - 1):
            self.add([-xs[i], s[i]])
            self.add([-s[i - 1], s[i]])
            self.add([-xs[i], -s[i - 1]])
        self.add([-xs[n - 1], -s[n - 2]])

    def config(self):
        """Fresh config variables: per emitter (pos one-hot list, act var)."""
        cfg = []
        for e in range(6):
            pos = [self.var() for _ in self.offs]
            self.add(pos[:])
            self.amo(pos)
            act = self.var()
            cfg.append((pos, act))
        return cfg

    def fixed_start(self):
        cfg = self.config()
        r = self.r
        for e in range(6):
            pos, act = cfg[e]
            self.add([pos[self.offs.index(0)]])
            self.add([-act])
        return cfg

    def trans(self, a, b):
        n = len(self.offs)
        for e in range(6):
            pa, aa = a[e]
            pb, ab = b[e]
            for i in range(n):
                self.add([-pb[i]] + [pa[j] for j in (i - 1, i, i + 1) if 0 <= j < n])
                # toggle -> same position
                self.add([-ab, aa, -pa[i], pb[i]])
                self.add([ab, -aa, -pa[i], pb[i]])

    def fire(self, cfg):
        """F[e][oi] var (active and at offset oi); for non-firing offsets None."""
        F = []
        for e in range(6):
            pos, act = cfg[e]
            row = []
            for oi in range(len(self.offs)):
                if not self.hit[e][oi]:
                    row.append(None)
                    continue
                f = self.var()
                self.add([-f, act])
                self.add([-f, pos[oi]])
                self.add([f, -act, -pos[oi]])
                row.append(f)
            F.append(row)
        return F

    def tick(self, cfg, Mprev):
        """Returns (M list, S var). Mprev: list of vars or None (= empty matter)."""
        F = self.fire(cfg)
        N = []
        for ci in range(len(self.cells)):
            ins = [F[e][self.cellline[ci][e]] for e in range(6)]
            ins = [x for x in ins if x is not None]
            g2, g3 = self.var(), self.var()
            for a, b in itertools.combinations(ins, 2):
                self.add([-a, -b, g2])
            for sub in itertools.combinations(ins, len(ins) - 1):
                self.add([-g2] + list(sub))
            for t in itertools.combinations(ins, 3):
                self.add([-t[0], -t[1], -t[2], g3])
            if len(ins) >= 3:
                for sub in itertools.combinations(ins, len(ins) - 2):
                    self.add([-g3] + list(sub))
            else:
                self.add([-g3])
            nn = self.var()
            mp = Mprev[ci] if Mprev is not None else None
            self.add([-nn, -g3])
            self.add([-nn, g2] + ([mp] if mp else []))
            self.add([g3, -g2, nn])
            if mp:
                self.add([g3, -mp, nn])
            N.append(nn)
        S = self.var()
        np_ = len(self.P)
        for ci in range(len(self.cells)):
            self.add([-S, N[ci]] if ci < np_ else [-S, -N[ci]])
        self.add([S] + [-N[ci] for ci in range(np_)] + [N[ci] for ci in range(np_, len(self.cells))])
        M = []
        for ci in range(len(self.cells)):
            if ci < np_:
                mm = self.var()
                self.add([-mm, N[ci]])
                self.add([-mm, -S])
                self.add([mm, -N[ci], S])
                M.append(mm)
            else:
                M.append(N[ci])
        return M, S

    def decode(self, model, cfg):
        out = []
        for e in range(6):
            pos, act = cfg[e]
            ps = [i for i, v in enumerate(pos) if v in model]
            assert len(ps) == 1
            out.append((self.offs[ps[0]], act in model))
        return out


def lines_between(cfgs):
    """cfgs: list of decoded configs, consecutive -> instruction lines."""
    out = []
    for a, b in zip(cfgs, cfgs[1:]):
        ins = []
        for (oa, aa), (ob, ab) in zip(a, b):
            if aa != ab:
                assert oa == ob
                ins.append('T')
            elif ob == oa + 1:
                ins.append('F')
            elif ob == oa - 1:
                ins.append('B')
            else:
                assert ob == oa
                ins.append('-')
        out.append(' '.join(ins))
    return out


def atleast(md, xs, m):
    """Clauses: at least m of xs true (sequential counter on negations: at most n-m false)."""
    n = len(xs)
    if m <= 0:
        return
    if m > n:
        md.add([])
        return
    if m == 1:
        md.add(list(xs))
        return
    # cnt[i][j]: among xs[0..i] at least j+1 true (j < m); upward implications only needed
    prev = None
    for i, x in enumerate(xs):
        cur = [md.var() for _ in range(m)]
        for j in range(m):
            # cur[j] -> prev[j] or (x and prev[j-1])
            if prev is None:
                if j == 0:
                    md.add([-cur[0], x])
                else:
                    md.add([-cur[j]])
            else:
                if j == 0:
                    md.add([-cur[0], prev[0], x])
                else:
                    md.add([-cur[j], prev[j], x])
                    md.add([-cur[j], prev[j], prev[j - 1]])
        prev = cur
    md.add([prev[m - 1]])


def build_cycle(md, K, m=1, start=None):
    """Cycle configs C_0..C_{K-1}; ticks fire C_0..C_{K-1} from empty matter, previous config = C_{K-1}
    (or `start` for a free / given start config: then it is not closed). Submission on the last tick and
    at least m submissions in total."""
    cs = [md.config() for _ in range(K)]
    for t in range(K):
        md.trans(start if (start is not None and t == 0) else cs[t - 1], cs[t])
    M = None
    Ss = []
    for t in range(K):
        M, S = md.tick(cs[t], M)
        Ss.append(S)
    md.add([Ss[-1]])
    atleast(md, Ss[:-1], m - 1)
    return cs, Ss


def cycle_only(r, pat, K, m=1, timeout_ms=0, free=False):
    md = Model(r, pat)
    st = md.config() if free else None
    cs, Ss = build_cycle(md, K, m, st)
    res = z3sat.solve(md.nv, md.cl, timeout_ms)
    if res is None or res == 'unknown':
        return res
    cfg = [md.decode(res, c) for c in cs]
    first = md.decode(res, st) if free else cfg[-1]
    return lines_between([first] + cfg)


def truncate(r, pat, count, prog):
    """Cut the program right after the count-th submission (None if it never gets there)."""
    lines = [l.split() for l in prog]
    lo, hi = 1, len(lines)
    if simulate(r, pat, lines) < count:
        return None
    while lo < hi:
        mid = (lo + hi) // 2
        if simulate(r, pat, lines[:mid]) >= count:
            hi = mid
        else:
            lo = mid + 1
    return prog[:lo]


def prog_with_prefix(r, pat, count, K, m, T0, timeout_ms=0):
    """Program = prefix of T0 lines (submission at T0) + (K,m)-cycle closing on the prefix's last config,
    repeated and cut after the count-th submission. Returns None / 'unknown' / program lines."""
    md = Model(r, pat)
    start = md.fixed_start()
    pre = [md.config() for _ in range(T0)]
    prev = start
    M = None
    S = None
    for t in range(T0):
        md.trans(prev, pre[t])
        M, S = md.tick(pre[t], M)
        prev = pre[t]
    md.add([S])
    if count > 1:
        cs = [md.config() for _ in range(K - 1)] + [pre[-1]]
        prev = pre[-1]
        M = None
        Ss = []
        for t in range(K):
            md.trans(prev, cs[t])
            M, S2 = md.tick(cs[t], M)
            Ss.append(S2)
            prev = cs[t]
        md.add([Ss[-1]])
        atleast(md, Ss[:-1], m - 1)
    res = z3sat.solve(md.nv, md.cl, timeout_ms)
    if res is None or res == 'unknown':
        return res
    st = md.decode(res, start)
    pc = [md.decode(res, c) for c in pre]
    prog = lines_between([st] + pc)
    if count > 1:
        cc = [md.decode(res, c) for c in cs]
        cl = lines_between([pc[-1]] + cc)
        reps = (count - 1 + m - 1) // m
        prog = truncate(r, pat, count, prog + cl * reps)
    return prog


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def auto(r, pat, count, best, tmo, kmin=1, mmax=3):
    """Search a shorter program than `best` lines: lower bound per copy, (K,m) cycles, then prefixes."""
    B = len(best)
    lines = [l.split() for l in best]
    # current first submission tick and per-copy rate
    f = next(t for t in range(1, B + 1) if simulate(r, pat, lines[:t]) >= 1)
    g = (B - f) / (count - 1) if count > 1 else 0
    log('B %d first %d rate %.2f' % (B, f, g))
    kstar = kmin
    if count > 1:
        while kstar < g:
            res = cycle_only(r, pat, kstar, 1, tmo, free=True)
            log('copy %d: %s' % (kstar, 'UNSAT' if res is None else res if res == 'unknown' else 'SAT'))
            if res is not None:
                break
            kstar += 1
    # lower bound for the first copy
    flo = kstar
    cands = []
    if count > 1:
        for m in range(1, mmax + 1):
            for K in range(m * kstar, int(g * m) + 2):
                cands.append((K / m, K, m))
        cands.sort()
    bestprog = None
    if count == 1:
        cyc_opts = [(1, 1)]
    else:
        cyc_opts = []
        for rate, K, m in cands:
            if flo + rate * (count - 1) - (K - 1) >= B:  # optimistic bound
                continue
            res = cycle_only(r, pat, K, m, tmo)
            log('cycle K=%d m=%d: %s' % (K, m, 'UNSAT' if res is None else res if res == 'unknown' else 'SAT'))
            if res is not None and res != 'unknown':
                cyc_opts.append((K, m))
                if len(cyc_opts) >= 2:
                    break
    for K, m in cyc_opts:
        # rest length of a (K,m) cycle is only known after solving: go downward from the largest useful T0
        cur = len(bestprog) if bestprog else B
        rest_lo = 0 if count == 1 else ((count - 1) // m) * K - (K - 1)
        T0 = min(f + 2, cur - 1 - rest_lo)
        while T0 >= max(flo, 1):
            cur = len(bestprog) if bestprog else B
            res = prog_with_prefix(r, pat, count, K, m, T0, tmo)
            log('prog K=%d m=%d T0=%d: %s' % (K, m, T0, 'UNSAT' if res is None else res if res == 'unknown'
                                                 else 'len %d' % len(res)))
            if res is None or res == 'unknown':
                break
            if len(res) < cur:
                bestprog = res
            T0 -= 1
    return bestprog


def main():
    inp, idx, mode = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    r, pat, count = list(cases(open(inp).read()))[idx]
    if mode in ('cycle', 'copy'):
        k = int(sys.argv[4])
        m = int(sys.argv[5]) if len(sys.argv) > 5 else 1
        res = cycle_only(r, pat, k, m, free=(mode == 'copy'))
        if res is None:
            print('UNSAT')
        elif res == 'unknown':
            print('UNKNOWN')
        else:
            print('SAT')
            print('\n'.join(res))
    elif mode == 'auto':
        # auto <bestfile(one program)> <timeout_ms>
        best = [l for l in open(sys.argv[4]).read().splitlines() if l.strip()]
        tmo = int(sys.argv[5]) if len(sys.argv) > 5 else 60000
        res = auto(r, pat, count, best, tmo)
        if res:
            n = simulate(r, pat, [l.split() for l in res])
            log('RESULT len %d sim %d/%d (best %d)' % (len(res), n, count, len(best)))
            print('\n'.join(res))


if __name__ == '__main__':
    main()
