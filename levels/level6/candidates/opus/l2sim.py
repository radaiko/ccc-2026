"""Fast bitmask simulator over the relevant cells (P + halo) for the large agent 2 tools.
Model(r, pat): .lines[e][pos] = bitmask of relevant cells hit by emitter e at rail pos;
.run(configs, M=0) and helpers to turn a program into a config sequence and back."""
from levels.level6.candidates.astra import board, ring, DIRS, NB

INV = {'F': 'B', 'B': 'F', 'T': 'T', '-': '-'}


class Model:
    def __init__(self, r, pat):
        self.r = r
        g = board(r)
        h, w = 2 * r + 1, 4 * r + 1
        rg = ring(r)
        self.m = m = len(rg)
        pc = [(y, x) for y in range(h) for x in range(w) if pat[y][x] == 'M']
        ps = set(pc)
        halo = sorted({(y + dy, x + dx) for y, x in pc for dy, dx in NB
                       if (y + dy, x + dx) not in ps and 0 <= y + dy < h and 0 <= x + dx < w
                       and g[y + dy][x + dx] in 'OM'})
        cells = pc + halo
        idx = {c: k for k, c in enumerate(cells)}
        self.NP = len(pc)
        self.PM = (1 << len(pc)) - 1
        self.HM = ((1 << len(cells)) - 1) & ~self.PM
        self.lines = []
        for e in range(6):
            dy, dx = DIRS[e]
            row = []
            for p in range(m):
                y, x = rg[p]
                y += dy
                x += dx
                b = 0
                while 0 <= y < h and 0 <= x < w and g[y][x] in 'OM':
                    k = idx.get((y, x))
                    if k is not None:
                        b |= 1 << k
                    y += dy
                    x += dx
                row.append(b)
            self.lines.append(row)
        self.start = (tuple(e * r for e in range(6)), 0)

    def configs(self, prog):
        """config after each line: list of (pos tuple, active bitmask)."""
        pos = list(self.start[0])
        act = 0
        out = []
        m = self.m
        for line in prog:
            for e, ins in enumerate(line.split()):
                if ins == 'F':
                    pos[e] = (pos[e] + 1) % m
                elif ins == 'B':
                    pos[e] = (pos[e] - 1) % m
                elif ins == 'T':
                    act ^= 1 << e
            out.append((tuple(pos), act))
        return out

    def step(self, M, cfg):
        """apply one tick's firing for config cfg; returns (new M, submitted)."""
        pos, act = cfg
        s0 = s1 = s2 = 0
        for e in range(6):
            if act >> e & 1:
                L = self.lines[e][pos[e]]
                s2 |= s1 & L
                s1 |= s0 & L
                s0 |= L
        M = (M | (s1 & ~s2)) & ~s2
        if M & self.PM == self.PM and not M & self.HM:
            return M & ~self.PM, True
        return M, False

    def subs(self, cfgs, M=0):
        out = []
        for t, c in enumerate(cfgs):
            M, s = self.step(M, c)
            if s:
                out.append(t)
        return out

    def line(self, a, b):
        """instruction line moving config a -> b (must be one step apart per emitter)."""
        (pa, aa), (pb, ab) = a, b
        ins = []
        m = self.m
        for e in range(6):
            ta = aa >> e & 1
            tb = ab >> e & 1
            if pa[e] == pb[e]:
                ins.append('T' if ta != tb else '-')
            elif (pa[e] + 1) % m == pb[e] and ta == tb:
                ins.append('F')
            elif (pa[e] - 1) % m == pb[e] and ta == tb:
                ins.append('B')
            else:
                return None
        return ' '.join(ins)
