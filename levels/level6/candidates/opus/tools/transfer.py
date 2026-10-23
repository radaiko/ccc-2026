"""Crazy idea: reuse a pattern's program for another pattern of the same radius under the 12 board symmetries
(60-degree rotation = emitter e -> e+1; mirror = emitters 2<->6, 3<->5 with F<->B). Keep verified shorter ones."""
import sys
sys.path.insert(0, '/Users/laurenzwurdinger/Documents/dev/CodingContest/ccc-2026/levels/level6/candidates/opus')
from harness import LEVEL, cases, load_best, save_best
from levels.level6.candidates.astra import simulate
MIR = [0, 5, 4, 3, 2, 1]
SW = {'F': 'B', 'B': 'F', 'T': 'T', '-': '-'}
def transforms(prog):
    rows = [l.split() for l in prog]
    for mir in (0, 1):
        base = [[SW[r[MIR[e]]] for e in range(6)] for r in rows] if mir else rows
        for k in range(6):
            yield [' '.join(r[(e - k) % 6] for e in range(6)) for r in base]
names = sys.argv[1:] or ['1-small', '2-medium', '3-large', '4-enormous']
for name in names:
    cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % name)).read_text()))
    best = load_best(name)
    size = [sum(row.count('M') for row in p) for r, p, c in cs]
    won = 0
    for j, (r, pat, c) in enumerate(cs):
        for i in range(len(cs)):
            if i == j or cs[i][0] != r or size[i] != size[j] or len(best[i]) >= len(best[j]):
                continue
            for t in transforms(best[i]):
                prog = [l.split() for l in t]
                if simulate(r, pat, prog) >= c:
                    lo = len(prog)
                    while lo > 1 and simulate(r, pat, prog[:lo - 1]) >= c:
                        lo -= 1
                    if lo < len(best[j]):
                        print('%s %d <- %d: %d -> %d' % (name, j, i, len(best[j]), lo), flush=True)
                        won += len(best[j]) - lo
                        best[j] = t[:lo]
                        save_best(name, best)
                    break
    print(name, 'saved', won, flush=True)
