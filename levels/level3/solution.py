from common import *

# Character-grid steps for each emitter direction (row, col).
DIRS = {'1': (0, 2), '4': (0, -2), '2': (1, 1), '3': (1, -1), '5': (-1, -1), '6': (-1, 1)}


def solve(text):
    ls = [l.strip() for l in text.splitlines()]
    n = int(ls[0])
    i = 1
    out = []
    for b in range(n):
        while not ls[i]:
            i += 1
        r, h, w = map(int, ls[i].split())
        g = [list(row) for row in ls[i + 1:i + 1 + h]]
        i += 1 + h
        # Count beams per cell; all emitters fire simultaneously, beams pass through O/M.
        cnt = {}
        for y in range(h):
            for x, c in enumerate(g[y]):
                if c in DIRS:
                    dy, dx = DIRS[c]
                    yy, xx = y + dy, x + dx
                    while 0 <= yy < h and 0 <= xx < len(g[yy]) and g[yy][xx] in 'OM':
                        cnt[(yy, xx)] = cnt.get((yy, xx), 0) + 1
                        yy += dy
                        xx += dx
        for (yy, xx), k in cnt.items():
            if k == 2:
                g[yy][xx] = 'M'
            elif k >= 3:
                g[yy][xx] = 'O'
        if b:
            out.append('')
        out.extend(''.join(row) for row in g)
    return out
