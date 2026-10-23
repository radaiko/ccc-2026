from collections import deque
from itertools import combinations


DIRS = ((0, 2), (1, 1), (1, -1), (0, -2), (-1, -1), (-1, 1))


def geometry(r, drawing):
    cells = [(y, x) for y, row in enumerate(drawing)
             for x, ch in enumerate(row) if ch in 'OM']
    index = {p: i for i, p in enumerate(cells)}
    targets = [p for p in cells if drawing[p[0]][p[1]] == 'M']
    target_index = {p: i for i, p in enumerate(targets)}
    target = sum(1 << index[p] for p in targets)
    halo = 0
    for y, x in targets:
        for dy, dx in DIRS:
            q = y + dy, x + dx
            if q in index and q not in target_index:
                halo |= 1 << index[q]
    rail = []
    y, x = r, 0
    for dy, dx in ((-1, 1), (0, 2), (1, 1), (1, -1), (0, -2), (-1, -1)):
        for _ in range(r):
            rail.append((y, x))
            y += dy
            x += dx
    m = 2 * r - 1
    beams = []
    positions = [[0, 0, 0] for _ in targets]
    for e in range(3):
        eb = []
        dy, dx = DIRS[e]
        for k in range(m):
            y, x = rail[(e * r + k - (r - 1)) % (6 * r)]
            y += dy
            x += dx
            beam = 0
            while (y, x) in index:
                beam |= 1 << index[y, x]
                if (y, x) in target_index:
                    positions[target_index[y, x]][e] = k
                y += dy
                x += dx
            eb.extend((0, beam))
        beams.append(eb)
    return cells, targets, target, halo, beams, positions, index


def pair_route(r, positions, pair, seed, start):
    """A target-only walk; simultaneous rail moves give eight neighbours."""
    a, b = pair
    n = len(positions)
    coords = [(p[a], p[b]) for p in positions]
    at = {p: i for i, p in enumerate(coords)}
    adj = []
    for x, y in coords:
        adj.append([at[x + dx, y + dy]
                    for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                    if (dx or dy) and (x + dx, y + dy) in at])
    unvisited = set(range(n))
    unvisited.remove(start)
    path = [start]
    degree = [len(ns) for ns in adj]
    for v in adj[start]:
        degree[v] -= 1
    current = start
    while unvisited:
        choices = [v for v in adj[current] if v in unvisited]
        if choices:
            nxt = min(choices, key=lambda v: (
                degree[v], ((v + 1) * 1103515245 + seed * 12345) % 65521))
            segment = [nxt]
        else:
            parents = {current: -1}
            frontier = [current]
            goals = []
            while frontier and not goals:
                nf = []
                for u in frontier:
                    for v in adj[u]:
                        if v not in parents:
                            parents[v] = u
                            nf.append(v)
                            if v in unvisited:
                                goals.append(v)
                frontier = nf
            if not goals:
                return None
            nxt = min(goals, key=lambda v: (
                degree[v], ((v + 1) * 1103515245 + seed * 12345) % 65521))
            segment = []
            v = nxt
            while v != current:
                segment.append(v)
                v = parents[v]
            segment.reverse()
        for v in segment:
            path.append(v)
            if v in unvisited:
                unvisited.remove(v)
                for w in adj[v]:
                    degree[w] -= 1
        current = nxt
    return path


class Builder:
    def __init__(self, r, drawing):
        self.r = r
        (self.cells, self.targets, self.target, self.halo, self.beams,
         self.positions, self.index) = geometry(r, drawing)
        self.m = 2 * r - 1
        self.n = 2 * self.m
        self.n2 = self.n * self.n
        self.centre = 2 * (r - 1)
        self.initial = self.encode([self.centre] * 3)
        self.paint_cache = [-2] * (self.n ** 3)
        self.local_next = []
        for p in range(self.n):
            ns = [p, p ^ 1]
            if p >= 2:
                ns.append(p - 2)
            if p + 2 < self.n:
                ns.append(p + 2)
            self.local_next.append(ns)
        self.weights = {}
        tset = set(self.targets)
        for p in self.targets:
            degree = sum((p[0] + dy, p[1] + dx) in tset for dy, dx in DIRS)
            self.weights[1 << self.index[p]] = 8 - degree

    def encode(self, q):
        return q[0] * self.n2 + q[1] * self.n + q[2]

    def decode(self, s):
        a, bc = divmod(s, self.n2)
        b, c = divmod(bc, self.n)
        return [a, b, c]

    def paint(self, s):
        ans = self.paint_cache[s]
        if ans != -2:
            return ans
        a, bc = divmod(s, self.n2)
        b, c = divmod(bc, self.n)
        aa, bb, cc = self.beams[0][a], self.beams[1][b], self.beams[2][c]
        triple = aa & bb & cc
        made = ((aa & bb) | (aa & cc) | (bb & cc)) & ~triple
        if triple & self.target or made & self.halo:
            ans = -1
        else:
            ans = made & self.target
        self.paint_cache[s] = ans
        return ans

    def neighbours(self, s):
        a, b, c = self.decode(s)
        for aa in self.local_next[a]:
            aoff = aa * self.n2
            for bb in self.local_next[b]:
                off = aoff + bb * self.n
                for cc in self.local_next[c]:
                    ns = off + cc
                    paint = self.paint(ns)
                    if paint >= 0:
                        yield ns, paint

    def rank(self, s, new, seed):
        score = 0
        count = 0
        while new:
            bit = new & -new
            score += self.weights[bit]
            count += 1
            new -= bit
        a, b, c = self.decode(s)
        return (count * 100000 + score * 100
                + ((a & 1) + (b & 1) + (c & 1)) * 10
                + ((s * 1103515245 + seed * 12345) % 65521) % 10)

    def pair_states(self, pair, path):
        q = [self.centre] * 3
        states = [self.initial]
        first = self.positions[path[0]]
        goal = q[:]
        for e in pair:
            goal[e] = 2 * first[e]
        while q != goal:
            q = [v + (2 if g > v else -2 if g < v else 0)
                 for v, g in zip(q, goal)]
            states.append(self.encode(q))
        for e in pair:
            q[e] |= 1
        states.append(self.encode(q))
        for cell in path[1:]:
            for e in pair:
                q[e] = 2 * self.positions[cell][e] + 1
            states.append(self.encode(q))
        return states

    def fallback(self, current, missing):
        q = self.decode(current)
        best = None
        for i, cell in enumerate(self.targets):
            bit = 1 << self.index[cell]
            if not (missing & bit):
                continue
            for pair in ((0, 1), (0, 2), (1, 2)):
                cost = max(abs(q[e] // 2 - self.positions[i][e]) for e in pair)
                key = (cost, -self.weights[bit], i, pair)
                if best is None or key < best:
                    best = key
        _, _, cell, pair = best
        states = []
        if any(v & 1 for v in q):
            q = [v & ~1 for v in q]
            states.append(self.encode(q))
        goal = q[:]
        for e in pair:
            goal[e] = 2 * self.positions[cell][e]
        while q != goal:
            q = [v + (2 if g > v else -2 if g < v else 0)
                 for v, g in zip(q, goal)]
            states.append(self.encode(q))
        for e in pair:
            q[e] |= 1
        states.append(self.encode(q))
        return states

    def greedy_states(self, seed):
        current = self.initial
        states = [current]
        missing = self.target
        while missing:
            best = None
            for ns, paint in self.neighbours(current):
                new = paint & missing
                if new:
                    rank = self.rank(ns, new, seed)
                    if best is None or rank > best[0]:
                        best = rank, ns
            if best is not None:
                segment = [best[1]]
            else:
                # Search a few layers for safe simultaneous moves and toggles.
                parents = {current: -1}
                frontier = [current]
                expanded = 0
                goal = None
                while frontier and goal is None and expanded < 160:
                    nf = []
                    best_rank = -1
                    for s in frontier:
                        if expanded >= 160:
                            break
                        expanded += 1
                        for ns, paint in self.neighbours(s):
                            if ns in parents:
                                continue
                            parents[ns] = s
                            nf.append(ns)
                            new = paint & missing
                            if new:
                                rank = self.rank(ns, new, seed)
                                if rank > best_rank:
                                    best_rank = rank
                                    goal = ns
                    frontier = nf
                if goal is None:
                    segment = self.fallback(current, missing)
                else:
                    segment = []
                    while goal != current:
                        segment.append(goal)
                        goal = parents[goal]
                    segment.reverse()
            for s in segment:
                states.append(s)
                missing &= ~self.paint(s)
            current = states[-1]
        # Remove moves after the first completion, if a fallback crossed it.
        missing = self.target
        for i, s in enumerate(states[1:], 1):
            missing &= ~self.paint(s)
            if not missing:
                return states[:i + 1]
        return states

    def program(self, states, required, cutoff=None):
        if required == 0:
            return ['- - - - - -']
        previous = self.decode(self.initial)
        missing = self.target
        count = 0
        result = []
        repeat_start = next(i for i in range(1, len(states)) if self.paint(states[i]))
        sequence = states[1:]
        reverse = True
        while True:
            for state in sequence:
                q = self.decode(state)
                line = []
                for old, new in zip(previous, q):
                    if old == new:
                        line.append('-')
                    elif old // 2 == new // 2:
                        line.append('T')
                    elif new == old + 2:
                        line.append('F')
                    elif new == old - 2:
                        line.append('B')
                    else:
                        raise AssertionError('nonlocal transition')
                result.append(' '.join(line) + ' - - -')
                previous = q
                missing &= ~self.paint(state)
                if not missing:
                    count += 1
                    missing = self.target
                    if count == required:
                        if any(v & 1 for v in q):
                            result.append(' '.join('T' if v & 1 else '-' for v in q)
                                          + ' - - -')
                        return result
                if cutoff is not None and len(result) >= cutoff:
                    return None
            if reverse:
                sequence = states[repeat_start:][::-1]
            else:
                sequence = states[repeat_start:]
            reverse = not reverse

    def build(self, required):
        if not required:
            return ['- - - - - -']
        best = None
        number = len(self.targets)
        for pair in ((0, 1), (0, 2), (1, 2)):
            a, b = pair
            coords = [(p[a], p[b]) for p in self.positions]
            points = set(coords)
            degrees = [sum((x + dx, y + dy) in points
                           for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                           if dx or dy) for x, y in coords]
            order = sorted(range(number), key=lambda i: (
                degrees[i], max(abs(v - (self.r - 1)) for v in coords[i]), i))
            starts = order[:8]
            starts.extend(sorted(range(number), key=lambda i:
                                 max(abs(v - (self.r - 1)) for v in coords[i]))[:4])
            starts.extend(range(0, number, max(1, number // 8)))
            for trial, start in enumerate(dict.fromkeys(starts)):
                path = pair_route(self.r, self.positions, pair, trial * 17, start)
                if path is None:
                    continue
                states = self.pair_states(pair, path)
                prog = self.program(states, required, len(best) if best else None)
                if prog is not None and (best is None or len(prog) < len(best)):
                    best = prog
        for seed in (1, 13, 47):
            states = self.greedy_states(seed)
            prog = self.program(states, required, len(best) if best else None)
            if prog is not None and (best is None or len(prog) < len(best)):
                best = prog
        return best


def solve(text):
    tokens = text.split()
    n = int(tokens[0])
    k = 1
    programs = []
    for _ in range(n):
        r, h, w, required = map(int, tokens[k:k + 4])
        k += 4
        drawing = tokens[k:k + h]
        k += h
        builder = Builder(r, drawing)
        programs.append('\n'.join(builder.build(required)))
    return '\n\n'.join(programs)
