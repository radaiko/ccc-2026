from common import *

# Character-grid steps for each emitter direction (row, col).
DIRS = [(0, 2), (1, 1), (1, -1), (0, -2), (-1, -1), (-1, 1)]  # emitters 1..6
NB = [(0, 2), (0, -2), (1, 1), (1, -1), (-1, 1), (-1, -1)]


def board(r):
    rows = []
    for i in range(2 * r + 1):
        k = abs(i - r)
        n = 2 * r + 1 - k
        cells = ['*'] * n if k == r else ['*'] + ['O'] * (n - 2) + ['*']
        rows.append(list('-' * k + '-'.join(cells) + '-' * k))
    return rows


def ring(r):
    # Border cells in clockwise order, starting at the left corner (emitter 1).
    cells = []
    i, c = r, 0
    for di, dc in [(-1, 1), (0, 2), (1, 1), (1, -1), (0, -2), (-1, -1)]:
        for _ in range(r):
            cells.append((i, c))
            i += di
            c += dc
    return cells


def simulate(r, pat, prog):
    g = board(r)
    h, w = 2 * r + 1, 4 * r + 1
    rg = ring(r)
    m = len(rg)
    pcells = [(y, x) for y in range(h) for x in range(w) if pat[y][x] == 'M']
    pset = set(pcells)
    # Cells adjacent to the pattern that are not part of it: must not hold matter.
    halo = set()
    for y, x in pcells:
        for dy, dx in NB:
            q = (y + dy, x + dx)
            if q not in pset and 0 <= q[0] < h and 0 <= q[1] < w:
                halo.add(q)
    halo = list(halo)
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
            while 0 <= y < h and 0 <= x < w and g[y][x] in 'OM':
                cnt[(y, x)] = cnt.get((y, x), 0) + 1
                y += dy
                x += dx
        for (y, x), k in cnt.items():
            if k == 2:
                g[y][x] = 'M'
            elif k >= 3:
                g[y][x] = 'O'
        if pcells and all(g[y][x] == 'M' for y, x in pcells) and \
                not any(g[y][x] == 'M' for y, x in halo):
            for y, x in pcells:
                g[y][x] = 'O'
            count += 1
    return count


def solve(text):
    t = text.split()
    n = int(t[0])
    p = 1
    out = []
    for _ in range(n):
        r = int(t[p])
        h = int(t[p + 1])
        p += 3
        pat = t[p:p + h]
        p += h
        l = int(t[p])
        p += 1
        prog = [t[p + 6 * j:p + 6 * j + 6] for j in range(l)]
        p += 6 * l
        out.append(str(simulate(r, pat, prog)))
    return out
