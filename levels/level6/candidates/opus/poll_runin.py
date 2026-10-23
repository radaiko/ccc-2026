"""Poll the merged best of given patterns and re-run runin2 on patterns whose program changed.
Usage: python3 poll_runin.py <name> <idx,..|@file> <period_s> <rounds> [timeout_ms]"""
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from harness import load_best

name, sel, period, rounds = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
tmo = sys.argv[5] if len(sys.argv) > 5 else '30000'
if sel.startswith('@'):
    sel = open(sel[1:]).read().strip()
idxs = [int(x) for x in sel.split(',')]
state = Path(os.environ.get('POLLSTATE', '/tmp/poll_runin_%s.json' % name))
last = json.loads(state.read_text()) if state.exists() else {}
here = Path(__file__).resolve().parent
for rnd in range(rounds):
    b = load_best(name)
    h = {str(i): hashlib.md5('\n'.join(b[i]).encode()).hexdigest() for i in idxs}
    changed = [i for i in idxs if last.get(str(i)) != h[str(i)]]
    print(time.strftime('%H:%M:%S'), 'round', rnd, 'changed', changed, flush=True)
    if changed:
        subprocess.run(['python3', str(here / 'runin2.py'), name, ','.join(map(str, changed)), tmo])
        for i in changed:
            last[str(i)] = h[str(i)]
        state.write_text(json.dumps(last))
    time.sleep(period)
