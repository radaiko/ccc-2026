from common import *

# Level 6: write programs that submit each pattern `count` times, using as few lines as possible.
# Simulation rules are ported from data/sandbox-level-6.html. Each tick runs the 6 instructions,
# then sets cells hit by exactly 2 beams to matter and clears cells hit by 3 or more, then accepts
# the pattern at most once (every M cell is matter and no 'O' cell next to an M is matter).
# ASSUMPTION: all emitters are switched off at the end of each program, as validator.py requires.

DIR_TO = [(2, 0), (1, 1), (-1, 1), (-2, 0), (-1, -1), (1, -1)]  # (dc, dr): E SE SW W NW NE
FIRE = [(2, 0), (1, 1), (-1, 1), (-2, 0), (-1, -1), (1, -1)]  # emitter t fires FIRE[t]
OPTS = ('-', 'F', 'B', 'T')
AXES = ((0, 3), (1, 4), (2, 5))


class Geo(object):
    def __init__(self, R):
        radius = R + 1
        rows, cols = 2 * radius - 1, 4 * radius - 3
        self.R, self.rows, self.cols = R, rows, cols

        def in_grid(c, r):
            if r < 0 or r >= rows or (r + c + radius + 1) % 2:
                return False
            if r < radius:
                return c + r >= radius - 1 and c - r <= cols - radius + 1
            return c + (2 * radius - 1 - r) >= radius - 1 and c + r - 2 * radius + 1 < cols - radius + 1

        idx = {}
        cells = []
        for r in range(rows):
            for c in range(cols):
                if not in_grid(c, r):
                    continue
                rail = r == 0 or r == rows - 1
                if r < radius:
                    rail = rail or c == radius - 1 - r or c == cols - radius + r
                else:
                    rail = rail or c == r - radius + 1 or c == cols + radius - 2 - r
                if not rail:
                    idx[(r, c)] = len(cells)
                    cells.append((r, c))
        self.idx, self.cells, self.n = idx, cells, len(cells)
        per = []
        c, r = 0, radius - 1
        for dc, dr in [(1, -1), (2, 0), (1, 1), (-1, 1), (-2, 0), (-1, -1)]:
            for _ in range(radius - 1):
                per.append((c, r))
                c += dc
                r += dr
        self.per = per
        P = self.P = len(per)
        # ray[t][p]: bitmask of interior cells hit by emitter t standing at perimeter p.
        ray = [[0] * P for _ in range(6)]
        for p, (c0, r0) in enumerate(per):
            for t, (dc, dr) in enumerate(FIRE):
                m = 0
                c, r = c0 + dc, r0 + dr
                while in_grid(c, r):
                    k = idx.get((r, c))
                    if k is not None:
                        m |= 1 << k
                    c += dc
                    r += dr
                ray[t][p] = m
        self.ray = ray
        # Line index of a cell on each axis; target perimeter position per emitter and line.
        self.nb = [0] * self.n
        for k, (r, c) in enumerate(cells):
            m = 0
            for dc, dr in DIR_TO:
                j = idx.get((r + dr, c + dc))
                if j is not None:
                    m |= 1 << j
            self.nb[k] = m
        # For each emitter: map from line mask -> perimeter position, and per cell the position.
        self.cellpos = [[None] * self.n for _ in range(6)]
        self.linepos = []  # per emitter: list of (p, mask) for useful positions
        for t in range(6):
            lst = []
            for p in range(P):
                m = ray[t][p]
                if m:
                    lst.append((p, m))
                    mm = m
                    while mm:
                        low = mm & -mm
                        self.cellpos[t][low.bit_length() - 1] = p
                        mm ^= low
            self.linepos.append(lst)
        # ring distance table
        self.rd = [[min((a - b) % P, (b - a) % P) for b in range(P)] for a in range(P)]


def parse(text):
    ls = text.replace('\r', '').split('\n')
    p = 0
    out = []

    def nxt():
        nonlocal p
        while not ls[p].strip():
            p += 1
        p += 1
        return ls[p - 1].strip()

    n = int(nxt().split()[0])
    for _ in range(n):
        R, rows, cols, k = map(int, nxt().split())
        pat = [nxt() for _ in range(rows)]
        out.append((R, k, pat))
    return out


def pattern_masks(g, pat):
    S = K = 0
    for k, (r, c) in enumerate(g.cells):
        if pat[r][c] == 'M':
            S |= 1 << k
    for k in range(g.n):
        if not (S >> k) & 1 and g.nb[k] & S:
            K |= 1 << k
    return S, K


def simulate(g, S, K, prog):
    """Number of accepted patterns and final active flags."""
    pos = [t * g.R for t in range(6)]
    act = [False] * 6
    M = 0
    acc = 0
    P = g.P
    for line in prog:
        for t in range(6):
            ins = line[t]
            if ins == 'F':
                pos[t] = (pos[t] + 1) % P
            elif ins == 'B':
                pos[t] = (pos[t] - 1) % P
            elif ins == 'T':
                act[t] = not act[t]
        t1 = t2 = t3 = 0
        for t in range(6):
            if act[t]:
                m = g.ray[t][pos[t]]
                t3 |= t2 & m
                t2 |= t1 & m
                t1 |= m
        M = (M | (t2 & ~t3)) & ~t3
        if M & S == S and not M & K:
            M &= ~S
            acc += 1
    return acc, act


# ---------------------------------------------------------------- safe fallback


def fallback(g, S, K, k, pos, act, M, copies, prog):
    """Point-by-point: emitter 1 sweeps active alone, emitter 0 flashes on at each target cell."""
    P = g.P
    pos = list(pos)
    act = list(act)
    if any(act):
        prog.append(['T' if act[t] else '-' for t in range(6)])
        act = [False] * 6
    # simulate the state change of an all-off tick: nothing happens
    cur_missing = S & ~M

    def step_towards(t, target):
        d = (target - pos[t]) % P
        if d == 0:
            return '-'
        if d <= P - d:
            pos[t] = (pos[t] + 1) % P
            return 'F'
        pos[t] = (pos[t] - 1) % P
        return 'B'

    while copies < k:
        todo = cur_missing
        while todo:
            # nearest missing cell
            best = None
            mm = todo
            while mm:
                low = mm & -mm
                c = low.bit_length() - 1
                mm ^= low
                p0, p1 = g.cellpos[0][c], g.cellpos[1][c]
                d = max(g.rd[pos[0]][p0] + (1 if act[0] else 0), g.rd[pos[1]][p1])
                if best is None or d < best[0]:
                    best = (d, c, p0, p1)
            _, c, p0, p1 = best
            # move: emitter 0 must be off; emitter 1 may be on (alone it creates nothing)
            while True:
                line = ['-'] * 6
                if act[0]:
                    line[0] = 'T'
                    act[0] = False
                else:
                    line[0] = step_towards(0, p0)
                if pos[1] != p1:
                    line[1] = step_towards(1, p1)
                elif not act[1]:
                    line[1] = 'T'
                    act[1] = True
                if line == ['-'] * 6:
                    break
                prog.append(line)
            line = ['-'] * 6
            line[0] = 'T'
            act[0] = True
            prog.append(line)
            todo &= ~(1 << c)
        copies += 1
        cur_missing = S
    prog.append(['T' if act[t] else '-' for t in range(6)])
    return prog


# ---------------------------------------------------------------- beam search


def axis_combos(g, e, f, pe, ae, pf, af, phi_e, phi_f):
    """All 16 instruction pairs for the two emitters of one axis."""
    P = g.P
    re, rf = g.ray[e], g.ray[f]
    oe = []
    for o in OPTS:
        if o == '-':
            q, a = pe, ae
        elif o == 'F':
            q, a = (pe + 1) % P, ae
        elif o == 'B':
            q, a = (pe - 1) % P, ae
        else:
            q, a = pe, not ae
        oe.append((o, q, a, re[q] if a else 0, phi_e[q] + (0 if a else 1)))
    of = []
    for o in OPTS:
        if o == '-':
            q, a = pf, af
        elif o == 'F':
            q, a = (pf + 1) % P, af
        elif o == 'B':
            q, a = (pf - 1) % P, af
        else:
            q, a = pf, not af
        of.append((o, q, a, rf[q] if a else 0, phi_f[q] + (0 if a else 1)))
    res = []
    for o1, q1, a1, m1, h1 in oe:
        for o2, q2, a2, m2, h2 in of:
            res.append((o1, o2, q1, a1, q2, a2, m1 | m2, m1 & m2, h1 + h2))
    return res


def phi_table(g, t, missing):
    """phi[p]: ring distance from p to the nearest useful position whose line has a missing cell."""
    P = g.P
    targets = [p for p, m in g.linepos[t] if m & missing]
    rd = g.rd
    if not targets:
        return [0] * P
    return [min(rd[p][q] for q in targets) for p in range(P)]


def beam(g, S, K, k, W=8, stall_limit=None):
    P = g.P
    nS = S.bit_count()
    BIG = 1 << 20
    if stall_limit is None:
        stall_limit = 4 * g.R + 6
    start = (tuple(t * g.R for t in range(6)), (False,) * 6, 0, 0)
    # beam entries: (score, pos, act, M, copies, hist) ; hist = linked list (line, parent)
    beamlist = [(0, start[0], start[1], 0, 0, None)]
    best_progress = 0
    stall = 0
    ticks = 0
    while True:
        cand = {}
        for _, pos, act, M, copies, hist in beamlist:
            missing = S & ~M
            phis = [phi_table(g, t, missing) for t in range(6)]
            ax = []
            for e, f in AXES:
                ax.append(axis_combos(g, e, f, pos[e], act[e], pos[f], act[f], phis[e], phis[f]))
            A, B, C = ax
            for a in A:
                a1, a2 = a[6], a[7]
                for b in B:
                    b1, b2 = b[6], b[7]
                    t1 = a1 | b1
                    t2 = a2 | b2 | (a1 & b1)
                    t3 = (a2 & b1) | (b2 & a1)
                    hab = a[8] + b[8]
                    for c in C:
                        c1, c2 = c[6], c[7]
                        T3 = t3 | (t2 & c1) | (c2 & t1)
                        C2 = (t2 | c2 | (t1 & c1)) & ~T3
                        if C2 & K:
                            continue
                        nM = (M | C2) & ~T3 & S
                        ncp = copies
                        if nM == S:
                            nM = 0
                            ncp += 1
                        sc = ncp * BIG + nM.bit_count() * 64 - (hab + c[8])
                        npos = (a[2], b[2], c[2], a[4], b[4], c[4])
                        nact = (a[3], b[3], c[3], a[5], b[5], c[5])
                        key = (npos, nact, nM, ncp)
                        old = cand.get(key)
                        if old is None or old[0] < sc:
                            line = (a[0], b[0], c[0], a[1], b[1], c[1])
                            cand[key] = (sc, hist, line)
        ticks += 1
        items = sorted(cand.items(), key=lambda kv: -kv[1][0])[:W]
        beamlist = []
        for (npos, nact, nM, ncp), (sc, hist, line) in items:
            nh = (line, hist)
            if ncp >= k:
                return unwind(nh), nact
            beamlist.append((sc, npos, nact, nM, ncp, nh))
        prog_val = max(e[4] * (nS + 1) + e[3].bit_count() for e in beamlist)
        if prog_val > best_progress:
            best_progress = prog_val
            stall = 0
        else:
            stall += 1
            if stall > stall_limit:
                # hand the best state over to the safe method
                sc, pos, act, M, copies, hist = beamlist[0]
                prog = unwind(hist)
                return fallback(g, S, K, k, pos, act, M, copies, prog), None


def unwind(h):
    out = []
    while h is not None:
        out.append(list(h[0]))
        h = h[1]
    out.reverse()
    return out


def make_program(g, S, K, k, W=8):
    prog, act = beam(g, S, K, k, W)
    if act is not None and any(act):
        prog.append(['T' if a else '-' for a in act])
    return prog


def solve(text):
    cases = parse(text)
    geos = {}
    out = []
    for R, k, pat in cases:
        g = geos.get(R)
        if g is None:
            g = geos[R] = Geo(R)
        S, K = pattern_masks(g, pat)
        prog = make_program(g, S, K, k)
        acc, act = simulate(g, S, K, prog)
        if acc < k or any(act):
            prog = fallback(g, S, K, k, [t * R for t in range(6)], [False] * 6, 0, 0, [])
        if out:
            out.append('')
        out.extend(' '.join(l) for l in prog)
    return out
