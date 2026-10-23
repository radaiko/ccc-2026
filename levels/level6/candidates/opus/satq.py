"""Quick batch of exact SAT queries. Specs: i:K[:m][:copy][:at=5,11] ... ; env SATTMO (ms, default 120000).
Prints one line per spec with result and seconds; SAT cycles are written to <scratch>/cyc_<i>_<K>_<m>.txt."""
import os, sys, time
from harness import LEVEL, cases
from satcyc import cycle_only

cs = list(cases((LEVEL / 'data' / 'in_level-6_2-medium.txt').read_text()))
tmo = int(os.environ.get('SATTMO', '120000'))
out = os.environ.get('SATOUT', '/private/tmp/claude-501/-Users-laurenzwurdinger-Documents-dev-CodingContest/'
                      '5e9e1394-2f05-4762-ad31-a81358130714/scratchpad/cycles')
os.makedirs(out, exist_ok=True)
for spec in sys.argv[1:]:
    parts = spec.split(':')
    i, K = int(parts[0]), int(parts[1])
    m = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
    free = 'copy' in parts
    at = None
    for p in parts:
        if p.startswith('at='):
            at = [int(x) for x in p[3:].split(',')]
    r, pat, count = cs[i]
    t = time.time()
    res = cycle_only(r, pat, K, m, tmo, free=free, at=at)
    tag = 'UNSAT' if res is None else res if res == 'unknown' else 'SAT'
    if tag == 'SAT':
        open(os.path.join(out, 'cyc_%d_%d_%d%s.txt' % (i, K, m, '_copy' if free else '')), 'w').write(
            '\n'.join(res) + '\n')
    print('%s: %s %.0fs' % (spec, tag, time.time() - t), flush=True)
