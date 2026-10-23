from common import *
import heapq
import time

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
        self.reach = [[ray[t][(p - 1) % P] | ray[t][p] | ray[t][(p + 1) % P] for p in range(P)] for t in range(6)]
        self.reach2 = [[self.reach[t][(p - 1) % P] | self.reach[t][(p + 1) % P] for p in range(P)] for t in range(6)]
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
    # clear any matter left on skirt cells: three beams meeting in one cell, nothing else active
    dirty = M & K
    while dirty:
        low = dirty & -dirty
        c = low.bit_length() - 1
        dirty ^= low
        tg = [g.cellpos[t][c] for t in range(3)]
        while True:
            line = ['-'] * 6
            for t in range(3):
                if pos[t] != tg[t]:
                    d = (tg[t] - pos[t]) % P
                    if d <= P - d:
                        pos[t] = (pos[t] + 1) % P
                        line[t] = 'F'
                    else:
                        pos[t] = (pos[t] - 1) % P
                        line[t] = 'B'
            if line == ['-'] * 6:
                break
            prog.append(line)
        prog.append(['T', 'T', 'T', '-', '-', '-'])
        prog.append(['T', 'T', 'T', '-', '-', '-'])
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


def axis_combos(g, e, f, pe, ae, pf, af, phi_e, phi_f, lk):
    """All 16 instruction pairs for the two emitters of one axis."""
    P = g.P
    res_e = []
    for t, p0, a0, phi in ((e, pe, ae, phi_e), (f, pf, af, phi_f)):
        rt = g.ray[t]
        ra = g.reach[t]
        ra2 = g.reach2[t]
        lst = []
        for o in OPTS:
            if o == '-':
                q, a = p0, a0
            elif o == 'F':
                q, a = (p0 + 1) % P, a0
            elif o == 'B':
                q, a = (p0 - 1) % P, a0
            else:
                q, a = p0, not a0
            if a:
                ls = (rt[(q - 1) % P], rt[q], rt[(q + 1) % P])
            else:
                ls = (rt[q],)
            lst.append((o, q, a, rt[q] if a else 0, phi[q] + (0 if a else 1), ra[q] if a else rt[q], ls, ra2[q] if a else ra[q]))
        res_e.append(lst)
    res = []
    for o1, q1, a1, m1, h1, r1, l1, s1 in res_e[0]:
        for o2, q2, a2, m2, h2, r2, l2, s2 in res_e[1]:
            pl = []
            if r1 & r2:
                for m in l1:
                    if m and m in l2:
                        v = lk.get(m)
                        if v is not None:
                            pl.append(v)
            res.append((o1, o2, q1, a1, q2, a2, m1 | m2, m1 & m2, h1 + h2, r1 | r2, pl, s1 | s2))
    return res


def phi_table(g, t, missing):
    """phi[p]: ring distance from p to the nearest useful position whose line has a missing cell."""
    P = g.P
    targets = [p for p, m in g.linepos[t] if m & missing]
    rd = g.rd
    if not targets:
        return [0] * P
    return [min(rd[p][q] for q in targets) for p in range(P)]


def beam(g, S, K, k, W=8, stall_limit=None, wopp=16, wcov=64, tb=1, wk=None, maxk=4,
         pos0=None, act0=None, target=False, maxdepth=None, wret=8, w2=0, sweep=None):
    """Beam search over ticks. With target=True: find a closed walk from (pos0, act0) back to the
    same configuration that submits one pattern on its last tick; returns None if none is found."""
    P = g.P
    nS = S.bit_count()
    BIG = 1 << 24
    if stall_limit is None:
        stall_limit = 4 * g.R + 6
    lk = {}
    for t in range(3):
        for p, lm in g.linepos[t]:
            if (lm & K).bit_count() <= maxk and lm & S:
                lk[lm] = (lm & K, lm & S)
    if pos0 is None:
        pos0 = tuple(t * g.R for t in range(6))
        act0 = (False,) * 6
    pos0 = tuple(pos0)
    act0 = tuple(act0)
    rd = g.rd
    beamlist = [(0, pos0, act0, 0, 0, None, 0 if sweep else 2)]
    if sweep:
        sw_ax, sx, sx3 = sweep
        sw_e, sw_f = AXES[sw_ax]
        ix = {p: i for i, p in enumerate(sx)}
        iend = len(sx) - 1

        def stepto(cur, tgt):
            d = (tgt - cur) % P
            if d == 0:
                return '-'
            return 'F' if d <= P - d else 'B'
    best_progress = 0
    stall = 0
    ticks = 0
    cnt = 0
    REL = S | K
    wkk = wk or 0
    while True:
        heap = []
        HW = 3 * W
        thr = -1 << 62
        for _, pos, act, M, copies, hist, sph in beamlist:
            missing = S & ~M
            phis = [phi_table(g, t, missing) for t in range(6)]
            if target:
                cov = nS - missing.bit_count()
                for t in range(6):
                    rt = rd[pos0[t]]
                    ph = phis[t]
                    phis[t] = [ph[q] + (wret * rt[q] * (cov + 1)) // (nS + 1) for q in range(P)]
            ax = []
            for i, (e, f) in enumerate(AXES):
                ax.append(axis_combos(g, e, f, pos[e], act[e], pos[f], act[f], phis[e], phis[f], lk))
            phmap = None
            if sph < 2:
                pe, pf = pos[sw_e], pos[sw_f]
                phmap = {}
                if sph == 0:
                    if pe == sx[0] and pf == sx3[0]:
                        phmap[('T', 'T')] = 2 if iend == 0 else 1
                        phmap[('-', '-')] = 0
                    else:
                        phmap[(stepto(pe, sx[0]), stepto(pf, sx3[0]))] = 0
                else:
                    i = ix[pe]
                    phmap[('-', '-')] = 1
                    phmap[('T', 'T')] = 1
                    if i < iend:
                        phmap[(stepto(pe, sx[i + 1]), stepto(pf, sx3[i + 1]))] = 2 if i + 1 == iend else 1
                ax[sw_ax] = [cmb for cmb in ax[sw_ax] if (cmb[0], cmb[1]) in phmap]
            A, B, C = ax
            base_cp = copies * BIG
            for a in A:
                a1, a2, aR, aL = a[6], a[7], a[9], a[10]
                for b in B:
                    b1, b2, bR = b[6], b[7], b[9]
                    t1 = a1 | b1
                    t2 = a2 | b2 | (a1 & b1)
                    t3 = (a2 & b1) | (b2 & a1)
                    hab = a[8] + b[8]
                    RAB = aR & bR
                    RAoB = aR | bR
                    bL = b[10]
                    RAB2 = a[11] & b[11]
                    RAoB2 = a[11] | b[11]
                    for c in C:
                        c1, c2 = c[6], c[7]
                        T3 = t3 | (t2 & c1) | (c2 & t1)
                        C2 = (t2 | c2 | (t1 & c1)) & ~T3
                        if C2 & K and wk is None:
                            continue
                        nM = (M | C2) & ~T3 & REL
                        if nM == S:
                            if target:
                                npos = (a[2], b[2], c[2], a[4], b[4], c[4])
                                nact = (a[3], b[3], c[3], a[5], b[5], c[5])
                                if npos == pos0 and nact == act0:
                                    return unwind(((a[0], b[0], c[0], a[1], b[1], c[1]), hist)), nact
                                continue
                            sc = base_cp + BIG
                            nM = 0
                            ncp = copies + 1
                            opp = nS * (wopp + w2)
                        else:
                            ncp = copies
                            sc = base_cp + (nM & S).bit_count() * wcov - (hab + c[8])
                            if nM & K:
                                sc -= (nM & K).bit_count() * wkk
                            if sc + nS * (wopp + w2) <= thr:
                                continue
                            cR = c[9]
                            ox = RAB | (RAoB & cR)
                            if aL:
                                ro = bR | cR
                                for Kl, Sl in aL:
                                    if not Kl & ~ro:
                                        ox |= Sl
                            if bL:
                                ro = aR | cR
                                for Kl, Sl in bL:
                                    if not Kl & ~ro:
                                        ox |= Sl
                            if c[10]:
                                for Kl, Sl in c[10]:
                                    if not Kl & ~RAoB:
                                        ox |= Sl
                            mis = S & ~nM
                            opp = (ox & mis).bit_count() * wopp
                            if w2:
                                opp += ((RAB2 | (RAoB2 & c[11])) & mis).bit_count() * w2
                        sc += opp
                        if sc <= thr:
                            continue
                        cnt += tb
                        if phmap is None:
                            nph = 2
                        else:
                            cmb = (a, b, c)[sw_ax]
                            nph = phmap[(cmb[0], cmb[1])]
                        item = (sc, cnt, (a[2], b[2], c[2], a[4], b[4], c[4]), (a[3], b[3], c[3], a[5], b[5], c[5]),
                                nM, ncp, hist, (a[0], b[0], c[0], a[1], b[1], c[1]), nph)
                        if len(heap) < HW:
                            heapq.heappush(heap, item)
                            if len(heap) == HW:
                                thr = heap[0][0]
                        else:
                            heapq.heapreplace(heap, item)
                            thr = heap[0][0]
        ticks += 1
        if target and (not heap or ticks >= maxdepth):
            return None
        heap.sort(reverse=True)
        seen = set()
        beamlist = []
        for sc, _, npos, nact, nM, ncp, hist, line, nph in heap:
            key = (npos, nact, nM, nph)
            if key in seen:
                continue
            seen.add(key)
            nh = (line, hist)
            if ncp >= k:
                return unwind(nh), nact
            beamlist.append((sc, npos, nact, nM, ncp, nh, nph))
            if len(beamlist) >= W:
                break
        if target:
            continue
        prog_val = max(e[4] * (nS + 1) + (e[3] & S).bit_count() - (e[3] & K).bit_count() for e in beamlist)
        if prog_val > best_progress:
            best_progress = prog_val
            stall = 0
        else:
            stall += 1
            if stall > stall_limit:
                sc, pos, act, M, copies, hist, _ = beamlist[0]
                prog = unwind(hist)
                return fallback(g, S, K, k, pos, act, M, copies, prog), None


def accept_points(g, S, K, prog):
    """For each submission: (number of lines so far, positions, active flags)."""
    pos = [t * g.R for t in range(6)]
    act = [False] * 6
    M = 0
    P = g.P
    res = []
    for i, line in enumerate(prog):
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
            res.append((i + 1, tuple(pos), tuple(act)))
    return res


def unwind(h):
    out = []
    while h is not None:
        out.append(list(h[0]))
        h = h[1]
    out.reverse()
    return out


def finish(prog, act):
    if act is not None and any(act):
        prog = prog + [['T' if x else '-' for x in act]]
    return prog


def make_program(g, S, K, k, **kw):
    return finish(*beam(g, S, K, k, **kw))


def valid(g, S, K, k, prog):
    acc, act = simulate(g, S, K, prog)
    return acc >= k and not any(act)


VARIANTS = [dict(tb=-1), dict(wopp=16, w2=4), dict(tb=-1, wopp=8, w2=4), dict(wopp=8), dict(tb=-1, wopp=24),
            dict(W=12, w2=2), dict(tb=-1, W=12, wopp=12), dict(wopp=20, wcov=48, w2=3), dict(tb=-1, wopp=10, wcov=80)]


def solve(text, budget=100.0):
    T0 = time.process_time()
    cases = parse(text)
    geos = {}
    data = []
    progs = []
    for R, k, pat in cases:
        g = geos.get(R)
        if g is None:
            g = geos[R] = Geo(R)
        S, K = pattern_masks(g, pat)
        data.append((g, S, K, k))
        prog = make_program(g, S, K, k)
        if not valid(g, S, K, k, prog):
            prog = fallback(g, S, K, k, [t * R for t in range(6)], [False] * 6, 0, 0, [])
        progs.append(prog)

    def left():
        return budget - (time.process_time() - T0)

    # exact short cycles: one configuration held, or two alternating ones
    for i, (g, S, K, k) in enumerate(data):
        if k < 2 or left() < budget * 0.4:
            break
        pts = accept_points(g, S, K, progs[i])
        gap = pts[1][0] - pts[0][0] if len(pts) > 1 else 99
        if gap <= 1:
            continue
        cands, maxcov = cycle_search(g, S, K, k, static_only=True)
        if gap >= 3 and 2 * maxcov >= S.bit_count() and g.R <= 6:
            c2, _ = cycle_search(g, S, K, k, deadline=time.time() + min(2.0, max(0.1, left() - budget * 0.4)))
            cands += c2
        for cost, stat, first1, specs in cands:
            if cost + 1 >= len(progs[i]):
                continue
            pr = cycle_program(g, S, K, k, stat, first1, specs)
            if pr is not None and len(pr) < len(progs[i]) and valid(g, S, K, k, pr):
                progs[i] = pr
    # more beam searches with other settings while time remains
    for kw in VARIANTS:
        for i in sorted(range(len(data)), key=lambda j: -len(progs[j])):
            if left() < 0:
                break
            g, S, K, k = data[i]
            pr = make_program(g, S, K, k, **kw)
            if len(pr) < len(progs[i]) and valid(g, S, K, k, pr):
                progs[i] = pr
    out = []
    for prog in progs:
        if out:
            out.append('')
        out.extend(' '.join(l) for l in prog)
    return out


# ---------------------------------------------------------------- short exact cycles


def emitter_cycle_opts(g, t, useful, static_only=False):
    """Two-phase behaviours of one emitter: (mask1, mask2, pos1, act1, pos2, act2)."""
    start = t * g.R
    P = g.P
    lines = sorted(g.linepos[t], key=lambda pm: (pm[0] - start + P // 2) % P)
    opts = [(0, 0, start, False, start, False)]
    for i, (p, m) in enumerate(lines):
        if m & useful:
            opts.append((m, m, p, True, p, True))
            if not static_only:
                opts.append((m, 0, p, True, p, False))
                opts.append((0, m, p, False, p, True))
        if not static_only and i + 1 < len(lines):
            q, m2 = lines[i + 1]
            if (m | m2) & useful:
                opts.append((m, m2, p, True, q, True))
                opts.append((m2, m, q, True, p, True))
    return opts


def axis_cycle_sigs(g, e, f, useful, static_only=False):
    rd = g.rd
    se, sf = e * g.R, f * g.R
    oe = emitter_cycle_opts(g, e, useful, static_only)
    of = emitter_cycle_opts(g, f, useful, static_only)
    sigs = {}
    for x in oe:
        de1, de2 = rd[se][x[2]], rd[se][x[4]]
        for y in of:
            key = (x[0] | y[0], x[0] & y[0], x[1] | y[1], x[1] & y[1])
            c1 = max(de1, rd[sf][y[2]])
            c2 = max(de2, rd[sf][y[4]])
            cur = sigs.get(key)
            if cur is None:
                sigs[key] = [c1, (x, y), c2, (x, y)]
            else:
                if c1 < cur[0]:
                    cur[0], cur[1] = c1, (x, y)
                if c2 < cur[2]:
                    cur[2], cur[3] = c2, (x, y)
    return list(sigs.items())


def cycle_search(g, S, K, k, static_only=False, deadline=None, keep=12):
    """Pairs of configurations (X1, X2), one tick apart, whose 2-hit sets cover the pattern
    without touching the skirt. Returns candidates (setup, phase, specs) sorted by setup."""
    useful = S | K
    axs = [axis_cycle_sigs(g, e, f, useful, static_only) for e, f in AXES]
    order = sorted(range(3), key=lambda i: -len(axs[i]))
    A, B, C = [axs[i] for i in order]
    best = []
    it = 0
    maxcov = 0
    for (a, ra) in A:
        ao1, at1, ao2, at2 = a
        for (b, rb) in B:
            bo1, bt1, bo2, bt2 = b
            ge1 = ao1 | bo1
            ge2 = at1 | bt1 | (ao1 & bo1)
            ge3 = (at1 & bo1) | (bt1 & ao1)
            p0, p1, p2 = ~ge1, ge1 & ~ge2, ge2 & ~ge3
            he1 = ao2 | bo2
            he2 = at2 | bt2 | (ao2 & bo2)
            he3 = (at2 & bo2) | (bt2 & ao2)
            if ge3 & he3 & S:
                continue
            q0, q1, q2 = ~he1, he1 & ~he2, he2 & ~he3
            it += 1
            if deadline is not None and it & 255 == 0 and time.time() > deadline:
                return finish_cands(best, order), maxcov
            for (c, rc) in C:
                co1, ct1, co2, ct2 = c
                C2a = (p2 & ~co1) | (p1 & co1 & ~ct1) | (p0 & ct1)
                if C2a & K:
                    continue
                C2b = (q2 & ~co2) | (q1 & co2 & ~ct2) | (q0 & ct2)
                if C2b & K:
                    continue
                if static_only:
                    cv = (C2a & S).bit_count()
                    if cv > maxcov:
                        maxcov = cv
                if (C2a | C2b) & S != S:
                    continue
                stat = 1 if C2a & S == S else (2 if C2b & S == S else 0)
                s1 = max(ra[0], rb[0], rc[0])
                s2 = max(ra[2], rb[2], rc[2])
                if stat:
                    cost = (s1 if stat == 1 else s2) + k
                else:
                    cost = min(s1, s2) + 2 * k
                item = (cost, stat, s1 <= s2, ra, rb, rc)
                if len(best) < keep or item[0] < best[-1][0]:
                    best.append(item)
                    best.sort(key=lambda x: x[0])
                    del best[keep:]
    return finish_cands(best, order), maxcov


def finish_cands(best, order):
    out = []
    for cost, stat, first1, ra, rb, rc in best:
        reps = [None] * 3
        reps[order[0]], reps[order[1]], reps[order[2]] = ra, rb, rc
        specs = [None] * 6
        for i, (e, f) in enumerate(AXES):
            rep = reps[i][1] if (stat == 1 or (stat == 0 and first1)) else reps[i][3]
            specs[e], specs[f] = rep
        out.append((cost, stat, first1, specs))
    return out


def cycle_program(g, S, K, k, stat, first1, specs):
    """Program: move to the first configuration, then alternate (or hold) until k submissions."""
    P = g.P
    X = [(sp[2], sp[3]) if (stat == 1 or (stat == 0 and first1)) else (sp[4], sp[5]) for sp in specs]
    Y = [(sp[4], sp[5]) if (stat == 0 and first1) else (sp[2], sp[3]) for sp in specs]
    if stat:
        Y = X
    pos = [t * g.R for t in range(6)]
    prog = []
    while True:
        line = ['-'] * 6
        for t in range(6):
            d = (X[t][0] - pos[t]) % P
            if d:
                if d <= P - d:
                    pos[t] = (pos[t] + 1) % P
                    line[t] = 'F'
                else:
                    pos[t] = (pos[t] - 1) % P
                    line[t] = 'B'
        if line == ['-'] * 6:
            break
        prog.append(line)
    prog.append(['T' if X[t][1] else '-' for t in range(6)])
    cur, nxt = X, Y

    def trans(a, b):
        line = []
        for t in range(6):
            if a[t][1] != b[t][1]:
                line.append('T')
            elif a[t][0] == b[t][0]:
                line.append('-')
            elif (a[t][0] + 1) % P == b[t][0]:
                line.append('F')
            else:
                line.append('B')
        return line

    fw, bw = trans(X, Y), trans(Y, X)
    # simulate until k submissions
    limit = len(prog) + 2 * k + 6
    flip = True
    while len(prog) < limit:
        acc, _ = simulate(g, S, K, prog)
        if acc >= k:
            break
        prog.append(fw if flip else bw)
        flip = not flip
    acc, act = simulate(g, S, K, prog)
    if acc < k:
        return None
    return finish(prog, act)


def emitter_moves(P, p, a):
    """(instruction, new pos, new active) for one emitter."""
    return (('-', p, a), ('F', (p + 1) % P, a), ('B', (p - 1) % P, a), ('T', p, not a))


def hits(g, pos, act):
    t1 = t2 = t3 = 0
    for t in range(6):
        if act[t]:
            m = g.ray[t][pos[t]]
            t3 |= t2 & m
            t2 |= t1 & m
            t1 |= m
    return t2 & ~t3, t3


def successors(g, K, pos, act):
    """All K-safe one-tick successors: (line, pos, act, C2, C3)."""
    P = g.P
    per = []
    for t in range(6):
        lst = []
        for ins, q, a in emitter_moves(P, pos[t], act[t]):
            lst.append((ins, q, a, g.ray[t][q] if a else 0))
        per.append(lst)
    out = []
    for e0 in per[0]:
        for e3 in per[3]:
            a1, a2 = e0[3] | e3[3], e0[3] & e3[3]
            for e1 in per[1]:
                for e4 in per[4]:
                    b1, b2 = e1[3] | e4[3], e1[3] & e4[3]
                    t1 = a1 | b1
                    t2 = a2 | b2 | (a1 & b1)
                    t3 = (a2 & b1) | (b2 & a1)
                    for e2 in per[2]:
                        for e5 in per[5]:
                            c1, c2 = e2[3] | e5[3], e2[3] & e5[3]
                            T3 = t3 | (t2 & c1) | (c2 & t1)
                            C2 = (t2 | c2 | (t1 & c1)) & ~T3
                            if C2 & K:
                                continue
                            out.append(((e0[0], e1[0], e2[0], e3[0], e4[0], e5[0]),
                                        (e0[1], e1[1], e2[1], e3[1], e4[1], e5[1]),
                                        (e0[2], e1[2], e2[2], e3[2], e4[2], e5[2]), C2, T3))
    return out


def step_ins(P, s, d):
    """Instruction taking emitter state s=(p,a) to d, or None if not adjacent."""
    if s == d:
        return '-'
    if s[1] == d[1]:
        if (s[0] + 1) % P == d[0]:
            return 'F'
        if (s[0] - 1) % P == d[0]:
            return 'B'
        return None
    if s[0] == d[0]:
        return 'T'
    return None


def anchored_cycles(g, S, K, pos, act, pmax=3, deadline=None):
    """Shortest closed walk X -> ... -> X (length 3) covering S, X = (pos, act). Returns lines or None."""
    P = g.P
    X = tuple(zip(pos, act))
    C2X, C3X = hits(g, pos, act)
    sx = successors(g, K, pos, act)
    # per-emitter states adjacent to X (as predecessor)
    predX = []
    for t in range(6):
        lst = []
        for ins, q, a in emitter_moves(P, pos[t], act[t]):
            lst.append((q, a))
        predX.append(lst)
    best = None
    for line1, npos, nact, C2Y, C3Y in sx:
        covY = ((C2Y & ~C3X) | C2X) & S  # coverage after Y, X order handled by simulation later
        need = S & ~(C2Y | C2X)
        if not need:
            continue
        # Z adjacent to Y and to X
        cand = []
        for t in range(6):
            yz = (npos[t], nact[t])
            lst = []
            for q, a in predX[t]:
                i1 = step_ins(P, yz, (q, a))
                if i1 is None:
                    continue
                i2 = step_ins(P, (q, a), X[t])
                if i2 is None:
                    continue
                lst.append((i1, i2, q, a, g.ray[t][q] if a else 0))
            if not lst:
                break
            cand.append(lst)
        else:
            for z0 in cand[0]:
                for z3 in cand[3]:
                    a1, a2 = z0[4] | z3[4], z0[4] & z3[4]
                    for z1 in cand[1]:
                        for z4 in cand[4]:
                            b1, b2 = z1[4] | z4[4], z1[4] & z4[4]
                            t1 = a1 | b1
                            t2 = a2 | b2 | (a1 & b1)
                            t3 = (a2 & b1) | (b2 & a1)
                            for z2 in cand[2]:
                                for z5 in cand[5]:
                                    c1, c2 = z2[4] | z5[4], z2[4] & z5[4]
                                    T3 = t3 | (t2 & c1) | (c2 & t1)
                                    C2 = (t2 | c2 | (t1 & c1)) & ~T3
                                    if C2 & K or need & ~C2:
                                        continue
                                    zs = (z0, z1, z2, z3, z4, z5)
                                    l2 = tuple(z[0] for z in zs)
                                    l3 = tuple(z[1] for z in zs)
                                    return [list(line1), list(l2), list(l3)]
        if deadline is not None and time.time() > deadline:
            return None
    return None


def sweep_specs(g, S, axis):
    """For each sweep direction: positions of the pair emitters for every line from the first to
    the last line holding pattern cells."""
    e, f = AXES[axis]
    P = g.P
    start = e * g.R
    le = sorted(g.linepos[e], key=lambda pm: (pm[0] - start + P // 2) % P)
    posf = {m: p for p, m in g.linepos[f]}
    seq = [(p, posf[m], m) for p, m in le]
    idx = [i for i, (p, q, m) in enumerate(seq) if m & S]
    if not idx:
        return []
    seq = seq[idx[0]:idx[-1] + 1]
    out = []
    for sq in (seq, seq[::-1]):
        out.append((axis, [p for p, q, m in sq], [q for p, q, m in sq]))
    return out
