from common import *

# Level 6: write a short program (6 instructions per line) that makes the pick-up arm
# submit the given pattern `count` times. Rules = level 5 simulation.
#
# Main strategy ("sweep"): pick an axis a. Emitters a and a+3 point in opposite
# directions along the same family of lines; put both on the same line ("pair") and the
# whole line gets 2 hits -> every cell of it becomes matter. The other four emitters
# ("punchers") cross that line: 3+ hits destroy, so they punch the halo cells (cells that
# must stay empty). The pair sweeps the pattern's lines one per tick; the line's final
# state is decided by the last tick the pair painted it. Lines with too many halo cells
# are fixed afterwards in "lag" ticks (one pair emitter stays, two punchers meet it at the
# hole = triple point). Builds alternate direction, so repeated patterns cost one tick per
# line. Every program is verified with an independent level-5 simulator; a simple
# per-cell program is the fallback.
#
# ASSUMPTION: a program is valid when the simulation submits AT LEAST `count` patterns
# (the official sandbox only flags "accepts X of N" when X < N); we stop at exactly count.
# ASSUMPTION (team validator): all emitters must be inactive at the end -> final T line.

DIRS = [(0, 2), (1, 1), (1, -1), (0, -2), (-1, -1), (-1, 1)]
NB = [(0, 2), (0, -2), (1, 1), (1, -1), (-1, 1), (-1, -1)]
LAMBDA = 3.0
DEBUG = False


def axis_line(a, y, x):
    return y if a == 0 else (x - y if a == 1 else x + y)


class Geo:
    def __init__(self, r):
        self.r = r
        h, w = 2 * r + 1, 4 * r + 1
        self.h, self.w = h, w
        inter = set()
        for i in range(h):
            k = abs(i - r)
            n = 2 * r + 1 - k
            if k == r:
                continue
            for j in range(1, n - 1):
                inter.add((i, k + 2 * j))
        self.inter = inter
        ring = []
        i, c = r, 0
        for di, dc in [(-1, 1), (0, 2), (1, 1), (1, -1), (0, -2), (-1, -1)]:
            for _ in range(r):
                ring.append((i, c))
                i += di
                c += dc
        self.ring = ring
        m = 6 * r
        self.m = m
        self.rays = [[None] * m for _ in range(6)]
        self.lineof = [[None] * m for _ in range(6)]
        self.idx = [dict() for _ in range(6)]
        for e in range(6):
            dy, dx = DIRS[e]
            a = e % 3
            for p in range(m):
                y, x = ring[p]
                y += dy
                x += dx
                cells = []
                while 0 <= y < h and 0 <= x < w:
                    if (y, x) in inter:
                        cells.append(y * w + x)
                    y += dy
                    x += dx
                self.rays[e][p] = cells
                if cells:
                    L = axis_line(a, cells[0] // w, cells[0] % w)
                    self.lineof[e][p] = L
                    home = e * r
                    old = self.idx[e].get(L)
                    if old is None or self.dist(p, home) < self.dist(old, home):
                        self.idx[e][L] = p

    def cross(self, a1, L1, a2, L2):
        """Cell id where line L1 of axis a1 meets line L2 of axis a2 (a1 != a2), or None."""
        if a1 > a2:
            a1, L1, a2, L2 = a2, L2, a1, L1
        if a1 == 0:
            y = L1
            x = L2 + L1 if a2 == 1 else L2 - L1
        else:
            if (L1 + L2) & 1:
                return None
            x = (L1 + L2) // 2
            y = (L2 - L1) // 2
        if (y, x) in self.inter:
            return y * self.w + x
        return None

    def dist(self, p, q):
        d = (q - p) % self.m
        return min(d, self.m - d)

    def step_dir(self, p, q):
        d = (q - p) % self.m
        return 'F' if d <= self.m - d else 'B'


# ---------------------------------------------------------------- simulation

class Sim:
    """Exact level-5 simulation with undo, plus pattern bookkeeping."""

    def __init__(self, geo, st, pcells):
        self.g = geo
        self.st = st              # cid -> 0 don't care, 1 pattern, 2 halo
        self.pcells = pcells
        self.totalP = len(pcells)
        self.bd = [0] * (geo.h * geo.w)
        self.pos = [e * geo.r for e in range(6)]
        self.act = [False] * 6
        self.nP = 0
        self.nH = 0
        self.count = 0
        self.prog = []

    def apply(self, ins):
        g = self.g
        m = g.m
        rec = (self.pos[:], self.act[:], self.nP, self.nH, self.count)
        pos, act = self.pos, self.act
        for e in range(6):
            c = ins[e]
            if c == 'F':
                pos[e] = (pos[e] + 1) % m
            elif c == 'B':
                pos[e] = (pos[e] - 1) % m
            elif c == 'T':
                act[e] = not act[e]
        cnt = {}
        for e in range(6):
            if act[e]:
                for cid in g.rays[e][pos[e]]:
                    cnt[cid] = cnt.get(cid, 0) + 1
        bd, st = self.bd, self.st
        changes = []
        for cid, k in cnt.items():
            if k == 2:
                if not bd[cid]:
                    bd[cid] = 1
                    changes.append((cid, 1))
                    s = st[cid]
                    if s == 1:
                        self.nP += 1
                    elif s == 2:
                        self.nH += 1
            elif k >= 3:
                if bd[cid]:
                    bd[cid] = 0
                    changes.append((cid, 0))
                    s = st[cid]
                    if s == 1:
                        self.nP -= 1
                    elif s == 2:
                        self.nH -= 1
        sub = None
        if self.nP == self.totalP and self.nH == 0:
            sub = [cid for cid in self.pcells if bd[cid]]
            for cid in sub:
                bd[cid] = 0
            self.nP = 0
            self.count += 1
        self.prog.append(ins)
        return (rec, changes, sub)

    def undo(self, u):
        rec, changes, sub = u
        if sub:
            for cid in sub:
                self.bd[cid] = 1
        for cid, v in changes:
            self.bd[cid] = 1 - v
        self.pos, self.act, self.nP, self.nH, self.count = rec[0], rec[1], rec[2], rec[3], rec[4]
        self.prog.pop()


def verify(r, pat, prog):
    """Independent simulation (accepted level-5 code). Returns number of submissions."""
    h, w = 2 * r + 1, 4 * r + 1
    g = []
    for i in range(h):
        k = abs(i - r)
        n = 2 * r + 1 - k
        cells = ['*'] * n if k == r else ['*'] + ['O'] * (n - 2) + ['*']
        g.append(list('-' * k + '-'.join(cells) + '-' * k))
    rg = []
    i, c = r, 0
    for di, dc in [(-1, 1), (0, 2), (1, 1), (1, -1), (0, -2), (-1, -1)]:
        for _ in range(r):
            rg.append((i, c))
            i += di
            c += dc
    m = len(rg)
    pcells = [(y, x) for y in range(h) for x in range(w) if pat[y][x] == 'M']
    pset = set(pcells)
    halo = set()
    for y, x in pcells:
        for dy, dx in NB:
            q = (y + dy, x + dx)
            if q not in pset and 0 <= q[0] < h and 0 <= q[1] < w:
                halo.add(q)
    pos = [0, r, 2 * r, 3 * r, 4 * r, 5 * r]
    active = [False] * 6
    count = 0
    for line in prog:
        for e, ins in enumerate(line):
            if ins == 'F':
                pos[e] = (pos[e] + 1) % m
            elif ins == 'B':
                pos[e] = (pos[e] - 1) % m
            elif ins == 'T':
                active[e] = not active[e]
        cnt = {}
        for e in range(6):
            if not active[e]:
                continue
            dy, dx = DIRS[e]
            y, x = rg[pos[e]]
            y += dy
            x += dx
            while 0 <= y < h and 0 <= x < w:
                if g[y][x] in 'OM':
                    cnt[(y, x)] = cnt.get((y, x), 0) + 1
                y += dy
                x += dx
        for (y, x), k in cnt.items():
            if k == 2:
                g[y][x] = 'M'
            elif k >= 3:
                g[y][x] = 'O'
        if all(g[y][x] == 'M' for y, x in pcells) and \
                not any(g[y][x] == 'M' for y, x in halo):
            for y, x in pcells:
                g[y][x] = 'O'
            count += 1
    return count


# ---------------------------------------------------------------- schedules

def sched(geo, p0, a0, p1, a1, k, mode):
    """Instruction list of length k taking (p0,a0) to (p1,a1), or None if too short."""
    d = geo.dist(p0, p1)
    mv = [geo.step_dir(p0, p1)] * d if d else []
    if not a0 and not a1:
        if d > k:
            return None
        return mv + ['-'] * (k - d)
    if not a0 and a1:
        if d + 1 > k:
            return None
        return mv + ['-'] * (k - d - 1) + ['T']
    if a0 and not a1:
        if d + 1 > k:
            return None
        return ['T'] + mv + ['-'] * (k - d - 1)
    if d == 0:
        return ['-'] * k
    if mode == 0:            # hot, move early
        if d > k:
            return None
        return mv + ['-'] * (k - d)
    if mode == 1:            # hot, move late
        if d > k:
            return None
        return ['-'] * (k - d) + mv
    if d + 2 > k:            # cold: off, move, on
        return None
    return ['T'] + mv + ['-'] * (k - d - 2) + ['T']


def req(geo, p0, a0, p1, a1, mode):
    d = geo.dist(p0, p1)
    if a0 != a1:
        return d + 1
    if a0 and mode == 2 and d > 0:
        return d + 2
    return d


# ---------------------------------------------------------------- sweep planner

class Sweep:
    def __init__(self, geo, st, pcells, a, lines, holes_by_line, cells_by_line, la):
        self.g = geo
        self.st = st
        self.a = a
        self.b = (a + 1) % 3
        self.c = (a + 2) % 3
        self.pair = (a, a + 3)
        self.punch = (self.b, self.b + 3, self.c, self.c + 3)
        self.lines = lines
        self.holes = holes_by_line
        self.lcells = cells_by_line
        self.la = la
        self.sim = Sim(geo, st, pcells)
        w = geo.w
        self.cellline = {}
        self.yx = lambda cid: (cid // w, cid % w)

    def wrong(self, cid):
        s = self.st[cid]
        v = self.sim.bd[cid]
        return (s == 1 and not v) or (s == 2 and v)

    # validate one applied tick
    def ok_tick(self, u, cur, lag, last):
        rec, changes, sub = u
        order = self.order
        st = self.st
        la = self.la
        for cid, v in changes:
            s = st[cid]
            if not s:
                continue
            if (s == 1 and v) or (s == 2 and not v):
                continue
            o = order.get(la[cid])
            if o is None or o < cur or (o == cur and lag):
                return False
        if sub is not None and cur != last:
            return False
        return True

    def run(self, targets, cur, lag, final_ok, modes_list):
        """Try schedules for the given targets; apply the first valid one.
        Returns None on failure, else 'sub' if a submission happened, else 'ok'."""
        g = self.g
        sim = self.sim
        last = len(self.order_list) - 1
        tried = set()
        for modes in modes_list:
            k = 1
            for e in range(6):
                p1, a1 = targets[e]
                k = max(k, req(g, sim.pos[e], sim.act[e], p1, a1, modes[e]))
            plan = []
            for e in range(6):
                p1, a1 = targets[e]
                plan.append(sched(g, sim.pos[e], sim.act[e], p1, a1, k, modes[e]))
            key = tuple(tuple(x) for x in plan)
            if key in tried:
                continue
            tried.add(key)
            undos = []
            good = True
            subbed = False
            for t in range(k):
                ins = [plan[e][t] for e in range(6)]
                u = sim.apply(ins)
                undos.append(u)
                if not self.ok_tick(u, cur, lag, last):
                    good = False
                    break
                if u[2] is not None:
                    subbed = True
                    break
            if good and not subbed and not final_ok():
                good = False
            if good:
                return 'sub' if subbed else 'ok'
            for u in reversed(undos):
                sim.undo(u)
        return None

    def modes_for(self, targets):
        sim = self.sim
        hot = [e for e in range(6) if sim.act[e] and targets[e][1] and
               self.g.dist(sim.pos[e], targets[e][0]) > 0]
        ml = [[0] * 6]
        if hot:
            ml.append([1] * 6)
            for e in hot:
                x = [0] * 6
                x[e] = 2
                ml.append(x)
            ml.append([2] * 6)
        return ml

    def puncher_target(self, e, cid):
        y, x = self.yx(cid)
        return self.g.idx[e][axis_line(e % 3, y, x)]

    def est_line(self, pos, act, L):
        """Rough number of ticks needed to punch line L's holes from (pos, act)."""
        hs = self.holes[L]
        g = self.g
        if not hs:
            return 0
        best = 99999
        pun = self.punch
        cost = [[req(g, pos[e], act[e], self.puncher_target(e, h), True, 0) for h in hs]
                for e in pun]
        n = len(hs)
        if n <= 4:
            for perm in permutations(range(4), n):
                v = 0
                for hi in range(n):
                    cc = cost[perm[hi]][hi]
                    if cc > v:
                        v = cc
                if v < best:
                    best = v
            return best
        return max(min(cost[j][hi] for j in range(4)) for hi in range(n)) + (n - 4)

    def paint_candidates(self, i, L):
        """Candidate targets for the final paint tick of line L (build index i).
        Each puncher either punches a hole, is switched off, or keeps its state;
        the final tick is pre-checked analytically (junk crossings, punched pattern)."""
        g = self.g
        sim = self.sim
        st = self.st
        a = self.a
        order = self.order
        la = self.la
        hs = self.holes[L]
        hset = set(hs)
        n = len(hs)
        pun = self.punch
        nxt = self.order_list[i + 1] if i + 1 < len(self.order_list) else None
        wish = self.wishes(nxt) if nxt is not None else None
        opts = []
        for e in pun:
            o = []
            ax = e % 3
            costs = []
            for h in hs:
                p = self.puncher_target(e, h)
                costs.append((req(g, sim.pos[e], sim.act[e], p, True, 0), h, p))
            costs.sort()
            if n > 6:
                costs = costs[:4]
            for c0, h, p in costs:
                o.append((h, p, True, c0))
            # off: stay, or drift one step toward the wish for the next line
            p0 = sim.pos[e]
            o.append((None, p0, False, req(g, p0, sim.act[e], p0, False, 0)))
            if wish is not None and wish[e] is not None and wish[e] != p0:
                d = g.step_dir(p0, wish[e])
                p1 = (p0 + (1 if d == 'F' else -1)) % g.m
                o.append((None, p1, False, req(g, p0, sim.act[e], p1, False, 0)))
                if sim.act[e]:
                    o.append((None, p1, True, 1))
            if sim.act[e]:
                o.append((None, p0, True, 0))
            opts.append(o)
        pk = 1
        for e in self.pair:
            pk = max(pk, req(g, sim.pos[e], sim.act[e], g.idx[e][L], True, 0))
        lines_of = [None] * 6
        cands = []
        for combo in product(*opts):
            used = set()
            okc = True
            for c in combo:
                if c[0] is not None:
                    if c[0] in used:
                        okc = False
                        break
                    used.add(c[0])
            if not okc:
                continue
            k = pk
            for c in combo:
                if c[3] > k:
                    k = c[3]
            # analytic check of the final tick
            covered = set()
            act_lines = []
            for j in range(4):
                c = combo[j]
                if not c[2]:
                    continue
                e = pun[j]
                Le = g.lineof[e][c[1]]
                if Le is None:
                    continue
                z = g.cross(a, L, e % 3, Le)
                if z is not None:
                    if st[z] == 1:
                        okc = False
                        break
                    covered.add(z)
                act_lines.append((e % 3, Le))
            if not okc:
                continue
            for x in range(len(act_lines)):
                ax1, L1 = act_lines[x]
                for y in range(x + 1, len(act_lines)):
                    ax2, L2 = act_lines[y]
                    if ax1 == ax2:
                        if L1 == L2:
                            okc = False
                        continue
                    z = g.cross(ax1, L1, ax2, L2)
                    if z is None or st[z] != 2:
                        continue
                    if la[z] == L:
                        continue
                    o = order.get(la[z])
                    if o is None or o < i:
                        okc = False
                if not okc:
                    break
            if not okc:
                continue
            left = [h for h in hs if h not in covered]
            pos2 = sim.pos[:]
            act2 = sim.act[:]
            for e in self.pair:
                pos2[e] = g.idx[e][L]
                act2[e] = True
            for j in range(4):
                e = pun[j]
                pos2[e] = combo[j][1]
                act2[e] = combo[j][2]
            lk = self.est_line(pos2, act2, nxt) if nxt is not None else 0
            tg = [(pos2[e], act2[e]) for e in range(6)]
            cands.append((k + 0.5 * lk + LAMBDA * len(left), k, lk, tg, frozenset(left)))
        cands.sort(key=lambda z: (z[0], z[1], z[2]))
        return cands

    def wishes(self, L):
        """Per puncher: a good position for line L (min-max assignment of its holes)."""
        hs = self.holes[L]
        g = self.g
        sim = self.sim
        pun = self.punch
        res = [None] * 6
        if not hs:
            return res
        tgt = [[self.puncher_target(e, h) for h in hs] for e in pun]
        cost = [[g.dist(sim.pos[e], tgt[j][hi]) for hi in range(len(hs))]
                for j, e in enumerate(pun)]
        n = len(hs)
        best = None
        if n <= 4:
            for perm in permutations(range(4), n):
                v = max(cost[perm[hi]][hi] for hi in range(n))
                if best is None or v < best[0]:
                    best = (v, perm)
            for hi in range(n):
                j = best[1][hi]
                res[pun[j]] = tgt[j][hi]
        else:
            for j in range(4):
                hi = min(range(n), key=lambda q: cost[j][q])
                res[pun[j]] = tgt[j][hi]
        return res

    def lag_candidates(self, W, leader, lagger, ltarget):
        g = self.g
        sim = self.sim
        holes = [cid for cid in W if self.st[cid] == 2]
        pats = [cid for cid in W if self.st[cid] == 1]
        bs = (self.b, self.b + 3)
        cs = (self.c, self.c + 3)
        cands = []
        base = [None] * 6
        base[lagger] = (sim.pos[lagger], True)
        base[leader] = ltarget
        offs = [(sim.pos[e], False) for e in range(6)]

        def mk(assign):
            tg = base[:]
            for e in self.punch:
                tg[e] = offs[e]
            for e, cid in assign:
                tg[e] = (self.puncher_target(e, cid), True)
            k = 1
            for e in range(6):
                k = max(k, req(g, sim.pos[e], sim.act[e], tg[e][0], tg[e][1], 0))
            return tg, k

        for h in holes:
            for be in bs:
                for ce in cs:
                    tg, k = mk([(be, h), (ce, h)])
                    cands.append((k / 1.0, k, tg, {h}))
        if len(holes) >= 2:
            for h1, h2 in combinations(holes, 2):
                for (b1, b2) in ((bs[0], bs[1]), (bs[1], bs[0])):
                    for (c1, c2) in ((cs[0], cs[1]), (cs[1], cs[0])):
                        tg, k = mk([(b1, h1), (c1, h1), (b2, h2), (c2, h2)])
                        cands.append((k / 2.0, k, tg, {h1, h2}))
        for pc in pats:
            for e in self.punch:
                tg, k = mk([(e, pc)])
                cands.append((k / 1.0, k, tg, {pc}))
        cands.sort(key=lambda z: (z[0], z[1]))
        return cands

    def build(self, order_list):
        self.order_list = order_list
        self.order = {L: i for i, L in enumerate(order_list)}
        sim = self.sim
        last = len(order_list) - 1
        start_count = sim.count
        for i, L in enumerate(order_list):
            cands = self.paint_candidates(i, L)
            done = None
            for sc, k, tot, tg, left in cands[:40]:
                lc = self.lcells[L]

                def fin(left=left, lc=lc):
                    for cid in lc:
                        if self.wrong(cid) and cid not in left:
                            return False
                    return True
                res = self.run(tg, i, False, fin, self.modes_for(tg))
                if res is not None:
                    done = res
                    break
            if done is None:
                # always possible: punch nothing, everything left for lag ticks
                tg = [(sim.pos[e], False) for e in range(6)]
                for e in self.pair:
                    tg[e] = (self.g.idx[e][L], True)
                lc = self.lcells[L]
                res = self.run(tg, i, False, lambda: True, [[2] * 6, [0] * 6])
                if res is None:
                    return False
                done = res
            if done == 'sub':
                if i == last:
                    return sim.count > start_count
                return False
            W = [cid for cid in self.lcells[L] if self.wrong(cid)]
            if W:
                if not self.lag(i, L, W, last):
                    return False
                if sim.count > start_count:
                    return i == last
        return sim.count > start_count

    def lag(self, i, L, W, last):
        g = self.g
        sim = self.sim
        best = None
        for leader in self.pair:
            lagger = self.pair[0] if leader == self.pair[1] else self.pair[1]
            if i < last:
                ltarget = (g.idx[leader][self.order_list[i + 1]], True)
            else:
                ltarget = (sim.pos[leader], False)
            best = (leader, lagger, ltarget)
            break
        leader, lagger, ltarget = best
        guard = 0
        while W:
            guard += 1
            if guard > 200:
                return False
            cands = self.lag_candidates(W, leader, lagger, ltarget)
            Wset = set(W)
            res = None
            for sc, k, tg, fixes in cands[:60]:
                def fin(fixes=fixes):
                    for cid in self.lcells[L]:
                        if self.wrong(cid) and cid not in Wset:
                            return False
                    return not any(self.wrong(cid) for cid in fixes)
                res = self.run(tg, i, True, fin, self.modes_for(tg) + [[2] * 6])
                if res is not None:
                    break
            if res is None:
                return False
            if res == 'sub':
                return True
            W = [cid for cid in self.lcells[L] if self.wrong(cid)]
        return True


def pattern_info(geo, pat):
    h, w = geo.h, geo.w
    st = [0] * (h * w)
    pcells = []
    for y in range(h):
        row = pat[y]
        for x in range(w):
            if x < len(row) and row[x] == 'M':
                st[y * w + x] = 1
                pcells.append(y * w + x)
    for cid in pcells:
        y, x = cid // w, cid % w
        for dy, dx in NB:
            yy, xx = y + dy, x + dx
            if 0 <= yy < h and 0 <= xx < w and (yy, xx) in geo.inter and st[yy * w + xx] == 0:
                st[yy * w + xx] = 2
    return st, pcells


def sweep_program(geo, st, pcells, a, direction, count, limit):
    w = geo.w
    la = [None] * (geo.h * w)
    for (y, x) in geo.inter:
        la[y * w + x] = axis_line(a, y, x)
    lines = sorted({la[cid] for cid in pcells})
    holes = {}
    lcells = {}
    for L in lines:
        holes[L] = []
        lcells[L] = []
    for (y, x) in geo.inter:
        cid = y * w + x
        L = la[cid]
        if L in lcells and st[cid]:
            lcells[L].append(cid)
            if st[cid] == 2:
                holes[L].append(cid)
    sw = Sweep(geo, st, pcells, a, lines, holes, lcells, la)
    order = lines if direction > 0 else lines[::-1]
    while sw.sim.count < count:
        if not sw.build(order):
            return None
        if len(sw.sim.prog) > limit:
            return None
        order = order[::-1]
    return sw.sim.prog


def simple_program(geo, st, pcells, count):
    """Fallback: one cell at a time with emitters 0 and 1, moving only while off."""
    w = geo.w
    sim = Sim(geo, st, pcells)
    out = []
    order = sorted(pcells)
    while sim.count < count:
        for cid in order:
            y, x = cid // w, cid % w
            t0 = geo.idx[0][axis_line(0, y, x)]
            t1 = geo.idx[1][axis_line(1, y, x)]
            k = max(geo.dist(sim.pos[0], t0), geo.dist(sim.pos[1], t1))
            s0 = sched(geo, sim.pos[0], False, t0, False, k, 0)
            s1 = sched(geo, sim.pos[1], False, t1, False, k, 0)
            for t in range(k):
                sim.apply([s0[t], s1[t], '-', '-', '-', '-'])
            sim.apply(['T', 'T', '-', '-', '-', '-'])
            sim.apply(['T', 'T', '-', '-', '-', '-'])
            if sim.count >= count:
                break
    return sim.prog


def walker_program(geo, st, pcells, eu, ev, count, limit):
    """Two beams on different axes; their crossing walks over pattern cells only
    (creating each one it visits). Far jumps switch one beam off meanwhile.
    Copies alternate between walking the tour forward and backward."""
    u, v = eu % 3, ev % 3
    w = geo.w
    node = {}
    for cid in pcells:
        y, x = cid // w, cid % w
        node[(geo.idx[eu][axis_line(u, y, x)], geo.idx[ev][axis_line(v, y, x)])] = cid
    m = geo.m
    adj = {}
    for (pu, pv) in node:
        nb = []
        for du in (-1, 0, 1):
            for dv in (-1, 0, 1):
                if du or dv:
                    q = ((pu + du) % m, (pv + dv) % m)
                    if q in node:
                        nb.append(q)
        adj[(pu, pv)] = nb
    dist = geo.dist

    def gate(a, b):
        d1 = dist(a[0], b[0])
        d2 = dist(a[1], b[1])
        return min(max(d1 + 2, d2), max(d1, d2 + 2))

    # states: (pu, au, pv, av) after each tick of one copy; first state creates a cell
    hu, hv = eu * geo.r, ev * geo.r
    start = min(node, key=lambda q: (max(dist(hu, q[0]), dist(hv, q[1])), q))
    cur = start
    todo = set(node)
    todo.discard(cur)
    states = [(cur[0], True, cur[1], True)]
    while todo:
        # BFS over pattern nodes
        prev = {cur: None}
        dq = deque([cur])
        best = None
        bestd = None
        dd = {cur: 0}
        while dq:
            q = dq.popleft()
            if q in todo:
                best, bestd = q, dd[q]
                break
            for nq in adj[q]:
                if nq not in dd:
                    dd[nq] = dd[q] + 1
                    prev[nq] = q
                    dq.append(nq)
        gbest = min(todo, key=lambda q: (gate(cur, q), q))
        gd = gate(cur, gbest)
        if best is not None and bestd <= gd:
            path = []
            q = best
            while q != cur:
                path.append(q)
                q = prev[q]
            for q in reversed(path):
                states.append((q[0], True, q[1], True))
                todo.discard(q)
            cur = best
        else:
            q = gbest
            d1 = dist(cur[0], q[0])
            d2 = dist(cur[1], q[1])
            if max(d1 + 2, d2) <= max(d1, d2 + 2):
                k = max(d1 + 2, d2)
                su = ['T'] + [geo.step_dir(cur[0], q[0])] * d1 + ['-'] * (k - 2 - d1) + ['T']
                sv = [geo.step_dir(cur[1], q[1])] * d2 + ['-'] * (k - d2)
                first_off = 0
            else:
                k = max(d1, d2 + 2)
                su = [geo.step_dir(cur[0], q[0])] * d1 + ['-'] * (k - d1)
                sv = ['T'] + [geo.step_dir(cur[1], q[1])] * d2 + ['-'] * (k - 2 - d2) + ['T']
                first_off = 1
            pu, au, pv, av = cur[0], True, cur[1], True
            for t in range(k):
                for s_, e_ in ((su[t], 0), (sv[t], 1)):
                    if s_ == 'T':
                        if e_ == 0:
                            au = not au
                        else:
                            av = not av
                    elif s_ in 'FB':
                        dlt = 1 if s_ == 'F' else -1
                        if e_ == 0:
                            pu = (pu + dlt) % m
                        else:
                            pv = (pv + dlt) % m
                states.append((pu, au, pv, av))
            cur = q
            todo.discard(q)
    # program
    prog = []

    def emit(a, b):
        ins = ['-'] * 6
        for e, p0, a0, p1, a1 in ((eu, a[0], a[1], b[0], b[1]), (ev, a[2], a[3], b[2], b[3])):
            if a0 != a1:
                ins[e] = 'T'
            elif p0 != p1:
                ins[e] = 'F' if (p1 - p0) % m == 1 else 'B'
        prog.append(ins)

    s0 = states[0]
    k = max(dist(hu, s0[0]), dist(hv, s0[2]))
    a = sched(geo, hu, False, s0[0], False, k, 0)
    b = sched(geo, hv, False, s0[2], False, k, 0)
    for t in range(k):
        ins = ['-'] * 6
        ins[eu] = a[t]
        ins[ev] = b[t]
        prog.append(ins)
    ins = ['-'] * 6
    ins[eu] = 'T'
    ins[ev] = 'T'
    prog.append(ins)
    sim = Sim(geo, st, pcells)
    for ins in prog:
        sim.apply(ins)
    seq = states
    curst = states[0]
    guard = 0
    while sim.count < count:
        guard += 1
        if guard > 4 * count + 4 or len(sim.prog) > limit:
            return None
        if guard > 1:
            seq = seq[::-1]
            sim.apply(['-'] * 6)
            prog.append(['-'] * 6)
            if sim.count >= count:
                break
        for nxt in seq[1:]:
            n0 = len(prog)
            emit(curst, nxt)
            sim.apply(prog[n0])
            curst = nxt
            if sim.count >= count:
                break
    return prog


def static_program(geo, st, pcells):
    """A fixed beam set whose 2-hit cells contain the whole pattern and no halo cell:
    then every tick (even '- - - - - -') submits one copy. Returns (setup program, ok)."""
    w = geo.w
    lines = [sorted({axis_line(a, cid // w, cid % w) for cid in pcells}) for a in range(3)]
    if max(len(x) for x in lines) > 12:
        return None
    halo = [cid for cid in range(len(st)) if st[cid] == 2]

    def choices(ls):
        res = [()]
        for i in range(len(ls)):
            res.append((ls[i],))
            for j in range(i, len(ls)):
                res.append((ls[i], ls[j]))
        return res
    yx = [(cid // w, cid % w) for cid in pcells]
    hyx = [(cid // w, cid % w) for cid in halo]
    best = None
    for c0 in choices(lines[0]):
        h0 = [c0.count(y) for (y, x) in yx]
        if max(h0) > 2:
            continue
        for c1 in choices(lines[1]):
            need = {}
            okc = True
            for i, (y, x) in enumerate(yx):
                k = 2 - h0[i] - c1.count(x - y)
                if k < 0:
                    okc = False
                    break
                L = x + y
                if need.get(L, k) != k:
                    okc = False
                    break
                need[L] = k
            if not okc:
                continue
            c2 = []
            for L, k in need.items():
                c2 += [L] * k
            if len(c2) > 2:
                continue
            c2 = tuple(c2)
            # halo cells must not get exactly 2 hits
            bad = False
            for (y, x) in hyx:
                if c0.count(y) + c1.count(x - y) + c2.count(x + y) == 2:
                    bad = True
                    break
            if bad:
                continue
            # assign emitters, cost = setup ticks
            tg = {}
            cost = 0
            for a, cs in ((0, c0), (1, c1), (2, c2)):
                es = (a, a + 3)
                if len(cs) == 0:
                    continue
                if len(cs) == 1:
                    opts = [((es[0], cs[0]),), ((es[1], cs[0]),)]
                else:
                    opts = [((es[0], cs[0]), (es[1], cs[1])), ((es[0], cs[1]), (es[1], cs[0]))]
                bo = None
                for o in opts:
                    cc = max(geo.dist(e * geo.r, geo.idx[e][L]) for e, L in o)
                    if bo is None or cc < bo[0]:
                        bo = (cc, o)
                cost = max(cost, bo[0])
                for e, L in bo[1]:
                    tg[e] = geo.idx[e][L]
            if best is None or cost < best[0]:
                best = (cost, tg)
    if best is None:
        return None
    k, tg = best
    prog = []
    sch = {e: sched(geo, e * geo.r, False, p, False, k, 0) for e, p in tg.items()}
    for t in range(k):
        prog.append([sch[e][t] if e in sch else '-' for e in range(6)])
    prog.append(['T' if e in tg else '-' for e in range(6)])
    return prog


class Cyc:
    """Short window of 'safe' configurations (no halo cell gets exactly 2 hits, no
    pattern cell gets 3+), consecutive ones one instruction apart, whose created cells
    cover the pattern. Copies walk the window forward and backward."""

    def __init__(self, geo, st, pcells):
        self.g = geo
        self.st = st
        w = geo.w
        r = geo.r
        self.pcells = pcells
        self.bit = {cid: 1 << i for i, cid in enumerate(pcells)}
        self.full = (1 << len(pcells)) - 1
        # line ids per axis -> index
        self.lids = []
        self.lidx = []
        for a in range(3):
            ids = sorted({axis_line(a, y, x) for (y, x) in geo.inter})
            self.lids.append(ids)
            self.lidx.append({L: i for i, L in enumerate(ids)})
        n = len(geo.inter)
        self.la = [dict() for _ in range(3)]
        cellla = {}
        for (y, x) in geo.inter:
            cid = y * w + x
            cellla[cid] = tuple(self.lidx[a][axis_line(a, y, x)] for a in range(3))
        self.cellla = cellla
        nl = [len(self.lids[a]) for a in range(3)]
        self.X = {}
        for a1 in range(3):
            for a2 in range(3):
                if a1 == a2:
                    continue
                tab = []
                for i1 in range(nl[a1]):
                    row = []
                    for i2 in range(nl[a2]):
                        z = geo.cross(a1, self.lids[a1][i1], a2, self.lids[a2][i2])
                        row.append(-1 if z is None else z)
                    tab.append(row)
                self.X[(a1, a2)] = tab
        self.patbits = [[0] * nl[a] for a in range(3)]
        self.holes = [[[] for _ in range(nl[a])] for a in range(3)]
        for cid, ls in cellla.items():
            s = st[cid]
            for a in range(3):
                if s == 1:
                    self.patbits[a][ls[a]] |= self.bit[cid]
                elif s == 2:
                    self.holes[a][ls[a]].append(cid)
        # beam (axis, line index) per emitter position
        self.beam = []
        for e in range(6):
            row = []
            for p in range(geo.m):
                L = geo.lineof[e][p]
                row.append(None if L is None else (e % 3, self.lidx[e % 3][L]))
            self.beam.append(row)
        # useful line index range per axis (pattern lines +- 1)
        self.rng = []
        for a in range(3):
            ls = sorted({cellla[c][a] for c in pcells})
            self.rng.append((ls[0] - 1, ls[-1] + 1))

    def evaluate(self, beams):
        st = self.st
        X = self.X
        cl = self.cellla
        seen = {}
        for b in beams:
            seen[b] = seen.get(b, 0) + 1
        pairs = []
        singles = []
        for b, k in seen.items():
            if k == 2:
                pairs.append(b)
            else:
                singles.append(b)
        created = 0
        allb = pairs + singles
        for (a, i) in pairs:
            Z = set()
            for (a2, i2) in allb:
                if a2 == a:
                    continue
                z = X[(a, a2)][i][i2]
                if z >= 0:
                    if st[z] == 1:
                        return -1
                    Z.add(z)
            for h in self.holes[a][i]:
                if h not in Z:
                    return -1
            created |= self.patbits[a][i]
        ns = len(singles)
        bit = self.bit
        for x in range(ns):
            a1, i1 = singles[x]
            for y in range(x + 1, ns):
                a2, i2 = singles[y]
                if a1 == a2:
                    continue
                z = X[(a1, a2)][i1][i2]
                if z < 0:
                    continue
                lz = cl[z]
                skip = False
                for (a, i) in pairs:
                    if lz[a] == i:
                        skip = True
                        break
                if skip:
                    continue
                third = False
                for q in range(ns):
                    if q != x and q != y:
                        a3, i3 = singles[q]
                        if a3 != a1 and a3 != a2 and lz[a3] == i3:
                            third = True
                            break
                s = st[z]
                if third:
                    if s == 1:
                        return -1
                    continue
                if s == 2:
                    return -1
                if s == 1:
                    created |= bit[z]
        return created

    def beams_of(self, pos, act):
        res = []
        for e in range(6):
            if act[e]:
                b = self.beam[e][pos[e]]
                if b is not None:
                    res.append(b)
        return res

    def seeds(self, rnd, tries):
        """Local search for safe configurations with large coverage."""
        g = self.g
        opts = []
        for e in range(6):
            a = e % 3
            lo, hi = self.rng[a]
            o = [None]
            for i in range(max(lo, 0), min(hi, len(self.lids[a]) - 1) + 1):
                p = g.idx[e].get(self.lids[a][i])
                if p is not None:
                    o.append(p)
            opts.append(o)

        def cov(cfg):
            beams = [self.beam[e][cfg[e]] for e in range(6) if cfg[e] is not None]
            c = self.evaluate(beams)
            return c

        found = {}
        for t in range(tries):
            cfg = [rnd.choice(opts[e]) if rnd.random() < 0.7 else None for e in range(6)]
            c = cov(cfg)
            if c < 0:
                cfg = [None] * 6
                c = 0
            cur = bin(c).count('1')
            while True:
                best = None
                for e in range(6):
                    old = cfg[e]
                    for o in opts[e]:
                        if o == old:
                            continue
                        cfg[e] = o
                        c2 = cov(cfg)
                        if c2 >= 0:
                            v = bin(c2).count('1')
                            if v > cur and (best is None or v > best[0]):
                                best = (v, e, o)
                    cfg[e] = old
                if best is None:
                    break
                cur = best[0]
                cfg[best[1]] = best[2]
            key = tuple(cfg)
            if cur > 0:
                found[key] = cur
        return sorted(found.items(), key=lambda kv: -kv[1])

    def search(self, count, width, maxt, rnd):
        g = self.g
        m = g.m
        seeds = self.seeds(rnd, 40)[:width * 2]
        if not seeds:
            return None
        # median pattern line per axis for idle emitters
        med = []
        for e in range(6):
            a = e % 3
            ls = sorted(self.cellla[c][a] for c in self.pcells)
            med.append(g.idx[e][self.lids[a][ls[len(ls) // 2]]])
        beam = []
        for cfg, v in seeds:
            pos = tuple(cfg[e] if cfg[e] is not None else med[e] for e in range(6))
            act = tuple(cfg[e] is not None for e in range(6))
            cov = self.evaluate(self.beams_of(pos, act))
            setup = max(g.dist(e * g.r, pos[e]) + (1 if act[e] else 0) for e in range(6))
            beam.append((pos, act, cov, setup, None))
        # beam entries: (pos, act, covered, setup, parent-chain)
        hist = [beam]
        bestc = -1
        stall = 0
        for t in range(maxt + 1):
            done = [s for s in beam if s[2] == self.full]
            if done:
                return [(self.chain_of(s), s[3]) for s in done]
            c0 = max(bin(s[2]).count('1') for s in beam)
            if c0 > bestc:
                bestc = c0
                stall = 0
            else:
                stall += 1
            if stall >= 2 or t == maxt:
                res = []
                for s in beam[:4]:
                    ch = self.chain_of(s)
                    ext = self.complete(s[0], s[1], s[2])
                    if ext is not None:
                        res.append((ch + ext, s[3]))
                return res or None
            nxt = {}
            for st_ in beam:
                pos, act, cov, setup, par = st_
                eopts = []
                for e in range(6):
                    p = pos[e]
                    o = [(p, act[e]), ((p + 1) % m, act[e]), ((p - 1) % m, act[e]), (p, not act[e])]
                    eopts.append(o)
                for combo in product(*eopts):
                    beams = []
                    for e in range(6):
                        if combo[e][1]:
                            b = self.beam[e][combo[e][0]]
                            if b is not None:
                                beams.append(b)
                    c = self.evaluate(beams)
                    if c < 0:
                        continue
                    nc = cov | c
                    npos = tuple(x[0] for x in combo)
                    nact = tuple(x[1] for x in combo)
                    key = (npos, nact, nc)
                    old = nxt.get(key)
                    if old is None or old[3] > setup:
                        nxt[key] = (npos, nact, nc, setup, st_)
            if not nxt:
                return None
            cand = sorted(nxt.values(), key=lambda s: (-bin(s[2]).count('1'), s[3]))
            cand = cand[:width * 6]
            sc = []
            for s in cand:
                sc.append((-bin(s[2]).count('1'), self.h(s[0], s[1], s[2]), s[3], s))
            sc.sort(key=lambda z: z[:3])
            beam = [z[3] for z in sc[:width]]
            hist.append(beam)
            if DEBUG: print("t", t, [bin(s[2]).count("1") for s in beam[:5]], self.h(beam[0][0], beam[0][1], beam[0][2]), len(self.pcells))
        return None

    def chain_of(self, s):
        chain = []
        while s is not None:
            chain.append((s[0], s[1]))
            s = s[4]
        chain.reverse()
        return chain

    def complete(self, pos, act, cov):
        """Create the remaining cells one by one with just two crossing beams."""
        g = self.g
        m = g.m
        pos = list(pos)
        act = list(act)
        out = []
        left = [cid for i, cid in enumerate(self.pcells) if not cov >> i & 1]
        while left:
            best = None
            for cid in left:
                ls = self.cellla[cid]
                for e1 in range(6):
                    for e2 in range(e1 + 1, 6):
                        if e1 % 3 == e2 % 3:
                            continue
                        p1 = g.idx[e1][self.lids[e1 % 3][ls[e1 % 3]]]
                        p2 = g.idx[e2][self.lids[e2 % 3][ls[e2 % 3]]]
                        others = [e for e in range(6) if e != e1 and e != e2 and act[e]]
                        d1 = g.dist(pos[e1], p1)
                        d2 = g.dist(pos[e2], p2)
                        # hot step: only e1, e2 active, one tick
                        if not others and act[e1] and act[e2] and d1 <= 1 and d2 <= 1:
                            k = 1
                            hot = True
                        else:
                            hot = False
                            k = max(d1 + (1 if act[e1] and d1 else 0),
                                    d2 + (1 if act[e2] and d2 else 0),
                                    1 if others else 0) + 1
                        if best is None or k < best[0]:
                            best = (k, cid, e1, e2, p1, p2, hot)
            k, cid, e1, e2, p1, p2, hot = best
            if hot:
                pos[e1], pos[e2] = p1, p2
                out.append((tuple(pos), tuple(act)))
            else:
                sch = []
                for e in range(6):
                    if e == e1 or e == e2:
                        tp = p1 if e == e1 else p2
                        if act[e] and pos[e] == tp:
                            sch.append(['-'] * k)
                        else:
                            sch.append(sched(g, pos[e], act[e], tp, True, k, 2))
                    else:
                        sch.append(sched(g, pos[e], act[e], pos[e], False, k, 0))
                for t in range(k):
                    for e in range(6):
                        c = sch[e][t]
                        if c == 'T':
                            act[e] = not act[e]
                        elif c == 'F':
                            pos[e] = (pos[e] + 1) % m
                        elif c == 'B':
                            pos[e] = (pos[e] - 1) % m
                    out.append((tuple(pos), tuple(act)))
            # cells now covered by the final state
            c = self.evaluate(self.beams_of(pos, act))
            if c < 0:
                return None
            left = [x for x in left if not c & self.bit[x]]
        return out

    def h(self, pos, act, cov):
        """Ticks until the nearest uncovered cell could be hit by two beams."""
        g = self.g
        best = 99
        tot = 0
        for i, cid in enumerate(self.pcells):
            if cov >> i & 1:
                continue
            ls = self.cellla[cid]
            d = []
            for e in range(6):
                a = e % 3
                p = g.idx[e].get(self.lids[a][ls[a]])
                d.append(g.dist(pos[e], p) + (0 if act[e] else 1))
            v = 99
            for a1 in range(3):
                x1 = min(d[a1], d[a1 + 3])
                for a2 in range(a1 + 1, 3):
                    x2 = min(d[a2], d[a2 + 3])
                    y = x1 if x1 > x2 else x2
                    if y < v:
                        v = y
            tot += v
            if v < best:
                best = v
        return best * 100 + tot

    def program(self, count, width=12, maxt=12, seed=1):
        import random
        rnd = random.Random(seed)
        res = self.search(count, width, maxt, rnd)
        if not res:
            return None
        chain = min(res, key=lambda z: z[1] + len(z[0]) * count)[0]
        g = self.g
        m = g.m
        prog = []
        pos0, act0 = chain[0]
        k = max(1, max(g.dist(e * g.r, pos0[e]) + (1 if act0[e] else 0) for e in range(6)))
        sch = [sched(g, e * g.r, False, pos0[e], act0[e], k, 0) for e in range(6)]
        for t in range(k):
            prog.append([sch[e][t] for e in range(6)])

        def ins(a, b):
            out = []
            for e in range(6):
                if a[1][e] != b[1][e]:
                    out.append('T')
                elif a[0][e] != b[0][e]:
                    out.append('F' if (b[0][e] - a[0][e]) % m == 1 else 'B')
                else:
                    out.append('-')
            return out
        sim = Sim(g, self.st, self.pcells)
        for x in prog:
            sim.apply(x)
        cur = chain[0]
        seq = chain
        first = True
        guard = 0
        while sim.count < count:
            guard += 1
            if guard > 3 * count + 5:
                return None
            if not first:
                seq = seq[::-1]
                x = ['-'] * 6
                prog.append(x)
                sim.apply(x)
                if sim.count >= count:
                    break
            first = False
            for nx in seq[1:]:
                x = ins(cur, nx)
                prog.append(x)
                sim.apply(x)
                cur = nx
                if sim.count >= count:
                    break
        return prog


def solve_one(r, pat, count):
    geo = Geo(r)
    st, pcells = pattern_info(geo, pat)
    best = simple_program(geo, st, pcells, count)
    if verify(r, pat, best) < count:
        best = None
    try:
        cy = Cyc(geo, st, pcells)
        cp = cy.program(count, 30, 40)
    except Exception:
        cp = None
    if cp is not None and (best is None or len(cp) < len(best)) and verify(r, pat, cp) >= count:
        best = cp
    sp = static_program(geo, st, pcells)
    if sp is not None:
        sp = sp + [['-'] * 6 for _ in range(count - 1)]
        if (best is None or len(sp) < len(best)) and verify(r, pat, sp) >= count:
            best = sp
    for eu in range(6):
        for ev in range(eu + 1, 6):
            if eu % 3 == ev % 3:
                continue
            lim = len(best) if best else 10 ** 9
            prog = walker_program(geo, st, pcells, eu, ev, count, lim)
            if prog is None or (best is not None and len(prog) >= len(best)):
                continue
            if verify(r, pat, prog) >= count:
                best = prog
    for a in range(3):
        for d in (1, -1):
            lim = len(best) if best else 10 ** 9
            prog = sweep_program(geo, st, pcells, a, d, count, lim)
            if prog is None:
                continue
            if best is not None and len(prog) >= len(best):
                continue
            if verify(r, pat, prog) >= count:
                best = prog
    # The validator requires every emitter to be switched off when the program ends.
    act = [False] * 6
    for ins in best:
        for e in range(6):
            if ins[e] == 'T':
                act[e] = not act[e]
    if any(act):
        best = best + [['T' if act[e] else '-' for e in range(6)]]
    return best


def solve(text):
    t = text.split('\n')
    n = int(t[0].split()[0])
    p = 1
    out = []
    for q in range(n):
        while not t[p].strip():
            p += 1
        r, hh, ww, cnt = map(int, t[p].split())
        p += 1
        pat = [s.rstrip('\r') for s in t[p:p + hh]]
        p += hh
        prog = solve_one(r, pat, cnt)
        if q:
            out.append('')
        for ins in prog:
            out.append(' '.join(ins))
    return out
