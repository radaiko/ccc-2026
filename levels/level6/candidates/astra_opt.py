"""Score-oriented beam search, with a verified two-emitter upper bound."""
from time import process_time
import random
from functools import lru_cache

from levels.level6.candidates.astra import (
    DIRS, NB, board, ring, cases, check, generate as baseline,
    cover_walk,
)


def geometry(r, pat):
    targets = [(y, x) for y, row in enumerate(pat) for x, c in enumerate(row) if c == 'M']
    target_set = set(targets)
    g = board(r)
    halo = sorted({(y + dy, x + dx) for y, x in targets for dy, dx in NB
                   if 0 <= y + dy < len(g) and 0 <= x + dx < len(g[0])
                   and g[y + dy][x + dx] == 'O'} - target_set)
    indices = {cell: 1 << i for i, cell in enumerate(targets + halo)}
    target = (1 << len(targets)) - 1
    forbidden = ((1 << len(indices)) - 1) ^ target
    perimeter = ring(r)
    rays = []
    for e, (dy, dx) in enumerate(DIRS):
        ray = []
        for offset in range(1 - r, r):
            y, x = perimeter[(e * r + offset) % (6 * r)]
            mask = 0
            y += dy
            x += dx
            while 0 <= y < len(g) and 0 <= x < len(g[0]) and g[y][x] == 'O':
                mask |= indices.get((y, x), 0)
                y += dy
                x += dx
            ray.extend((0, mask))
        rays.append(ray)
    return target, forbidden, rays


def static_program(r, target, forbidden, rays, required):
    """Find an exact static six-beam configuration: then every tick is a pickup.

    Each target must be covered by exactly two of six chosen lines. Propagate
    these cardinality constraints over six small finite domains.
    """
    domains = [(1 << (2 * r)) - 1] * 6  # choice 0 is off
    masks = [[0] + ray[1::2] for ray in rays]
    if sum(max((mask & target).bit_count() for mask in row) for row in masks) < 2 * target.bit_count():
        return None
    coverage = []
    for cell in range(target.bit_count()):
        bit = 1 << cell
        coverage.append([sum(1 << p for p, mask in enumerate(row) if mask & bit)
                         for row in masks])
    failures = set()

    def dfs(ds):
        ds = list(ds)
        changed = True
        while changed:
            changed = False
            for cover in coverage:
                possible = [e for e in range(6) if ds[e] & cover[e]]
                certain = [e for e in possible if not (ds[e] & ~cover[e])]
                if len(possible) < 2 or len(certain) > 2:
                    return None
                if len(certain) == 2:
                    for e in possible:
                        if e not in certain:
                            new = ds[e] & ~cover[e]
                            if new != ds[e]:
                                ds[e] = new
                                changed = True
                elif len(possible) == 2:
                    for e in possible:
                        new = ds[e] & cover[e]
                        if new != ds[e]:
                            ds[e] = new
                            changed = True
        key = tuple(ds)
        if key in failures:
            return None
        if all(d.bit_count() == 1 for d in ds):
            settings = [d.bit_length() - 1 for d in ds]
            once = twice = three = 0
            for e, p in enumerate(settings):
                mask = masks[e][p]
                three |= twice & mask
                twice |= once & mask
                once |= mask
            created = twice & ~three
            if created & forbidden or created & target != target:
                return None
            return settings
        e = min((e for e in range(6) if ds[e].bit_count() > 1), key=lambda e: ds[e].bit_count())
        choices = [p for p in range(2 * r) if ds[e] & (1 << p)]
        choices.sort(key=lambda p: abs(p - r) if p else -1)
        for p in choices:
            trial = ds[:]
            trial[e] = 1 << p
            result = dfs(trial)
            if result is not None:
                return result
        failures.add(key)
        return None

    if dfs(domains) is None:
        return None
    for distance in range(r):
        domain = 1 | sum(1 << p for p in range(1, 2 * r) if abs(p - r) <= distance)
        settings = dfs([domain] * 6)
        if settings is None:
            continue
        program = []
        offsets = [p - r if p else 0 for p in settings]
        for step in range(max(map(abs, offsets))):
            program.append(' '.join('F' if x > step else 'B' if -x > step else '-' for x in offsets))
        program.append(' '.join('T' if p else '-' for p in settings))
        program.extend(['- - - - - -'] * (required - 1))
        return program
    return None


def finish_pattern(r, target, rays, emitters, config, painted):
    """Deterministically complete a partial beam-search state with two beams."""
    n = target.bit_count()
    coords = [[next(p - r + 1 for p in range(2 * r - 1) if rays[e][2 * p + 1] & (1 << cell))
               for e in range(3)] for cell in range(n)]
    positions = [0] * 6
    active = [False] * 6
    for i, e in enumerate(emitters):
        state = (config >> (6 * i)) & 63
        positions[e] = state // 2 - r + 1
        active[e] = bool(state & 1)
    already = [i for i in range(n) if painted & (1 << i)]
    missing = [i for i in range(n) if not painted & (1 << i)]
    best = None
    for pair in [(0, 1), (0, 2), (1, 2)]:
        points = [(c[pair[0]], c[pair[1]]) for c in coords]
        lookup = {p: i for i, p in enumerate(points)}
        adj = [[lookup[x + dx, y + dy] for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                if (dx or dy) and (x + dx, y + dy) in lookup] for x, y in points]
        start = min(missing, key=lambda v: max(abs(points[v][i] - positions[e]) for i, e in enumerate(pair)))
        route = cover_walk(points, adj, start, random.Random(0), 1, already)
        pos = positions[:]
        program = []
        if any(active):
            program.append(' '.join('T' if a else '-' for a in active))

        def emit(a, b):
            line = ['-'] * 6
            line[pair[0]], line[pair[1]] = a, b
            program.append(' '.join(line))

        def move(destination):
            while any(pos[e] != destination[i] for i, e in enumerate(pair)):
                ins = []
                for i, e in enumerate(pair):
                    delta = (destination[i] > pos[e]) - (destination[i] < pos[e])
                    pos[e] += delta
                    ins.append('F' if delta > 0 else 'B' if delta < 0 else '-')
                emit(*ins)

        move(points[route[0]])
        emit('T', 'T')
        for v in route[1:]:
            point = points[v]
            dist = max(abs(point[i] - pos[e]) for i, e in enumerate(pair))
            if dist > 1:
                emit('T', '-')
                move(point)
                emit('T', '-')
            else:
                move(point)
        end = sum((2 * (pos[e] + r - 1) + (e in pair)) << (6 * i) for i, e in enumerate(emitters))
        if best is None or len(program) < len(best[0]):
            best = program, end
    return best


@lru_cache(maxsize=24)
def prepare_emitter(ray, target, r):
    choices, reachable = [], []
    for state in range(len(ray)):
        opts = [(state, '-', ray[state]), (state ^ 1, 'T', ray[state ^ 1])]
        if state >= 2:
            opts.append((state - 2, 'B', ray[state - 2]))
        if state + 2 < len(ray):
            opts.append((state + 2, 'F', ray[state + 2]))
        choices.append(opts)
        mask = 0
        by_distance = []
        for d in range(2 * r + 1):
            radius = d - (not (state & 1))
            if radius >= 0:
                for p in (state // 2 - radius, state // 2 + radius):
                    if 0 <= p < len(ray) // 2:
                        mask |= ray[2 * p + 1] & target
            by_distance.append(mask)
        reachable.append(by_distance)
    return choices, reachable


def search(r, target, forbidden, rays, emitters, required, limit, width, deadline, initial=None,
           priority=0, bias=0.75):
    """Search simultaneous legal instructions, retaining diverse good states.

    We never create matter touching the pattern. Target matter may be erased;
    tracking it explicitly is exact even when distant waste is produced.
    """
    k = len(emitters)
    n = target.bit_count()
    selected = [rays[e] for e in emitters]
    choices = []
    reachable = []
    for ray in selected:
        emitter_choices, reach = prepare_emitter(tuple(ray), target, r)
        choices.append(emitter_choices)
        reachable.append(reach)

    cache = {}

    def successors(config):
        cached = cache.get(config)
        if cached is not None:
            return cached
        opts = [choices[e][(config >> (6 * e)) & 63] for e in range(k)]
        result = []
        # Shared prefixes avoid recomputing beam intersections for every action.
        suffix = [0] * (k + 1)
        for e in range(k - 1, -1, -1):
            suffix[e] = suffix[e + 1]
            for _, _, ray in opts[e]:
                suffix[e] |= ray
        def extend(e, code, once, twice, three):
            if twice & ~three & forbidden & ~suffix[e]:
                return
            if e == k:
                created = twice & ~three
                result.append((code, created & target, three & target))
                return
            for state, _, ray in opts[e]:
                new_three = three | (twice & ray)
                extend(e + 1, code | (state << (6 * e)),
                       once | ray, twice | (once & ray), new_three)

        extend(0, 0, 0, 0, 0)
        cache[config] = result
        return result

    def distance(config, missing):
        state_reach = [reachable[e][(config >> (6 * e)) & 63] for e in range(k)]
        for d in range(1, 2 * r + 1):
            seen = 0
            for reach in state_reach:
                mask = reach[d] & missing
                if mask & seen:
                    return d
                seen |= mask
        return 2 * r + 1

    if initial is None:
        initial = sum((2 * (r - 1)) << (6 * e) for e in range(k))
    # node = (config, painted, accepted, parent)
    nodes = [(initial, 0, 0, None)]
    seen = {(initial, 0, 0)}
    fallback = None

    def reconstruct(node):
        result = []
        while node[3] is not None:
            line = ['-'] * 6
            for i, e in enumerate(emitters):
                before = (node[3][0] >> (6 * i)) & 63
                after = (node[0] >> (6 * i)) & 63
                line[e] = 'T' if before ^ after == 1 else 'F' if after > before else 'B' if after < before else '-'
            result.append(' '.join(line))
            node = node[3]
        return result[::-1]

    for depth in range(1, limit):
        if depth >= limit:
            return fallback
        if depth % 8 == 0 and process_time() > deadline:
            return fallback
        candidates = {}
        complete = None
        complete_value = -1
        for parent in nodes:
            config, painted, accepted = parent[:3]
            for dest, created, destroyed in successors(config):
                material = (painted | created) & ~destroyed
                done = accepted
                if material == target:
                    material = 0
                    done += 1
                key = (dest, material, done)
                if key in seen or key in candidates:
                    continue
                node = (dest, material, done, parent)
                if done == required:
                    value = created.bit_count()
                    if value > complete_value:
                        complete_value, complete = value, node
                    continue
                progress = done * (n + bias * priority.bit_count()) + material.bit_count() + bias * (material & priority).bit_count()
                candidates[key] = (progress, node)
        if complete is not None:
            return reconstruct(complete), complete[0]
        if not candidates:
            return fallback
        # First discard clearly inferior progress; use a geometric lower bound
        # to keep moving toward unpainted cells when immediate progress stalls.
        ranked = sorted(candidates.values(), key=lambda item: -item[0])
        if required == 1 and depth % 8 == 0 and n - ranked[0][1][1].bit_count() <= min(24, n // 3):
            node = ranked[0][1]
            tail, end = finish_pattern(r, target, rays, emitters, node[0], node[1])
            if depth + len(tail) < limit:
                fallback = reconstruct(node) + tail, end
                limit = depth + len(tail)
        threshold = ranked[min(len(ranked), width * 8) - 1][0]
        shortlist = [item for item in ranked if item[0] >= threshold]
        ranked = []
        for progress, node in shortlist:
            dist = distance(node[0], target ^ node[1])
            ranked.append((progress * 4 - dist, progress, node))
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        nodes = []
        configurations = set()
        for _, _, node in ranked:
            # Avoid spending the whole beam on almost identical configurations.
            diversity = (node[0], node[2])
            if diversity in configurations:
                continue
            configurations.add(diversity)
            nodes.append(node)
            seen.add(node[:3])
            if len(nodes) == width:
                break
    return fallback


def generate(r, pat, required, budget=1.0):
    best = baseline(r, pat, required)
    deadline = process_time() + budget
    target, forbidden, rays = geometry(r, pat)
    static = static_program(r, target, forbidden, rays, required)
    if static is not None and len(static) < len(best):
        best = static
    if len(best) == required:
        return best
    cells = [(y, x) for y, row in enumerate(pat) for x, c in enumerate(row) if c == 'M']
    cell_set = set(cells)
    edge = sum(1 << i for i, (y, x) in enumerate(cells)
               if sum((y + dy, x + dx) in cell_set for dy, dx in NB) <= 3)
    searches = [((0, 1, 2, 3), 16, 0), ((0, 1, 2, 4), 16, 0),
                ((0, 1, 2, 5), 16, 0), ((0, 1, 2, 3, 4, 5), 16, 0),
                ((0, 1, 2, 3, 4, 5), 16, 1.5)]
    for method, (emitters, width, bias) in enumerate(searches):
        if process_time() > deadline:
            break
        method_deadline = process_time() + (deadline - process_time()) / (len(searches) - method)
        program = []
        config = None
        cycles = {}
        for _ in range(required):
            if config not in cycles:
                cycles[config] = search(r, target, forbidden, rays, emitters, 1,
                                        len(best) - len(program), width, method_deadline, config,
                                        priority=edge, bias=bias)
            result = cycles[config]
            if result is None:
                break
            part, config = result
            program.extend(part)
        else:
            if len(program) < len(best):
                best = program
    return best


def solve(text):
    inputs = list(cases(text))
    weights = [sum(row.count('M') for row in pat) ** 1.2 for _, pat, _ in inputs]
    total = sum(weights)
    deadline = process_time() + 240
    result = []
    for (r, pat, count), weight in zip(inputs, weights):
        budget = max(0.01, (deadline - process_time()) * weight / total)
        result.append('\n'.join(generate(r, pat, count, budget)))
        total -= weight
    return '\n\n'.join(result)
