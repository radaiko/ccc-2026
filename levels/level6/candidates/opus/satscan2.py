"""Like satscan.py but multi-copy cycles are split by their copy lengths: for (K, m) every composition of K into
m copy lengths >= kmin (up to rotation) is a separate SAT query with fixed submission ticks (easier than the
free 'at least m' form). kmin = smallest copy length not proven impossible (free copy SAT query, short timeout).
Usage: satscan2.py <i,j,..> [cycle tmo ms=300000] [prefix tmo=30000]   env MMAX (3), KMINTMO (60000)"""
import itertools, json, os, sys, time
from harness import LEVEL, cases, load_best, save_best, valid
from satcyc import cycle_only, build_from_cycle, sub_ticks

NAME = '2-medium'
cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % NAME)).read_text()))
ids = [int(x) for x in sys.argv[1].split(',')]
tmo = int(sys.argv[2]) if len(sys.argv) > 2 else 300000
ptmo = int(sys.argv[3]) if len(sys.argv) > 3 else 30000
MMAX = int(os.environ.get('MMAX', '3'))
KTMO = int(os.environ.get('KMINTMO', '60000'))
out = '/private/tmp/claude-501/-Users-laurenzwurdinger-Documents-dev-CodingContest/' \
      '5e9e1394-2f05-4762-ad31-a81358130714/scratchpad/cycles'
os.makedirs(out, exist_ok=True)


def comps(K, m, kmin):
    res = set()
    for c in itertools.product(range(kmin, K + 1), repeat=m):
        if sum(c) != K:
            continue
        rots = [c[i:] + c[:i] for i in range(m)]
        res.add(min(rots))
    return sorted(res)


for i in ids:
    r, pat, count = cs[i]
    best = load_best(NAME)[i]
    st = sub_ticks(r, pat, best)
    if len(st) < 2:
        continue
    g = (st[-1] - st[0]) / (len(st) - 1)
    kmin = 1
    while kmin < g:
        t = time.time()
        res = cycle_only(r, pat, kmin, 1, KTMO, free=True)
        tag = 'UNSAT' if res is None else res if res == 'unknown' else 'SAT'
        print('pattern %d: copy %d %s %.0fs' % (i, kmin, tag, time.time() - t), flush=True)
        if tag != 'UNSAT':
            break
        kmin += 1
    cands = sorted({(K / m, K, m) for m in range(1, MMAX + 1) for K in range(m * kmin, int(g * m) + 1)
                    if K / m < g - 1e-9}, key=lambda x: (-x[0], x[1]))
    fails = 0
    k = 0
    while k < len(cands) and fails < 2:
        rate = cands[k][0]
        group = [c for c in cands[k:] if abs(c[0] - rate) < 1e-9]
        k += len(group)
        ok = False
        for _, K, m in group:
            for comp in comps(K, m, kmin):
                at = list(itertools.accumulate(comp))
                t = time.time()
                res = cycle_only(r, pat, K, m, tmo, want_cfg=True, at=at)
                tag = 'UNSAT' if res is None else res if res == 'unknown' else 'SAT'
                msg = ''
                if tag == 'SAT':
                    ok = True
                    cfg, subs = res
                    json.dump({'cfg': cfg, 'subs': subs},
                              open(os.path.join(out, 'cyc_%d_%d_%d.json' % (i, K, m)), 'w'))
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
                print('pattern %d rate %.2f: K=%d m=%d copies %s %s %.0fs%s' % (i, g, K, m, comp, tag,
                      time.time() - t, msg), flush=True)
                if ok:
                    break
            if ok:
                break
        fails = 0 if ok else fails + 1
print('done', flush=True)
