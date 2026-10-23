"""Run satcyc.py auto over medium patterns (parallel JOBS, hard timeout per pattern), keep improvements.
Usage: satdrive.py <input-name> <idx,idx,...|all> [z3 timeout ms]"""
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from harness import HERE, LEVEL, cases, load_best, save_best, valid, run_job

name, sel = sys.argv[1], sys.argv[2]
tmo = sys.argv[3] if len(sys.argv) > 3 else '30000'
ctmo = sys.argv[4] if len(sys.argv) > 4 else '8000'
inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
cs = list(cases(inp.read_text()))
best = load_best(name)
idxs = range(len(cs)) if sel == 'all' else [int(x) for x in sel.split(',')]
tmpd = tempfile.mkdtemp(prefix='satdrive_')


def job(i):
    f = os.path.join(tmpd, 'b%d.txt' % i)
    open(f, 'w').write('\n'.join(best[i]) + '\n')
    p = run_job(['python3', str(HERE / 'satcyc.py'), str(inp), str(i), 'auto', f, tmo, ctmo],
                capture_output=True, text=True)
    logd = os.environ.get('SATLOG')
    if logd:
        os.makedirs(logd, exist_ok=True)
        open(os.path.join(logd, '%d.err' % i), 'a').write(p.stderr or '')
    return i, [l for l in p.stdout.split('\n') if l.strip()], p.stderr


saved = 0
with ThreadPoolExecutor(int(os.environ.get('JOBS', '2'))) as ex:
    for i, prog, err in ex.map(job, idxs):
        r, pat, count = cs[i]
        tail = [l for l in err.splitlines() if l.startswith(('B ', 'cycle', 'RESULT')) and 'unknown' not in l]
        print('pattern %d: %s' % (i, ' | '.join(tail)), flush=True)
        if prog and valid(r, pat, count, prog):
            cur = load_best(name)[i]
            if len(prog) < len(cur):
                saved += len(cur) - len(prog)
                print('pattern %d: %d -> %d' % (i, len(cur), len(prog)), flush=True)
                b = load_best(name)
                b[i] = prog
                save_best(name, b)
        elif prog:
            print('INVALID', i, flush=True)
print('saved', saved)
