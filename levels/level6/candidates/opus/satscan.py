"""Free (K,m) cycle scan below the current repeat rate, best rate last: for each pattern, candidates with
K/m < current rate (m <= MMAX) from the highest rate down; a SAT cycle is turned into a program
(SAT prefix + rotated cycle) and saved when shorter. Stops a pattern after 2 consecutive failed rates.
Usage: satscan.py <i,j,..> [cycle tmo ms=120000] [prefix tmo ms=30000]   env MMAX (3)"""
import json, os, sys, time
from harness import LEVEL, cases, load_best, save_best, valid
from satcyc import cycle_only, build_from_cycle, sub_ticks

NAME = '2-medium'
cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % NAME)).read_text()))
ids = [int(x) for x in sys.argv[1].split(',')]
tmo = int(sys.argv[2]) if len(sys.argv) > 2 else 120000
ptmo = int(sys.argv[3]) if len(sys.argv) > 3 else 30000
MMAX = int(os.environ.get('MMAX', '3'))
out = '/private/tmp/claude-501/-Users-laurenzwurdinger-Documents-dev-CodingContest/' \
      '5e9e1394-2f05-4762-ad31-a81358130714/scratchpad/cycles'
os.makedirs(out, exist_ok=True)
for i in ids:
    r, pat, count = cs[i]
    best = load_best(NAME)[i]
    st = sub_ticks(r, pat, best)
    if len(st) < 2:
        continue
    g = (st[-1] - st[0]) / (len(st) - 1)
    cands = sorted({(K / m, K, m) for m in range(1, MMAX + 1) for K in range(1, int(g * m) + 1)
                    if K / m < g - 1e-9}, key=lambda x: (-x[0], x[1]))
    fails = 0
    k = 0
    while k < len(cands) and fails < 2:
        rate = cands[k][0]
        group = [c for c in cands[k:] if abs(c[0] - rate) < 1e-9]
        k += len(group)
        ok = False
        for _, K, m in group:
            t = time.time()
            res = cycle_only(r, pat, K, m, tmo, want_cfg=True)
            tag = 'UNSAT' if res is None else res if res == 'unknown' else 'SAT'
            msg = ''
            if tag == 'SAT':
                ok = True
                cfg, subs = res
                json.dump({'cfg': cfg, 'subs': subs}, open(os.path.join(out, 'cyc_%d_%d_%d.json' % (i, K, m)), 'w'))
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
            print('pattern %d rate %.2f: K=%d m=%d %s %.0fs%s' % (i, g, K, m, tag, time.time() - t, msg), flush=True)
            if ok:
                break
        fails = 0 if ok else fails + 1
print('done', flush=True)
