from functools import lru_cache


DIRS = ((0, 2), (1, 1), (1, -1), (0, -2), (-1, -1), (-1, 1))


@lru_cache(None)
def sources(radius):
    border = []
    y, x = radius, 0
    for dy, dx in ((-1, 1), (0, 2), (1, 1), (1, -1), (0, -2), (-1, -1)):
        for _ in range(radius):
            border.append((y, x))
            y += dy
            x += dx
    inside = set()
    for y in range(1, 2 * radius):
        pad = abs(y - radius)
        for x in range(pad + 2, 4 * radius - pad, 2):
            inside.add((y, x))
    result = []
    for e, (dy, dx) in enumerate(DIRS):
        mapping = {}
        for pos, (y, x) in enumerate(border):
            offset = (pos - e * radius + 3 * radius) % (6 * radius) - 3 * radius
            y += dy
            x += dx
            while (y, x) in inside:
                mapping[y, x] = offset
                y += dy
                x += dx
        result.append(mapping)
    return result


def transition_cost(a, b, c, d):
    da, db = abs(c - a), abs(d - b)
    if da <= 1 and db <= 1:
        return 1
    return min(max(da + 2, db), max(da, db + 2))


def choose_plan(radius, cells, copies):
    maps = sources(radius)
    best = None
    for e in range(6):
        for f in range(6):
            if e == f or (e - f) % 6 == 3:
                continue
            groups = {}
            for cell in cells:
                a, b = maps[e][cell], maps[f][cell]
                groups.setdefault(a, []).append(b)
            rows = [(a, sorted(bs)) for a, bs in sorted(groups.items())]
            for initial_reverse in (False, True):
                sequence = []
                for rep in range(copies):
                    sequence.extend(reversed(rows) if bool(rep % 2) ^ initial_reverse else rows)
                costs = None
                parents = []
                previous_a = previous_bs = None
                for a, bs in sequence:
                    endpoints = (bs[0], bs[-1])
                    span = bs[-1] - bs[0]
                    new_costs = []
                    back = []
                    for direction in (0, 1):
                        start = endpoints[direction]
                        if costs is None:
                            new_costs.append(max(abs(a), abs(start)) + 1 + span)
                            back.append(-1)
                        else:
                            candidates = [
                                costs[old] + transition_cost(previous_a, previous_bs[-1 if old == 0 else 0], a, start) + span
                                for old in (0, 1)
                            ]
                            old = 0 if candidates[0] <= candidates[1] else 1
                            new_costs.append(candidates[old])
                            back.append(old)
                    costs = new_costs
                    parents.append(back)
                    previous_a, previous_bs = a, bs
                direction = 0 if costs[0] <= costs[1] else 1
                score = costs[direction]
                if best is None or score < best[0]:
                    chosen = []
                    for i in range(len(sequence) - 1, -1, -1):
                        a, bs = sequence[i]
                        chosen.append((a, bs if direction == 0 else bs[::-1]))
                        direction = parents[i][direction]
                    chosen.reverse()
                    best = (score, e, f, chosen)
    return best


def make_program(radius, cells, copies):
    score, e, f, rows = choose_plan(radius, cells, copies)
    output = []
    templates = {}
    for one in ('-', 'F', 'B', 'T'):
        for two in ('-', 'F', 'B', 'T'):
            line = ['-'] * 6
            line[e], line[f] = one, two
            templates[one, two] = ' '.join(line)

    def emit(one, two):
        output.append(templates[one, two])

    def movement(delta):
        return 'F' if delta > 0 else 'B' if delta < 0 else '-'

    a = b = 0
    active = False

    def visit(c, d):
        nonlocal a, b, active
        da, db = c - a, d - b
        na, nb = abs(da), abs(db)
        ia, ib = movement(da), movement(db)
        if not active:
            for t in range(max(na, nb)):
                emit(ia if t < na else '-', ib if t < nb else '-')
            emit('T', 'T')
            active = True
        elif na <= 1 and nb <= 1:
            # Both beams reach their next target in this single tick.
            emit(ia, ib)
        else:
            # Toggle one beam off during travel. The other can move during
            # both toggle ticks, so crossing a gap often costs no extra time.
            gate_a = max(na + 2, nb) <= max(na, nb + 2)
            length = max(na + 2, nb) if gate_a else max(na, nb + 2)
            for t in range(length):
                if gate_a:
                    one = 'T' if t == 0 or t == length - 1 else ia if t <= na else '-'
                    two = ib if t < nb else '-'
                else:
                    one = ia if t < na else '-'
                    two = 'T' if t == 0 or t == length - 1 else ib if t <= nb else '-'
                emit(one, two)
        a, b = c, d

    for row, coordinates in rows:
        for column in coordinates:
            visit(row, column)
    assert len(output) == score
    emit('T', 'T')
    return '\n'.join(output)


def solve(text: str):
    tokens = text.split()
    n = int(tokens[0])
    p = 1
    result = []
    for _ in range(n):
        radius, height, width, copies = map(int, tokens[p:p + 4])
        p += 4
        pattern = tokens[p:p + height]
        p += height
        cells = [(y, x) for y, row in enumerate(pattern) for x, c in enumerate(row) if c == 'M']
        result.append(make_program(radius, cells, copies))
    return '\n\n'.join(result)
