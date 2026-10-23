from collections import deque
from itertools import combinations
from random import Random


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


class SixBuilder:
    """Search all simultaneous one-tick actions with six emitters."""

    def __init__(self, base):
        self.base = base
        self.r = base.r
        self.m = base.m
        self.n = base.n
        self.n2 = base.n2
        self.target = base.target
        self.halo = base.halo
        interest = self.target | self.halo
        self.beams = [[b & interest for b in row] for row in base.beams]
        self.beams += [[self.beams[e][2 * (self.m - 1 - k) + on]
                        for k in range(self.m) for on in (0, 1)]
                       for e in range(3)]
        self.positions = [p + [self.m - 1 - v for v in p]
                          for p in base.positions]
        self.initial = (base.centre,) * 6
        self.bits = [1 << base.index[p] for p in base.targets]
        self.pairs = [(a, b) for a in range(6) for b in range(a + 1, 6)
                      if a % 3 != b % 3]
        self.group_cache = [{}, {}]

    def group(self, group, q):
        key = tuple(q)
        cached = self.group_cache[group].get(key)
        if cached is not None:
            return cached
        offset = group * 3
        result = []
        b0, b1, b2 = self.beams[offset:offset + 3]
        for a in self.base.local_next[q[0]]:
            aa = b0[a]
            for b in self.base.local_next[q[1]]:
                bb = b1[b]
                ab = aa & bb
                for c in self.base.local_next[q[2]]:
                    cc = b2[c]
                    triple = ab & cc
                    union = aa | bb | cc
                    double = (ab | (aa & cc) | (bb & cc)) & ~triple
                    single = union & ~(double | triple)
                    sleeping = ((b0[a | 1] if not a & 1 else 0)
                                | (b1[b | 1] if not b & 1 else 0)
                                | (b2[c | 1] if not c & 1 else 0))
                    result.append(((a, b, c), union, single, double,
                                   double & self.target, triple & self.target, sleeping))
        self.group_cache[group][key] = result
        return result

    def effects(self, q):
        union = double = triple = 0
        for e, p in enumerate(q):
            b = self.beams[e][p]
            triple |= double & b
            double |= union & b
            union |= b
        made = double & ~triple
        assert not made & self.halo
        return made & self.target, triple & self.target

    def effect(self, q):
        return self.effects(q)[0]

    def next_gain(self, current, missing, seed, lookahead=True):
        first = self.group(0, current[:3])
        second = self.group(1, current[3:])
        best = None
        best_rank = -1
        best_count = 0
        prep = None
        prep_rank = -1
        prep_future = 0
        for qa, ua, oa, ta, tat, bat, asleep in first:
            for qb, ub, ob, tb, tbt, bbt, bsleep in second:
                burn = bat | bbt | (tat & ub) | (tbt & ua)
                if seed == 1 and burn:
                    continue
                made = (ta & ~ub) | (tb & ~ua) | (oa & ob)
                if made & self.halo:
                    continue
                new = made & missing
                count = bin(new).count('1') - bin(burn & ~missing).count('1')
                if count < 0:
                    continue
                if count and count < best_count:
                    continue
                single = (oa & ~ub) | (ob & ~ua)
                future = bin((asleep | bsleep) & single & missing & ~new).count('1')
                # Beams already crossing other missing cells are useful next tick.
                potential = bin((ua | ub) & missing & ~new).count('1')
                q = qa + qb
                noise = (sum((i + 3) * v * 73471 for i, v in enumerate(q))
                         + seed * 31337) % 97
                rank = count * 1000000 + future * 1000 + potential * 10 + noise
                if not count:
                    if future and rank > prep_rank:
                        prep_rank = rank
                        prep_future = future
                        prep = q, made & self.target, burn
                    continue
                if rank > best_rank:
                    best_rank = rank
                    best_count = count
                    best = q, made & self.target, burn
        if lookahead and prep is not None and prep_future >= max(2, 2 * best_count):
            q, paint, burn = prep
            after = (missing | burn) & ~paint
            continuation = self.next_gain(q, after, seed, False)
            if continuation is not None:
                _, np, nb = continuation[0]
                gain = bin(np & after).count('1') - bin(nb & ~after).count('1')
                if gain >= max(1, 2 * best_count):
                    return [prep] + continuation
        return [best] if best is not None else None

    def fallback(self, current, missing):
        best = None
        for i, bit in enumerate(self.bits):
            if not (missing & bit):
                continue
            p = self.positions[i]
            for a, b in self.pairs:
                cost = max(abs(current[a] // 2 - p[a]),
                           abs(current[b] // 2 - p[b]))
                key = cost, i, a, b
                if best is None or key < best:
                    best = key
        _, cell, a, b = best
        q = list(current)
        states = []
        if any(v & 1 for v in q):
            q = [v & ~1 for v in q]
            states.append((tuple(q), 0, 0))
        goal = q[:]
        goal[a] = 2 * self.positions[cell][a]
        goal[b] = 2 * self.positions[cell][b]
        while q != goal:
            q = [v + (2 if g > v else -2 if g < v else 0)
                 for v, g in zip(q, goal)]
            states.append((tuple(q), 0, 0))
        q[a] |= 1
        q[b] |= 1
        paint, burn = self.effects(q)
        states.append((tuple(q), paint, burn))
        return states

    def route(self, seed, first=None, current=None):
        if current is not None:
            states = [(current, 0, 0)]
        else:
            states = self.setup(first) if first is not None else [(self.initial, 0, 0)]
        missing = self.target
        for _, paint, burn in states:
            missing = (missing | burn) & ~paint
        while missing:
            found = self.next_gain(states[-1][0], missing, seed)
            local_gain = 0
            if found is not None:
                after = missing
                for _, paint, burn in found:
                    after = (after | burn) & ~paint
                local_gain = bin(missing).count('1') - bin(after).count('1')
            jump = self.pool_jump(states[-1][0], missing,
                                  local_gain, len(found) if found else 1)
            if jump is not None:
                found = jump
            if found is not None:
                segment = found
            else:
                segment = self.fallback(states[-1][0], missing)
            for state in segment:
                states.append(state)
                _, paint, burn = state
                missing = (missing | burn) & ~paint
                if not missing:
                    return states
        return states

    def online(self, initial_route, required, cutoff):
        states = initial_route[:]
        cache = {}
        for _ in range(1, required):
            q = states[-1][0]
            if q not in cache:
                cache[q] = self.route(1, current=q)
            states.extend(cache[q][1:])
            if len(states) >= cutoff:
                return None
        return self.program(states, required, cutoff)

    def beam_route(self, initial_route, width=18):
        first = next(i for i in range(1, len(initial_route)) if initial_route[i][1])
        prefix = initial_route[:first + 1]
        q, paint, burn = prefix[-1]
        board = paint & ~burn
        frontier = [(q, board, [])]
        seen = {(q, board)}
        target = self.target
        halo = self.halo

        def evaluate(a, b, old):
            qa, ua, oa, ta = a[:4]
            qb, ub, ob, tb = b[:4]
            made = (ta & ~ub) | (tb & ~ua) | (oa & ob)
            burnt = ((ua & ~(oa | ta)) | (ub & ~(ob | tb))
                     | (ta & ub) | (tb & ua))
            newboard = (old | made) & ~burnt
            wrong = newboard & halo
            filled = newboard & target
            score = bin(filled).count('1') * 10000 - bin(wrong).count('1') * 18000
            single = (oa & ~ub) | (ob & ~ua)
            future = (a[6] | b[6]) & single & target & ~filled
            score += bin(future).count('1') * 60
            score += bin((ua | ub) & target & ~filled).count('1') * 10
            return score, qa + qb, newboard, made, burnt

        for _ in range(min(60, len(initial_route) - first - 1)):
            choices = []
            kept = set()
            for q, board, path in frontier:
                aopts = self.group(0, q[:3])
                bopts = self.group(1, q[3:])
                atop = sorted(aopts, key=lambda a: -evaluate(a, bopts[0], board)[0])[:4]
                btop = sorted(bopts, key=lambda b: -evaluate(aopts[0], b, board)[0])[:4]
                for aa, bb in ((atop, bopts), (aopts, btop)):
                    for a in aa:
                        for b in bb:
                            score, ns, nb, made, burnt = evaluate(a, b, board)
                            key = ns, nb
                            if key in seen or key in kept:
                                continue
                            if nb & target == target and not nb & halo:
                                return prefix + path + [(ns, made, burnt)]
                            if len(choices) < width or score > choices[-1][0]:
                                kept.add(key)
                                choices.append((score, ns, nb, path + [(ns, made, burnt)]))
                                choices.sort(key=lambda v: -v[0])
                                del choices[width:]
            if not choices:
                break
            frontier = [(q, board, path) for _, q, board, path in choices]
            seen.update((q, board) for q, board, _ in frontier)
        return None

    def pool_jump(self, current, missing, local_gain, local_cost):
        best = None
        best_gain = local_gain
        best_cost = local_cost
        fast = None
        fast_gain = local_gain
        fast_cost = local_cost
        for goal, paint in getattr(self, 'pool', []):
            gain = bin(paint & missing).count('1')
            if not gain:
                continue
            distance = max([abs(current[e] // 2 - v // 2)
                            for e, v in enumerate(goal) if v & 1] or [0])
            cost = distance + 1 + any(v & 1 for v in current)
            if gain * best_cost > best_gain * cost:
                best_gain, best_cost = gain, cost
                best = goal, paint
            lower = max([abs(current[e] // 2 - v // 2) + ((current[e] ^ v) & 1)
                         if v & 1 else (current[e] & 1)
                         for e, v in enumerate(goal)])
            lower = max(1, lower)
            if lower < cost and gain * fast_cost > fast_gain * lower:
                fast_gain, fast_cost = gain, lower
                fast = goal, lower, cost
        if fast is not None and local_gain <= 2:
            goal, lower, upper = fast
            destination = tuple(v if v & 1 else current[e] & ~1
                                for e, v in enumerate(goal))
            for ticks in range(lower, min(upper, lower + 2)):
                if fast_gain * local_cost <= local_gain * ticks:
                    break
                path = self.connect(current, destination, missing, ticks)
                if path is not None:
                    return path
        if best is None:
            return None
        goal, paint = best
        q = [v & ~1 for v in current]
        states = []
        if tuple(q) != current:
            states.append((tuple(q), 0, 0))
        destination = [v & ~1 if v & 1 else q[e] for e, v in enumerate(goal)]
        while q != destination:
            q = [v + (2 if g > v else -2 if g < v else 0)
                 for v, g in zip(q, destination)]
            states.append((tuple(q), 0, 0))
        q = tuple(v | (goal[e] & 1) for e, v in enumerate(q))
        states.append((q, paint, 0))
        return states

    def connect(self, current, goal, missing, ticks):
        frontier = [(current, missing, [])]
        tried = 0
        for tick in range(ticks):
            remaining = ticks - tick - 1
            candidates = []
            seen = set()
            for q, need, path in frontier:
                groups = []
                for group in range(2):
                    group_goal = goal[3 * group:3 * group + 3]
                    options = []
                    for entry in self.group(group, q[3 * group:3 * group + 3]):
                        qq = entry[0]
                        if all(abs(a // 2 - b // 2) + ((a ^ b) & 1) <= remaining
                               for a, b in zip(qq, group_goal)):
                            options.append(entry)
                    groups.append(options)
                for qa, ua, oa, ta, tat, bat, _ in groups[0]:
                    if bat:
                        continue
                    for qb, ub, ob, tb, tbt, bbt, _ in groups[1]:
                        tried += 1
                        if tried > 12000:
                            return None
                        if bbt or (tat & ub) or (tbt & ua):
                            continue
                        made = (ta & ~ub) | (tb & ~ua) | (oa & ob)
                        if made & self.halo:
                            continue
                        ns = qa + qb
                        if ns in seen:
                            continue
                        seen.add(ns)
                        paint = made & self.target
                        after = need & ~paint
                        distance = sum(abs(a // 2 - b // 2) + ((a ^ b) & 1)
                                       for a, b in zip(ns, goal))
                        rank = -bin(after).count('1') * 10000 - distance
                        if len(candidates) < 4 or rank > candidates[-1][0]:
                            candidates.append((rank, ns, after, path + [(ns, paint, 0)]))
                            candidates.sort(key=lambda v: -v[0])
                            del candidates[4:]
            if not candidates:
                return None
            frontier = [(q, after, path) for _, q, after, path in candidates]
        return frontier[0][2]

    def global_starts(self):
        rng = Random(2309)
        found = {}
        opts = [self.base.centre] + list(range(1, self.n, 2))
        for trial in range(40):
            q = [2 * rng.choice(self.positions)[e] + 1 for e in range(6)]
            for turn in range(4):
                order = list(range(6))
                rng.shuffle(order)
                for e in order:
                    best_score = -10 ** 9
                    best_value = q[e]
                    for v in opts:
                        q[e] = v
                        union = double = triple = 0
                        for f, w in enumerate(q):
                            beam = self.beams[f][w]
                            triple |= double & beam
                            double |= union & beam
                            union |= beam
                        made = double & ~triple
                        bad = (made & self.halo) | (triple & self.target)
                        paint = made & self.target
                        score = (bin(paint).count('1') * 10000
                                 - bin(bad).count('1') * 100000
                                 + bin(union & self.target).count('1') * 10
                                 + rng.randrange(8))
                        if score > best_score:
                            best_score = score
                            best_value = v
                        if not bad and paint:
                            config = tuple(q)
                            distance = max(abs(w // 2 - (self.r - 1)) for w in q)
                            if paint not in found or distance < found[paint][0]:
                                found[paint] = distance, config
                    q[e] = best_value
        choices = sorted(found, key=lambda mask:
                         (-bin(mask).count('1'), found[mask][0]))
        self.pool = [(found[mask][1], mask) for mask in choices[:300]]
        return [found[mask][1] for mask in choices[:2]]

    def program(self, states, required, cutoff=None):
        previous = self.initial
        matter = 0
        count = 0
        result = []
        repeat_start = next(i for i in range(1, len(states)) if states[i][1])
        sequence = states[1:]
        reverse = True
        while True:
            for q, paint, burn in sequence:
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
                result.append(' '.join(line))
                previous = q
                matter = (matter | paint) & ~burn
                if matter & self.target == self.target and not matter & self.halo:
                    count += 1
                    matter &= ~self.target
                    if count == required:
                        if any(v & 1 for v in q):
                            result.append(' '.join('T' if v & 1 else '-' for v in q))
                        return result
                if cutoff is not None and len(result) >= cutoff:
                    return None
            sequence = states[repeat_start:][::-1] if reverse else states[repeat_start:]
            reverse = not reverse


    def static_groups(self, group):
        offset = group * 3
        opts = [-1] + list(range(self.m))
        result = []
        for a in opts:
            aa = self.beams[offset][2 * a + 1] if a >= 0 else 0
            for b in opts:
                bb = self.beams[offset + 1][2 * b + 1] if b >= 0 else 0
                ab = aa & bb
                for c in opts:
                    cc = self.beams[offset + 2][2 * c + 1] if c >= 0 else 0
                    triple = ab & cc
                    if triple & self.target:
                        continue
                    union = aa | bb | cc
                    double = (ab | (aa & cc) | (bb & cc)) & ~triple
                    single = union & ~(double | triple)
                    result.append(((a, b, c), union, single, double,
                                   double & self.target))
        return result

    def setup(self, q):
        """Reach a chosen first firing configuration with the beams off."""
        current = list(self.initial)
        states = [(self.initial, 0, 0)]
        goal = [v & ~1 for v in q]
        while current != goal:
            current = [v + (2 if g > v else -2 if g < v else 0)
                       for v, g in zip(current, goal)]
            states.append((tuple(current), 0, 0))
        paint, burn = self.effects(q)
        states.append((q, paint, burn))
        return states

    def short_cycles(self, required, best):
        """Enumerate static firing sets and seek one- or two-tick cycles."""
        groups = self.static_groups(0), self.static_groups(1)
        by_mask = {}
        full_best = None
        full_cost = 1000000
        centre = self.r - 1
        for qa, ua, oa, ta, tat in groups[0]:
            for qb, ub, ob, tb, tbt in groups[1]:
                if (tat & ub) or (tbt & ua):
                    continue
                made = (ta & ~ub) | (tb & ~ua) | (oa & ob)
                if made & self.halo:
                    continue
                paint = made & self.target
                if not paint:
                    continue
                q = qa + qb
                if paint == self.target:
                    cost = max(abs(v - centre) for v in q if v >= 0)
                    if cost < full_cost:
                        full_cost = cost
                        full_best = q
                by_mask.setdefault(paint, []).append(q)
        if full_best is not None:
            q = tuple(2 * v + 1 if v >= 0 else self.base.centre for v in full_best)
            route = self.setup(q)
            prog = self.program(route, required, len(best))
            if prog is not None and len(prog) < len(best):
                best = prog
            return best
        masks = list(by_mask)
        masks.sort(key=lambda v: -bin(v).count('1'))
        self.pool = []
        for mask in masks[:300]:
            q = min(by_mask[mask], key=lambda q:
                    max(abs(v - centre) for v in q if v >= 0))
            self.pool.append((tuple(2 * v + 1 if v >= 0 else self.base.centre
                                    for v in q), mask))
        self.static_starts = []
        for mask in masks[:2]:
            q = min(by_mask[mask], key=lambda q:
                    max(abs(v - centre) for v in q if v >= 0))
            self.static_starts.append(tuple(2 * v + 1 if v >= 0 else self.base.centre
                                            for v in q))
        size = bin(self.target).count('1')
        pair_cost = 1000000
        chosen = None
        for i, ma in enumerate(masks):
            if 2 * bin(ma).count('1') < size:
                break
            qa_list = by_mask[ma]
            needed = self.target & ~ma
            for mb in masks[i:]:
                if mb & needed != needed:
                    continue
                qb_list = by_mask[mb]
                for qa in qa_list:
                    for qb in qb_list:
                        if any(a >= 0 and b >= 0 and abs(a - b) > 1
                               for a, b in zip(qa, qb)):
                            continue
                        first = tuple(2 * (a if a >= 0 else b if b >= 0 else centre)
                                      + (a >= 0) for a, b in zip(qa, qb))
                        second = tuple(2 * (b if b >= 0 else a if a >= 0 else centre)
                                       + (b >= 0) for a, b in zip(qa, qb))
                        first_cost = max(abs(v // 2 - centre) for v in first)
                        second_cost = max(abs(v // 2 - centre) for v in second)
                        cost = min(first_cost, second_cost)
                        if cost < pair_cost:
                            pair_cost = cost
                            chosen = (first, second) if first_cost <= second_cost else (second, first)
        if chosen is not None:
            first, second = chosen
            route = self.setup(first)
            route.append((second, self.effect(second), 0))
            # A two-state cycle needs no repeated endpoint tick.
            q = self.initial
            out = []
            missing = self.target
            copies = 0
            schedule = route[1:]
            while copies < required:
                for ns, paint, burn in schedule:
                    line = []
                    for old, new in zip(q, ns):
                        line.append('-' if old == new else 'T' if old // 2 == new // 2
                                    else 'F' if new == old + 2 else 'B')
                    out.append(' '.join(line))
                    q = ns
                    missing &= ~paint
                    if not missing:
                        copies += 1
                        missing = self.target
                        if copies == required:
                            break
                schedule = [(first, self.effect(first), 0), (second, self.effect(second), 0)]
            out.append(' '.join('T' if v & 1 else '-' for v in q))
            if len(out) < len(best):
                best = out
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
        best = builder.build(required)
        if required:
            six = SixBuilder(builder)
            if r <= 5:
                best = six.short_cycles(required, best)
                starts = getattr(six, 'static_starts', [])
            else:
                starts = six.global_starts()
            best_route = None
            best_six_size = 10 ** 9
            for seed in (1, 17):
                route = six.route(seed)
                prog = six.program(route, required, len(best))
                if prog is not None and len(prog) < len(best):
                    best = prog
                size = len(prog) if prog is not None else 10 ** 9
                if best_route is None or size < best_six_size:
                    best_route, best_six_size = route, size
            for start in starts:
                route = six.route(1, start)
                prog = six.program(route, required, len(best))
                if prog is not None and len(prog) < len(best):
                    best = prog
                if prog is not None and len(prog) < best_six_size:
                    best_route, best_six_size = route, len(prog)
            if required > 1 and len(best) > 2 * required + r + 2:
                prog = six.online(best_route, required, len(best))
                if prog is not None and len(prog) < len(best):
                    best = prog
            if r <= 8 and len(builder.targets) <= 65 and len(best) > 3 * required + r:
                route = six.beam_route(best_route)
                if route is not None:
                    prog = six.program(route, required, len(best))
                    if prog is not None and len(prog) < len(best):
                        best = prog
        programs.append('\n'.join(best))
    return '\n\n'.join(programs)
