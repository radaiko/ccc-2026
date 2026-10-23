"""Polish every current best program with the C++ polisher; keep verified improvements.
Usage: python3 polish_all.py <input-name> [seed] [window]"""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from harness import HERE, LEVEL, cases, load_best, save_best, valid

name = sys.argv[1]
seed = sys.argv[2] if len(sys.argv) > 2 else '1'
window = sys.argv[3] if len(sys.argv) > 3 else '3'
inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
cs = list(cases(inp.read_text()))
best = load_best(name)
before = sum(map(len, best))


def job(i):
    out = subprocess.run([str(HERE / 'polish'), str(inp), str(i), seed, window], input='\n'.join(best[i]) + '\n',
                         capture_output=True, text=True).stdout
    return i, [l for l in out.split('\n') if l.strip()]


with ThreadPoolExecutor(int(os.environ.get('JOBS', os.cpu_count()))) as ex:
    for i, prog in ex.map(job, range(len(cs))):
        r, pat, count = cs[i]
        if prog and prog != ['INVALID'] and len(prog) < len(best[i]) and valid(r, pat, count, prog):
            print('pattern %d: %d -> %d' % (i, len(best[i]), len(prog)), flush=True)
            best[i] = prog
save_best(name, best)
print('%s: %d -> %d' % (name, before, sum(map(len, best))))
