"""Build programs from saved SAT cycles (scratchpad/cycles/cyc_<i>_<K>_<m>.json): SAT prefix + rotated cycle;
save when shorter. Usage: satbuild.py <file.json> ... [env SATPTMO ms]"""
import json, os, re, sys
from harness import LEVEL, cases, load_best, save_best, valid
from satcyc import build_from_cycle

NAME = '2-medium'
cs = list(cases((LEVEL / 'data' / ('in_level-6_%s.txt' % NAME)).read_text()))
ptmo = int(os.environ.get('SATPTMO', '30000'))
for f in sys.argv[1:]:
    i = int(re.search(r'cyc_(\d+)_', f).group(1))
    d = json.load(open(f))
    cfg = [[tuple(x) for x in c] for c in d['cfg']]
    r, pat, count = cs[i]
    B = len(load_best(NAME)[i])
    prog = build_from_cycle(r, pat, count, cfg, d['subs'], B, ptmo)
    msg = 'no program < %d' % B
    if prog and valid(r, pat, count, prog):
        b = load_best(NAME)
        if len(prog) < len(b[i]):
            msg = 'IMPROVED %d -> %d' % (len(b[i]), len(prog))
            b[i] = prog
            save_best(NAME, b)
        else:
            msg = 'built %d (best %d)' % (len(prog), len(b[i]))
    print('%s: %s' % (os.path.basename(f), msg), flush=True)
