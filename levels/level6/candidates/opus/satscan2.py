"""Anchor-neighbourhood SAT scan: fix 4 emitters of a base anchor, leave 2 emitters completely free (position and
on/off), ask for a (K, m) cycle (one query covers ~(2r+1)^2*4 anchors, ~1-2 s on r=5 patterns). Base anchors =
submission configs of the best program. On SAT: beam run-in into the cycle phases, save if shorter, record cycle.
Usage: python3 satscan2.py <name> <idx> <m> <K> <deadline epoch> [tmo_ms]"""
import itertools
import json
import fcntl
import sys
import time
from harness import LEVEL, cases, load_best, save_best, valid
from retcyc import sim, assemble, runin_variants
from satanchor import anchored

name, i, m, K, deadline = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5])
tmo = int(sys.argv[6]) if len(sys.argv) > 6 else 10000
nfree = int(sys.argv[7]) if len(sys.argv) > 7 else 2
inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
r, pat, count = list(cases(inp.read_text()))[i]
prog = load_best(name)[i]
subs = sim(r, pat, prog)
bases = []
for t, pos, am in subs[:count - 1]:
    if (pos, am) not in bases:
        bases.append((pos, am))
weights = '100,1,0.3,0.5,1'.split(',')
nq = 0
for base in bases:
    for fe in itertools.combinations(range(6), nfree):
        if time.time() > deadline:
            print('deadline, queries', nq, flush=True)
            sys.exit(0)
        nq += 1
        res = anchored(r, pat, K, m, base, tmo, freeE=fe, want_cfg=True)
        if not isinstance(res, tuple):
            continue
        cyc, anc = res
        cur = load_best(name)[i]
        alt = runin_variants(inp, i, r, pat, count, anc, cyc, 20000, '1', subs[0][0] + 6, weights, ncs=(1, 2))
        print('SAT base %s free %s -> cycle %d, run-in assembled %s (best %d)' % (base, fe, len(cyc),
              len(alt) if alt else None, len(cur)), flush=True)
        with open(LEVEL / 'runs' / 'opus' / ('cycles_%s.jsonl' % name), 'a') as cf:
            fcntl.flock(cf, fcntl.LOCK_EX)
            cf.write(json.dumps({'pattern': i, 'nc': m, 'K': len(cyc), 'anchor': [list(anc[0]), anc[1]],
                                 'cycle': cyc, 'assembled': len(alt) if alt else None, 'src': 'satscan2'}) + '\n')
        if alt and len(alt) < len(cur) and valid(r, pat, count, alt):
            b = load_best(name)
            b[i] = alt
            save_best(name, b)
            print('pattern %d: %d -> %d' % (i, len(cur), len(alt)), flush=True)
print('done, queries', nq)
