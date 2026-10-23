DIRS4 = [(0, 1), (1, 0), (0, -1), (-1, 0)]
DIRS8 = DIRS4 + [(1, 1), (1, -1), (-1, 1), (-1, -1)]


class Grid:
    """2D char grid addressed as (row, col)."""

    def __init__(self, rows):
        self.g = [list(r) for r in rows]
        self.h = len(self.g)
        self.w = len(self.g[0]) if self.g else 0

    def __getitem__(self, p):
        return self.g[p[0]][p[1]]

    def __setitem__(self, p, v):
        self.g[p[0]][p[1]] = v

    def inside(self, p):
        return 0 <= p[0] < self.h and 0 <= p[1] < self.w

    def neighbors(self, p, dirs=DIRS4):
        r, c = p
        for dr, dc in dirs:
            q = (r + dr, c + dc)
            if self.inside(q):
                yield q

    def find(self, ch):
        return [(r, c) for r in range(self.h) for c in range(self.w) if self.g[r][c] == ch]

    def cells(self):
        for r in range(self.h):
            for c in range(self.w):
                yield (r, c)

    def __str__(self):
        return "\n".join("".join(map(str, row)) for row in self.g)
