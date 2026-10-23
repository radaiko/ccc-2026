"""Read-only: print the merged total whenever it dropped by >= step since the last print."""
import sys, time
from harness import load_best
last = int(sys.argv[1]); step = int(sys.argv[2]) if len(sys.argv) > 2 else 200
while True:
    try:
        parts = {n: sum(map(len, load_best(n))) for n in ['1-small', '2-medium', '3-large', '4-enormous']}
        tot = sum(parts.values())
        if tot <= last - step:
            print('TOTAL %d (%s)' % (tot, ', '.join('%s %d' % (k.split('-')[1], v) for k, v in parts.items())), flush=True)
            last = tot
    except Exception as e:
        print('watch error', e, flush=True)
    time.sleep(120)
