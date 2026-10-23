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


def build_cycle(md, k):
    """Cycle configs C_0..C_{k-1}; ticks fire C_0..C_{k-1} from empty matter, previous config = C_{k-1}."""
    cs = [md.config() for _ in range(k)]
    for t in range(k):
        md.trans(cs[t - 1], cs[t])
    M = None
    Ss = []
    for t in range(k):
        M, S = md.tick(cs[t], M)
        Ss.append(S)
    md.add([Ss[-1]])
    return cs, Ss


def cycle_only(r, pat, k, timeout_ms=0):
    md = Model(r, pat)
    cs, Ss = build_cycle(md, k)
    res = z3sat.solve(md.nv, md.cl, timeout_ms)
    if res is None or res == 'unknown':
        return res
    cfg = [md.decode(res, c) for c in cs]
    return lines_between([cfg[-1]] + cfg)


def prog_with_prefix(r, pat, count, k, T0, timeout_ms=0):
    """Program = prefix of T0 lines (submission at T0) + k-cycle repeated count-1 times."""
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
    cyc = []
    if count > 1:
        cyc = [md.config() for _ in range(k - 1)] + [pre[-1]]
        prev = pre[-1]
        M = None
        for t in range(k):
            md.trans(prev, cyc[t])
            M, S2 = md.tick(cyc[t], M)
            prev = cyc[t]
        md.add([S2])
    res = z3sat.solve(md.nv, md.cl, timeout_ms)
    if res is None or res == 'unknown':
        return res
    st = md.decode(res, start)
    pc = [md.decode(res, c) for c in pre]
    prog = lines_between([st] + pc)
    if count > 1:
        cc = [md.decode(res, c) for c in cyc]
        cl = lines_between([pc[-1]] + cc)
        prog += cl * (count - 1)
    return prog


def main():
    inp, idx, mode = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    r, pat, count = list(cases(open(inp).read()))[idx]
    if mode == 'cycle':
        k = int(sys.argv[4])
        res = cycle_only(r, pat, k)
        if res is None:
            print('UNSAT')
        elif res == 'unknown':
            print('UNKNOWN')
        else:
            print('SAT')
            print('\n'.join(res))
    elif mode == 'prog':
        k, tmax = int(sys.argv[4]), int(sys.argv[5])
        tmin = int(sys.argv[6]) if len(sys.argv) > 6 else 1
        for T0 in range(tmin, tmax + 1):
            res = prog_with_prefix(r, pat, count, k, T0)
            if res is None or res == 'unknown':
                print('T0 %d: %s' % (T0, res), file=sys.stderr, flush=True)
                continue
            n = simulate(r, pat, [l.split() for l in res])
            print('T0 %d: len %d sim %d/%d' % (T0, len(res), n, count), file=sys.stderr, flush=True)
            print('\n'.join(res))
            break


if __name__ == '__main__':
    main()
