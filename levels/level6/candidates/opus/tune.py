"""Compare beam weight settings on a fixed pattern sample (sum of program lengths)."""
import subprocess, sys, os
from concurrent.futures import ThreadPoolExecutor
from harness import LEVEL, HERE
name = sys.argv[1]; width = sys.argv[2]; idxs = [int(x) for x in sys.argv[3].split(',')]
settings = [s.split(',') for s in sys.argv[4:]]
inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
def job(a):
    i, s = a
    out = subprocess.run([str(HERE / 'beam'), str(inp), str(i), width, '1'] + s, capture_output=True, text=True).stdout
    return len([l for l in out.split('\n') if l.strip()])
with ThreadPoolExecutor(int(os.environ.get('JOBS', os.cpu_count()))) as ex:
    for s in settings:
        print(s, sum(ex.map(job, [(i, s) for i in idxs])), flush=True)
