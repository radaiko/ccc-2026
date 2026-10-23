"""Per-copy lower bounds by exact SAT: a copy (from ANY emitter configuration, empty matter) in exactly j ticks.
If copies of 1..k ticks are all UNSAT, every copy needs >= k+1 ticks, so a pattern whose current repeat rate is
k+1 is optimal in its repeats. Prints one line per pattern.
Usage: satlb.py <input-name> <i,j,..> [timeout_ms]"""
import sys
from harness import LEVEL, cases, load_best
from satcyc import cycle_only, sub_ticks

name, sel = sys.argv[1], sys.argv[2]
tmo = int(sys.argv[3]) if len(sys.argv) > 3 else 600000
cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % name)).read_text()))
for i in [int(x) for x in sel.split(',')]:
    r, pat, count = cs[i]
    best = load_best(name)[i]
    subs = sub_ticks(r, pat, best)
    g = (subs[-1] - subs[0]) / (len(subs) - 1) if len(subs) > 1 else 0
    res = 'SAT'
    j = 0
    stat = []
    for j in range(1, int(-(-g // 1))):
        res = cycle_only(r, pat, j, 1, tmo, free=True)
        res = 'UNSAT' if res is None else res if res == 'unknown' else 'SAT'
        stat.append('%d:%s' % (j, res))
        if res != 'UNSAT':
            break
    verdict = 'OPTIMAL' if all(x.endswith('UNSAT') for x in stat) else 'open'
    print('pattern %d: rate %.2f count %d copy %s -> %s' % (i, g, count, ' '.join(stat), verdict), flush=True)
