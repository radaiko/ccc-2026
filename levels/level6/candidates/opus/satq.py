"""Quick batch of exact SAT queries. Specs: i:K[:m][:copy][:at=5,11] ... ; env SATTMO (ms, default 120000).
Prints one line per spec; for a SAT (non-copy) cycle it builds prefix + cycle (SAT prefix) and saves the
program via harness.save_best when it beats the current best."""
import json, os, sys, time
from harness import LEVEL, cases, load_best, save_best, valid
from satcyc import cycle_only, build_from_cycle

NAME = '2-medium'
cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % NAME)).read_text()))
tmo = int(os.environ.get('SATTMO', '120000'))
ptmo = int(os.environ.get('SATPTMO', '30000'))
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
    res = cycle_only(r, pat, K, m, tmo, free=free, at=at, want_cfg=True)
    tag = 'UNSAT' if res is None else res if res == 'unknown' else 'SAT'
    msg = ''
    if tag == 'SAT':
        cfg, subs = res
        json.dump({'cfg': cfg, 'subs': subs}, open(os.path.join(
            out, 'cyc_%d_%d_%d%s.json' % (i, K, m, '_copy' if free else '')), 'w'))
        if not free:
            B = len(load_best(NAME)[i])
            prog = build_from_cycle(r, pat, count, cfg, subs, B, ptmo)
            if prog and valid(r, pat, count, prog):
                b = load_best(NAME)
                if len(prog) < len(b[i]):
                    msg = ' IMPROVED %d -> %d' % (len(b[i]), len(prog))
                    b[i] = prog
                    save_best(NAME, b)
                else:
                    msg = ' built %d (best %d)' % (len(prog), len(b[i]))
            else:
                msg = ' no program < %d' % B
    print('%s: %s %.0fs%s' % (spec, tag, time.time() - t, msg), flush=True)
