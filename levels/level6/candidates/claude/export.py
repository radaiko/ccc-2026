import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import recon, recon2
L = '/home/user/ccc-2026/levels/level6'
S = os.path.dirname(os.path.abspath(__file__))
tot_old = tot_new = 0
for n in ['1-small', '2-medium', '3-large', '4-enormous']:
    cur = [b.splitlines() for b in re.split(r'\n\s*\n', open(L + '/output/out_level-6_%s.txt' % n).read().strip())]
    o2 = L + '/output2/out_level-6_%s.txt' % n
    srcs = [L + '/runs/opus/out_level-6_%s.txt' % n, o2]
    c = json.load(open(S + '/cands_%s.json' % n))
    best = [p[:] for p in cur]
    for f in srcs:
        if not os.path.exists(f):
            continue
        progs = [b.splitlines() for b in re.split(r'\n\s*\n', open(f).read().strip())]
        if len(progs) != len(cur):
            continue
        for i, p in enumerate(progs):
            if len(p) >= len(best[i]):
                continue
            pl = [l.split() for l in p]
            ok = True
            for R, C, nn, t, mn in c[str(i)]:
                if mn <= 0:
                    continue
                g = recon.geom(R)
                P = recon2.tomask(C); H = recon2.tomask(recon.halo_of(g, set(C)))
                if recon2.bsim(R, pl, P, H) < mn:
                    ok = False; break
            if ok:
                best[i] = p
    a, b = sum(map(len, cur)), sum(map(len, best))
    tot_old += a; tot_new += b
    print(n, a, '->', b)
    os.makedirs(L + '/output2', exist_ok=True)
    open(o2, 'w').write('\n\n'.join('\n'.join(p) for p in best) + '\n')
print('total', tot_old, '->', tot_new)
