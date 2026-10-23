"""Crazy idea 2: pattern j = pattern i shifted by v -> each emitter's lines shift by a constant d_e; program for j =
run-in moving every emitter by d_e (inactive) + i's program. Keep simulation-verified shorter programs."""
import sys
sys.path.insert(0, '/Users/laurenzwurdinger/Documents/dev/CodingContest/ccc-2026/levels/level6/candidates/opus')
from harness import LEVEL, cases, load_best, save_best
from levels.level6.candidates.astra import simulate, ring, DIRS
def cells(p):
    return sorted((y, x) for y, row in enumerate(p) for x, ch in enumerate(row) if ch == 'M')
def cov(r, e, cell, ri):
    y, x = cell
    dy, dx = DIRS[e]
    while (y, x) not in ri:
        y -= dy; x -= dx
    return ri[(y, x)]
for name in sys.argv[1:] or ['2-medium', '3-large', '4-enormous', '1-small']:
    cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % name)).read_text()))
    best = load_best(name)
    C = [cells(p) for r, p, c in cs]
    won = 0
    for j, (r, pat, c) in enumerate(cs):
        ri = {cl: k for k, cl in enumerate(ring(r))}
        m = 6 * r
        for i in range(len(cs)):
            if i == j or cs[i][0] != r or len(C[i]) != len(C[j]):
                continue
            v = (C[j][0][0] - C[i][0][0], C[j][0][1] - C[i][0][1])
            if [(y + v[0], x + v[1]) for y, x in C[i]] != C[j]:
                continue
            d = [((cov(r, e, C[j][0], ri) - cov(r, e, C[i][0], ri) + m // 2) % m) - m // 2 for e in range(6)]
            pre = []
            for t in range(max(abs(x) for x in d)):
                pre.append(' '.join(('F' if d[e] > 0 else 'B') if t < abs(d[e]) else '-' for e in range(6)))
            prog = pre + best[i]
            rows = [l.split() for l in prog]
            if len(prog) < len(best[j]) and simulate(r, pat, rows) >= c:
                lo = len(rows)
                while lo > 1 and simulate(r, pat, rows[:lo - 1]) >= c:
                    lo -= 1
                print('%s %d <- %d shifted %s: %d -> %d' % (name, j, i, d, len(best[j]), lo), flush=True)
                won += len(best[j]) - lo
                best[j] = prog[:lo]
                save_best(name, best)
    print(name, 'saved', won, flush=True)
