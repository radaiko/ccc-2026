from collections import deque


DIRS = ((0, 2), (1, 1), (1, -1), (0, -2), (-1, -1), (-1, 1))
STEPS = ((-1, -1), (-1, 0), (-1, 1), (0, -1),
         (0, 1), (1, -1), (1, 0), (1, 1))
GEOMETRY = {}


def geometry(r):
    if r in GEOMETRY:
        return GEOMETRY[r]
    ring = []
    y, x = r, 0
    for dy, dx in ((-1, 1), (0, 2), (1, 1),
                   (1, -1), (0, -2), (-1, -1)):
        for _ in range(r):
            ring.append((y, x))
            y += dy
            x += dx
    interior = set()
    for y in range(1, 2 * r):
        pad = abs(y - r)
        for x in range(pad + 2, 4 * r - pad, 2):
            interior.add((y, x))
    maps = []
    for e in range(3):
        dy, dx = DIRS[e]
        entry = {}
        for j, (y, x) in enumerate(ring):
            offset = (j - e * r + 3 * r) % (6 * r) - 3 * r
            y += dy
            x += dx
            while (y, x) in interior:
                entry[y, x] = offset
                y += dy
                x += dx
        assert len(entry) == len(interior)
        maps.append(entry)
    GEOMETRY[r] = maps
    return maps


def walk_graph(coords, start, variant):
    """Visit every target, travelling only between safe beam intersections."""
    n = len(coords)
    index = {p: i for i, p in enumerate(coords)}
    adj = []
    for a, b in coords:
        adj.append([index[a + da, b + db] for da, db in STEPS
                    if (a + da, b + db) in index])
    visited = [False] * n
    visited[start] = True
    degree = [len(a) for a in adj]
    for v in adj[start]:
        degree[v] -= 1
    route = [start]
    remaining = n - 1
    cur = start

    def tie(v):
        a, b = coords[v]
        if variant & 1:
            a, b = b, a
        if variant & 2:
            a = -a
        if variant & 4:
            b = -b
        return a, b

    while remaining:
        nxts = [v for v in adj[cur] if not visited[v]]
        if nxts:
            nxt = min(nxts, key=lambda v: (degree[v], tie(v)))
            path = [nxt]
        else:
            parent = [-1] * n
            parent[cur] = cur
            q = deque([cur])
            found = -1
            while q and found < 0:
                u = q.popleft()
                for v in sorted(adj[u], key=tie):
                    if parent[v] >= 0:
                        continue
                    parent[v] = u
                    if not visited[v]:
                        found = v
                        break
                    q.append(v)
            if found < 0:
                # The statement calls patterns connected; also handle separated
                # components with a beam-off transfer in make_program.
                a, b = coords[cur]
                found = min((v for v in range(n) if not visited[v]),
                            key=lambda v: (max(abs(coords[v][0] - a),
                                               abs(coords[v][1] - b)), tie(v)))
                path = [found]
            else:
                path = []
                v = found
                while v != cur:
                    path.append(v)
                    v = parent[v]
                path.reverse()
        for v in path:
            route.append(v)
            if not visited[v]:
                visited[v] = True
                remaining -= 1
                for u in adj[v]:
                    degree[u] -= 1
        cur = path[-1]
    return route


def make_program(coords, route, e, f, required, limit):
    n = len(coords)
    full = (1 << n) - 1
    bits = [1 << i for i in range(n)]
    covered = 0
    count = 0
    program = []
    pos = [0, 0]
    active = [False, False]
    index = {p: i for i, p in enumerate(coords)}

    def emit(a, b):
        nonlocal covered, count
        for j, ins in enumerate((a, b)):
            if ins == 'F':
                pos[j] += 1
            elif ins == 'B':
                pos[j] -= 1
            elif ins == 'T':
                active[j] = not active[j]
        program.append((a, b))
        if active[0] and active[1]:
            v = index.get(tuple(pos))
            assert v is not None
            covered |= bits[v]
            if covered == full:
                covered = 0
                count += 1
        return count == required

    def transfer(target):
        da, db = target[0] - pos[0], target[1] - pos[1]
        sa = 'F' if da > 0 else 'B'
        sb = 'F' if db > 0 else 'B'
        da, db = abs(da), abs(db)
        if not active[0] and not active[1]:
            # Each emitter can activate as soon as it finishes moving.
            for t in range(max(da, db) + 1):
                a = sa if t < da else ('T' if t == da else '-')
                b = sb if t < db else ('T' if t == db else '-')
                if emit(a, b):
                    return True
            return False
        if max(da, db) <= 1:
            return emit(sa if da else '-', sb if db else '-')
        # Turn off the emitter with the shorter journey. Its two toggles
        # overlap the other emitter's movement whenever possible.
        gate = 0 if max(da + 2, db) <= max(da, db + 2) else 1
        distances = (da, db)
        signs = (sa, sb)
        duration = max(distances[gate] + 2, distances[1 - gate])
        for t in range(duration):
            commands = ['-', '-']
            if t == 0 or t == duration - 1:
                commands[gate] = 'T'
            elif t <= distances[gate]:
                commands[gate] = signs[gate]
            if t < distances[1 - gate]:
                commands[1 - gate] = signs[1 - gate]
            if emit(*commands):
                return True
        return False

    if transfer(coords[route[0]]):
        return program
    forward = True
    while count < required:
        seq = route[1:] if forward else route[-2::-1]
        for v in seq:
            if transfer(coords[v]):
                return program
            if len(program) >= limit:
                return None
        forward = not forward
        # The endpoint was removed on submission. Recreate it before
        # walking back, also covering the one-cell pattern case.
        if emit('-', '-'):
            return program
        if len(program) >= limit:
            return None
    return program


def generate(r, pattern, required):
    cells = [(y, x) for y, row in enumerate(pattern)
             for x, c in enumerate(row) if c == 'M']
    if required == 0:
        return '- - - - - -'
    maps = geometry(r)
    best = None
    best_pair = None
    for e, f in ((0, 1), (0, 2), (1, 2)):
        coords = [(maps[e][cell], maps[f][cell]) for cell in cells]
        # Four corners of the target plus the nearest entry point provide
        # good starts for thin, dense and branching patterns alike.
        starts = {min(range(len(cells)),
                      key=lambda i: (max(abs(coords[i][0]), abs(coords[i][1])),
                                     abs(coords[i][0]) + abs(coords[i][1])))}
        for sa, sb in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
            starts.add(min(range(len(cells)),
                           key=lambda i: (sa * coords[i][0], sb * coords[i][1])))
        for variant in range(8):
            for start in starts:
                route = walk_graph(coords, start, variant)
                program = make_program(coords, route, e, f, required,
                                       len(best) if best is not None else 10 ** 9)
                if program is not None and (best is None or len(program) < len(best)):
                    best = program
                    best_pair = (e, f)
    out = []
    e, f = best_pair
    for a, b in best:
        line = ['-'] * 6
        line[e], line[f] = a, b
        out.append(' '.join(line))
    # Shut down after the final pickup; no further matter is produced.
    line = ['-'] * 6
    line[e] = line[f] = 'T'
    out.append(' '.join(line))
    return '\n'.join(out)


def solve(text):
    tokens = text.split()
    p = 1
    out = []
    for _ in range(int(tokens[0])):
        r, h, w, required = map(int, tokens[p:p + 4])
        p += 4
        pattern = tokens[p:p + h]
        p += h
        out.append(generate(r, pattern, required))
    return '\n\n'.join(out)
