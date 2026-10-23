from common import *

# Character-grid steps for each emitter direction (row, col).
DIRS = [(0, 2), (1, 1), (1, -1), (0, -2), (-1, -1), (-1, 1)]  # emitters 1..6


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


def simulate(r, prog):
    g = board(r)
    h, w = 2 * r + 1, 4 * r + 1
    rg = ring(r)
    m = len(rg)
    # Emitter k starts at corner k (corners are every r cells clockwise from the left one).
    pos = [0, r, 2 * r, 3 * r, 4 * r, 5 * r]
    active = [False] * 6
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
    return [''.join(row) for row in g]


def solve(text):
    t = text.split()
    n = int(t[0])
    p = 1
    out = []
    for b in range(n):
        r, l = int(t[p]), int(t[p + 1])
        p += 2
        prog = [t[p + 6 * j:p + 6 * j + 6] for j in range(l)]
        p += 6 * l
        if b:
            out.append('')
        out.extend(simulate(r, prog))
    return out
