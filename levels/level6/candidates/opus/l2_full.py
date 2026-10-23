"""Full beam runs + bounce post-processing (large agent 2).
Usage: python3 l2_full.py <name> <width> <i,j,..|@file> [--seeds 1,2] [--w 100,1,0.3,0.25] [--bin beam_l2]
env is passed to the beam (HFORBID, WTM, ...).  Every output is checked as is and after best_bounce."""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from harness import HERE, LEVEL, cases, load_best, save_best, valid, run_job
from l2_bounce import best_bounce


def main():
    args = sys.argv[1:]

    def opt(name, default):
        if name in args:
            k = args.index(name)
            v = args[k + 1]
            del args[k:k + 2]
            return v
        return default
    seeds = opt('--seeds', '1').split(',')
    weights = opt('--w', '100,1,0.3,0.25').split(',')
    binary = opt('--bin', 'beam_l2')
    name, width, sel = args[0], args[1], args[2]
    if sel.startswith('@'):
        sel = open(sel[1:]).read().strip()
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    idxs = [int(x) for x in sel.split(',')]
    best = load_best(name)
    jobs = [(i, s) for i in idxs for s in seeds]

    def job(a):
        i, s = a
        L = len(load_best(name)[i])
        env = dict(os.environ)
        env.pop('PREFIX', None)
        out = run_job([str(HERE / binary), str(inp), str(i), width, s] + weights + [str(L + 10)],
                      capture_output=True, text=True, env=env).stdout.split('\n')
        return i, s, [l for l in out if l.strip() and l != 'NONE']

    with ThreadPoolExecutor(int(os.environ.get('JOBS', '2'))) as ex:
        for i, s, prog in ex.map(job, jobs):
            r, pat, count = cs[i]
            if not prog or not valid(r, pat, count, prog):
                print('pattern %d seed %s: FAIL' % (i, s), flush=True)
                continue
            raw = len(prog)
            bb = best_bounce(r, pat, count, prog)
            if bb and len(bb) < len(prog) and valid(r, pat, count, bb):
                prog = bb
            cur = load_best(name)[i]
            tag = ''
            if len(prog) < len(cur):
                best = load_best(name)
                best[i] = prog
                save_best(name, best)
                tag = ' IMPROVED'
            print('pattern %d seed %s: raw %d bounce %d best %d%s' % (i, s, raw, len(prog), len(cur), tag),
                  flush=True)


if __name__ == '__main__':
    main()
