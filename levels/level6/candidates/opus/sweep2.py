"""First copy by a DP-planned row sweep (sweepdp), forced into the beam search, which then cleans up the
unpunched halo cells and builds the remaining copies freely.
Usage: python3 sweep2.py <input-name> <width> [--only i,j] [--copies k]"""
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from harness import HERE, LEVEL, cases, load_best, save_best, valid


def main():
    args = sys.argv[1:]
    only = None
    copies = '1'
    if '--only' in args:
        i = args.index('--only')
        only = [int(x) for x in args[i + 1].split(',')]
        del args[i:i + 2]
    if '--copies' in args:
        i = args.index('--copies')
        copies = args[i + 1]
        del args[i:i + 2]
    name, width = args[0], args[1]
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    before = sum(map(len, best))
    tmp = tempfile.mkdtemp()
    jobs = [(i, a, rv) for i in (only if only is not None else range(len(cs))) for a in range(3) for rv in range(2)]

    def job(arg):
        i, a, rv = arg
        out = subprocess.run([str(HERE / 'sweepdp'), str(inp), str(i), str(a), str(rv), '3', copies],
                             capture_output=True, text=True).stdout.split('\n')
        sched = [l.replace(' ', '') for l in out[1:] if l.strip()]
        path = os.path.join(tmp, '%d_%d_%d.txt' % (i, a, rv))
        with open(path, 'w') as f:
            f.write('\n'.join(sched) + '\n')
        res = subprocess.run([str(HERE / 'beam'), str(inp), str(i), width, '1', '3', '1', '0.3', '0.5', '600', path],
                             capture_output=True, text=True).stdout.split('\n')
        return i, out[0], [l for l in res if l.strip() and l != 'NONE']

    with ThreadPoolExecutor(int(os.environ.get('JOBS', os.cpu_count()))) as ex:
        for i, head, prog in ex.map(job, jobs):
            r, pat, count = cs[i]
            print('pattern %d: %s -> %d (best %d)' % (i, head, len(prog), len(best[i])), flush=True)
            if prog and len(prog) < len(best[i]) and valid(r, pat, count, prog):
                print('  improved %d -> %d' % (len(best[i]), len(prog)), flush=True)
                best[i] = prog
                save_best(name, best)
    save_best(name, best)
    print('%s: %d -> %d' % (name, before, sum(map(len, best))))


if __name__ == '__main__':
    main()
