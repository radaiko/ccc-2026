import sys, time
sys.path.insert(0, '/Users/laurenzwurdinger/Documents/dev/CodingContest/ccc-2026/levels/level6/candidates/opus')
from harness import *
import satcyc, z3sat
from resuffixL import sub_ticks
from runin2 import configs, to_offsets
name, i, s, q, T0, tmo, extra = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), int(sys.argv[6]), int(sys.argv[7])
cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % name)).read_text()))
r, pat, count = cs[i]
B = load_best(name)[i]
st = sub_ticks(r, pat, B)
tgt = to_offsets(r, configs(r, B, st)[st[s]])
md = satcyc.Model(r, pat)
start = md.fixed_start()
pre = [md.config() for _ in range(T0)]
prev, M, Ss = start, None, []
for t in range(T0):
    md.trans(prev, pre[t])
    M, S = md.tick(pre[t], M)
    Ss.append(S)
    prev = pre[t]
md.add([Ss[-1]])
if q > 1:
    satcyc.atleast(md, Ss[:-1], q - 1)
for e in range(6):
    pos, act = pre[-1][e]
    o, a = tgt[e]
    md.add([pos[md.offs.index(o)]])
    md.add([act if a else -act])
if extra:
    # reachability from start and to target: |o(t) - 0| <= t+1 and |o(t) - o_T| <= T0 - 1 - t
    for t in range(T0):
        for e in range(6):
            pos, act = pre[t][e]
            for oi, o in enumerate(md.offs):
                if abs(o) > t + 1 or abs(o - tgt[e][0]) > T0 - 1 - t:
                    md.add([-pos[oi]])
    # no submission possible before f_min: first submissions need >= fmin ticks
t0 = time.time()
res = z3sat.solve(md.nv, md.cl, tmo)
print('extra', extra, 'res', 'UNSAT' if res is None else res if res == 'unknown' else 'SAT', '%.1fs' % (time.time() - t0), md.nv, len(md.cl))
