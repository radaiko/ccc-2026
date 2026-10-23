from common import *
import random
import re

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


def cases(text):
    t = text.split()
    n = int(t[0])
    p = 1
    for _ in range(n):
        r, h, w, count = map(int, t[p:p + 4])
        p += 4
        pat = t[p:p + h]
        p += h
        assert h == 2 * r + 1 and w == 4 * r + 1
        yield r, pat, count
    assert p == len(t)


def emitter_coordinates(r, cells):
    """Signed offsets from each emitter's initial corner for each target."""
    rg = {cell: i for i, cell in enumerate(ring(r))}
    coords = []
    for y, x in cells:
        row = []
        for e, (dy, dx) in enumerate(DIRS[:3]):
            yy, xx = y, x
            while (yy, xx) not in rg:
                yy -= dy
                xx -= dx
            offset = (rg[yy, xx] - e * r + 3 * r) % (6 * r) - 3 * r
            row.append(offset)
        coords.append(row)
    return coords


def cover_walk(points, adj, start, rng, trial, already=()):
    """Visit every target, preferring unvisited neighbours with few exits."""
    n = len(points)
    seen = [False] * n
    for v in already:
        seen[v] = True
    degree = [len(a) for a in adj]
    for v in already:
        for u in adj[v]:
            degree[u] -= 1
    left = n - len(already)
    route = []

    def visit(v):
        nonlocal left
        route.append(v)
        if not seen[v]:
            seen[v] = True
            left -= 1
            for u in adj[v]:
                degree[u] -= 1

    visit(start)
    while left:
        v = route[-1]
        choices = [u for u in adj[v] if not seen[u]]
        if choices:
            # Random restarts vary ties and occasionally relax the degree rule.
            noise = 0.9 if trial % 4 else 2.5
            u = min(choices, key=lambda u: degree[u] + noise * rng.random())
            visit(u)
            continue

        # Find the nearest unvisited target through already painted cells.
        parent = {v: -1}
        queue = [v]
        goals = []
        for u in queue:
            if not seen[u]:
                goals.append(u)
                break
            neighbours = list(adj[u])
            rng.shuffle(neighbours)
            for z in neighbours:
                if z not in parent:
                    parent[z] = u
                    queue.append(z)
        if goals:
            path = []
            u = goals[0]
            while u != v:
                path.append(u)
                u = parent[u]
            path.reverse()
        else:
            path = []

        # Turning a beam off permits a safe shortcut, even across holes.
        x, y = points[v]
        dest = min((u for u in range(n) if not seen[u]),
                   key=lambda u: max(abs(points[u][0] - x), abs(points[u][1] - y)))
        jump = max(abs(points[dest][0] - x), abs(points[dest][1] - y)) + 2
        if not path or jump < len(path):
            visit(dest)
        else:
            for u in path:
                visit(u)
    return route


def make_program(points, pair, route, required):
    """Two nonparallel beams create only their single intersection cell."""
    program = []
    pos = [0, 0]
    painted = set()
    accepted = 0

    def emit(a, b):
        line = ['-'] * 6
        line[pair[0]], line[pair[1]] = a, b
        program.append(' '.join(line))

    def move(target):
        while pos != list(target):
            ins = []
            for e in range(2):
                delta = (target[e] > pos[e]) - (target[e] < pos[e])
                pos[e] += delta
                ins.append('F' if delta > 0 else 'B' if delta < 0 else '-')
            emit(*ins)

    def paint(v):
        nonlocal accepted
        painted.add(v)
        if len(painted) == len(points):
            painted.clear()
            accepted += 1

    move(points[route[0]])
    emit('T', 'T')
    paint(route[0])
    forward = True
    while accepted < required:
        walk = route if forward else route[::-1]
        for v in walk[1:]:
            target = points[v]
            distance = max(abs(target[e] - pos[e]) for e in range(2))
            if distance > 1:
                emit('T', '-')
                move(target)
                emit('T', '-')
            else:
                move(target)
            paint(v)
            if accepted == required:
                return program
        # The arm clears the pattern, including the current intersection.
        # A waiting tick recreates this endpoint before the reverse traversal.
        emit('-', '-')
        paint(walk[-1])
        forward = not forward
    return program


def generate(r, pat, required):
    cells = [(y, x) for y, row in enumerate(pat) for x, ch in enumerate(row) if ch == 'M']
    assert cells and required > 0
    coords = emitter_coordinates(r, cells)
    rng = random.Random(2026)
    best = None
    best_estimate = float('inf')
    for pair in [(0, 1), (0, 2), (1, 2)]:
        points = [(c[pair[0]], c[pair[1]]) for c in coords]
        lookup = {p: i for i, p in enumerate(points)}
        adj = []
        for x, y in points:
            adj.append([lookup[x + dx, y + dy]
                        for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                        if (dx or dy) and (x + dx, y + dy) in lookup])
        starts = sorted(range(len(cells)), key=lambda v: (max(map(abs, points[v])), len(adj[v])))
        trials = 48 if len(cells) < 80 else 32
        for trial in range(trials):
            if trial < min(8, len(starts)):
                start = starts[trial]
            elif trial % 2:
                start = rng.randrange(len(cells))
            else:
                start = min(range(len(cells)), key=lambda v: len(adj[v]) + rng.random())
            route = cover_walk(points, adj, start, rng, trial)
            cost = 0
            for a, b in zip(route, route[1:]):
                dist = max(abs(points[a][e] - points[b][e]) for e in range(2))
                cost += dist if dist <= 1 else dist + 2
            # Both ends can be the first target; compare their setup costs.
            if max(map(abs, points[route[-1]])) < max(map(abs, points[route[0]])):
                route.reverse()
            estimate = (cost + 1) * required + max(map(abs, points[route[0]]))
            if estimate <= best_estimate:
                program = make_program(points, pair, route, required)
                best_estimate = min(best_estimate, estimate)
                if best is None or len(program) < len(best):
                    best = program
    return best


def solve(text):
    return '\n\n'.join('\n'.join(generate(r, pat, count)) for r, pat, count in cases(text))


def check(input_text, output_text):
    inputs = list(cases(input_text))
    blocks = re.split(r'\n\s*\n', output_text.strip())
    if len(blocks) != len(inputs):
        return False, 'Wrong number of programs', None
    score = 0
    for i, ((r, pat, count), block) in enumerate(zip(inputs, blocks), 1):
        prog = [line.split() for line in block.splitlines()]
        if any(len(line) != 6 or any(c not in ('F', 'B', 'T', '-') for c in line) for line in prog):
            return False, 'Invalid instruction in program %d' % i, None
        actual = simulate(r, pat, prog)
        if actual != count:
            return False, 'Program %d: produced %d, expected %d' % (i, actual, count), None
        score += len(prog)
    return True, 'All pattern counts match', score


if __name__ == '__main__':
    import sys
    print(solve(sys.stdin.read()))
