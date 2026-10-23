import sys, time
sys.path.insert(0, '/Users/laurenzwurdinger/Documents/dev/CodingContest/ccc-2026/levels/level6/candidates/opus')
import satanchor
from harness import LEVEL, cases, load_best
from retcyc import sim
cs = list(cases((LEVEL / 'data' / 'in_level-6_2-medium.txt').read_text()))
i, K, m = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
r, p, c = cs[i]
b = load_best('2-medium')[i]
t, pos, am = sim(r, p, b)[-2]
print('anchor act mask', am)
t0 = time.time()
res = satanchor.anchored(r, p, K, m, (pos, am), 300000, freepos=range(6))
print('UNSAT' if res is None else res if isinstance(res, str) else 'SAT', '%.1fs' % (time.time() - t0), flush=True)
