# Level 6 validator: ported from the official visualizer (data/sandbox-level-6.html).
#
# Input : N, then N cases "R rows cols count" + the pattern (rows lines), blank line between.
# Output: N programs separated by one empty line; each line = 6 instructions from {-,T,F,B}
#         separated by single spaces.
# A program is valid if simulating it (level 4/5 rules) submits the pattern at least
# `count` times (visualizer: "Simulation accepts X of Y required patterns" when X < Y).
# ASSUMPTION: all emitters must also be inactive when a program ends (see check()).
# Score = total number of instruction lines over all programs (lower is better).

SCORE = 'min'

VALID = ('-', 'T', 'F', 'B')

# Overlay (doubled) coordinates, (dc, dr), as in the visualizer.
DIR_TO = {
    'E': (2, 0), 'SE': (1, 1), 'SW': (-1, 1),
    'W': (-2, 0), 'NW': (-1, -1), 'NE': (1, -1),
}
# Firing direction of emitter track t (0..5).
FIRE_OV = [(2, 0), (1, 1), (-1, 1), (-2, 0), (-1, -1), (1, -1)]


def _parse_input(text):
    lines = [l.rstrip() for l in text.replace('\r', '').split('\n')]
    p = 0

    def nxt():
        nonlocal p
        while p < len(lines) and not lines[p].strip():
            p += 1
        if p >= len(lines):
            raise ValueError('input ended early')
        l = lines[p]
        p += 1
        return l

    n = int(nxt().split()[0])
    cases = []
    for _ in range(n):
        hdr = nxt().split()
        r, rows, cols, count = int(hdr[0]), int(hdr[1]), int(hdr[2]), int(hdr[3])
        pat = [nxt().strip() for _ in range(rows)]
        cases.append((r, rows, cols, count, pat))
    return cases


class _Geom(object):
    """Board geometry for one board radius (visualizer radius = R + 1)."""

    def __init__(self, R):
        radius = R + 1
        rows = 2 * radius - 1
        cols = 4 * radius - 3
        o_cols = cols
        self.rows, self.cols = rows, cols

        def in_grid(c, r):
            if r < 0 or r >= rows:
                return False
            if (r + c + radius + 1) % 2 != 0:
                return False
            if r < radius:
                return c + r >= radius - 1 and c - r <= o_cols - radius + 1
            return c + (2 * radius - 1 - r) >= radius - 1 and c + r - 2 * radius + 1 < o_cols - radius + 1

        # Cell kinds as in the visualizer's baseGrid: 'O' playable, '#' rail, else not a cell.
        playable = bytearray(rows * cols)
        for r in range(rows):
            r_rail = r == 0 or r == rows - 1
            for c in range(cols):
                if (r + c + radius + 1) % 2 != 0:
                    continue
                if r < radius:
                    c_rail = c == radius - 1 - r or c == cols - 1 - radius + 1 + r
                    if c + r >= radius - 1 and c - r <= cols - radius + 1:
                        playable[r * cols + c] = 0 if (r_rail or c_rail) else 1
                else:
                    c_rail = c == radius - 1 + r - 2 * radius + 2 or c == cols - 1 + radius - 1 - r
                    if c + 2 * radius - 1 - r >= radius - 1 and c + r - 2 * radius + 1 < cols - radius + 1:
                        playable[r * cols + c] = 0 if (r_rail or c_rail) else 1
        self.playable = playable

        perimeter = []
        if radius > 1:
            c, r = 0, radius - 1
            for d in ('NE', 'E', 'SE', 'SW', 'W', 'NW'):
                dc, dr = DIR_TO[d]
                for _ in range(radius - 1):
                    perimeter.append((c, r))
                    c += dc
                    r += dr
        self.perimeter = perimeter

        # ray[idx][t]: playable cells (flat index) hit by track t standing at perimeter idx.
        # Rail cells on the ray are ignored by the matter rules, so they are dropped here.
        ray = []
        for c0, r0 in perimeter:
            per_t = []
            for dc, dr in FIRE_OV:
                cells = []
                c, r = c0 + dc, r0 + dr
                while in_grid(c, r):
                    k = r * cols + c
                    if playable[k]:
                        cells.append(k)
                    c += dc
                    r += dr
                per_t.append(cells)
            ray.append(per_t)
        self.ray = ray
        self.edge = max(radius - 1, 1)


def _simulate(geom, pat, prog):
    """(submitted patterns, final active flags), as in the visualizer's applyEmitterStep loop."""
    rows, cols = geom.rows, geom.cols
    ncell = rows * cols
    # role: 1 = pattern matter cell, 2 = skirting 'O' (adjacent to pattern matter), 0 = don't care
    role = bytearray(ncell)
    pcells = []
    sizes_ok = len(pat) == rows and all(len(l) == cols for l in pat)
    if sizes_ok:
        for r in range(rows):
            row = pat[r]
            for c in range(cols):
                ch = row[c]
                if ch == 'M':
                    role[r * cols + c] = 1
                    pcells.append(r * cols + c)
                elif ch == 'O':
                    for dc, dr in FIRE_OV:
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < rows and 0 <= cc < cols and pat[rr][cc] == 'M':
                            role[r * cols + c] = 2
                            break
    npat = len(pcells)
    can_accept = sizes_ok and npat > 0
    grid = bytearray(ncell)  # 1 = matter
    cnt = [0] * ncell
    ray = geom.ray
    plen = len(geom.perimeter)
    idx = [t * geom.edge if plen else 0 for t in range(6)]
    active = [False] * 6
    pm = 0  # pattern matter cells currently holding matter
    hm = 0  # skirting cells currently holding matter
    accepted = 0
    for line in prog:
        for t in range(6):
            ins = line[t]
            if ins == 'F' and plen:
                idx[t] = (idx[t] + 1) % plen
            elif ins == 'B' and plen:
                idx[t] = (idx[t] + plen - 1) % plen
            elif ins == 'T':
                active[t] = not active[t]
        touched = []
        for t in range(6):
            if active[t] and plen:
                for k in ray[idx[t]][t]:
                    if cnt[k] == 0:
                        touched.append(k)
                    cnt[k] += 1
        for k in touched:
            n = cnt[k]
            cnt[k] = 0
            if n == 2:
                if not grid[k]:
                    grid[k] = 1
                    rk = role[k]
                    if rk == 1:
                        pm += 1
                    elif rk == 2:
                        hm += 1
            elif n >= 3:
                if grid[k]:
                    grid[k] = 0
                    rk = role[k]
                    if rk == 1:
                        pm -= 1
                    elif rk == 2:
                        hm -= 1
        if can_accept and pm == npat and hm == 0:
            for k in pcells:
                grid[k] = 0
            pm = 0
            accepted += 1
    return accepted, active


def check(input_text, output_text):
    try:
        cases = _parse_input(input_text)
    except Exception as e:
        return (False, 'cannot parse input: %s' % e)
    n = len(cases)

    raw = output_text.replace('\r\n', '\n').replace('\r', '\n').rstrip()
    if not raw.strip():
        return (False, 'empty output')
    lines = raw.split('\n')

    # Split into programs separated by exactly one empty line.
    progs = []  # list of (first_line_no, [tokens...])
    cur = None
    blank_run = 0
    for i, line in enumerate(lines, 1):
        s = line.rstrip()
        if not s.strip():
            if cur is None:
                return (False, 'line %d: empty line before the first program' % i)
            blank_run += 1
            if blank_run > 1:
                return (False, 'line %d: more than one empty line between programs' % i)
            continue
        if blank_run or cur is None:
            cur = (i, [])
            progs.append(cur)
            blank_run = 0
        toks = s.split(' ')
        if len(toks) != 6:
            return (False, 'program %d, line %d: expected 6 instructions separated by single spaces, got %r'
                    % (len(progs), i, line))
        for t in toks:
            if t not in VALID:
                return (False, 'program %d, line %d: unknown instruction %r (allowed: - T F B)'
                        % (len(progs), i, t))
        cur[1].append(toks)

    if len(progs) != n:
        return (False, 'expected %d programs separated by empty lines, got %d' % (n, len(progs)))

    geoms = {}
    total = 0
    for ci, ((R, rows, cols, count, pat), (first, prog)) in enumerate(zip(cases, progs), 1):
        g = geoms.get(R)
        if g is None:
            g = geoms[R] = _Geom(R)
        acc, active = _simulate(g, pat, prog)
        if acc < count:
            return (False, 'program %d (starting at line %d): simulation submits %d of %d required patterns'
                    % (ci, first, acc, count))
        # ASSUMPTION (not checked by the visualizer): every emitter must be switched off when the
        # program ends. All official example programs do this, and it costs at most one extra
        # line, so any answer accepted here is also valid under the visualizer's rules.
        on = [str(t + 1) for t in range(6) if active[t]]
        if on:
            return (False, 'program %d (starting at line %d): emitter(s) %s still active at the end '
                    '(must be switched off)' % (ci, first, ','.join(on)))
        total += len(prog)
    return (True, '%d programs OK, %d instruction lines' % (n, total), total)
