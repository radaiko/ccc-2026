"""tuneL.py <bin> <name> <width> <idxs> <setting>... ; setting = 'ENV=V;ENV2=V2|wh,w1,w2,wl|seed'"""
import os, sys
sys.path.insert(0, '/Users/laurenzwurdinger/Documents/dev/CodingContest/ccc-2026/levels/level6/candidates/opus')
from concurrent.futures import ThreadPoolExecutor
from harness import LEVEL, HERE, run_job, cases, valid, load_best, save_best
binary, name, width = sys.argv[1], sys.argv[2], sys.argv[3]
idxs = [int(x) for x in sys.argv[4].split(',')]
inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
cs = list(cases(inp.read_text()))
best = load_best(name)
SAVE = os.environ.get('SAVE')
def job(a):
    i, st = a
    parts = st.split('|')
    envs = parts[0]; w = parts[1] if len(parts) > 1 and parts[1] else '3,1,0.3,0.5'; seed = parts[2] if len(parts) > 2 else '1'
    env = dict(os.environ)
    for kv in envs.split(';'):
        if kv: k, v = kv.split('='); env[k] = v
    out = run_job([binary, str(inp), str(i), width, seed] + w.split(','), capture_output=True, text=True, env=env).stdout
    prog = [l for l in out.split('\n') if l.strip() and l != 'NONE']
    return i, prog
with ThreadPoolExecutor(int(os.environ.get('JOBS', 3))) as ex:
    for st in sys.argv[5:]:
        res = list(ex.map(job, [(i, st) for i in idxs]))
        tot = 0; per = []
        for i, prog in res:
            n = len(prog) if prog else 999
            tot += n; per.append(n)
            if SAVE and prog and len(prog) < len(best[i]) and valid(*cs[i], prog):
                print('  improved %d: %d -> %d' % (i, len(best[i]), len(prog)), flush=True)
                best[i] = prog; save_best(name, best)
        print(st, tot, per, flush=True)
print('best', sum(len(best[i]) for i in idxs), [len(best[i]) for i in idxs])
