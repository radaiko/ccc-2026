"""Sample tester (enormous agent): run a beam binary with an env config over pattern indices, print per-pattern
lengths vs merged best, the sum, and save improvements (verified).
Usage: python3 samp_e.py <name> <idxs|topN> <width> <seed> "<ENV=.. ENV=..>" [--bin beam_e] [--w 3,1,0.3,0.5] [--nosave]"""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from harness import HERE, LEVEL, cases, load_best, save_best, valid, run_job


def main():
    args = sys.argv[1:]
    binary, weights, nosave = 'beam_e', '3,1,0.3,0.5', False
    if '--bin' in args:
        i = args.index('--bin'); binary = args[i + 1]; del args[i:i + 2]
    if '--w' in args:
        i = args.index('--w'); weights = args[i + 1]; del args[i:i + 2]
    if '--nosave' in args:
        args.remove('--nosave'); nosave = True
    name, sel, width, seed, envs = args[0], args[1], args[2], args[3], args[4] if len(args) > 4 else ''
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    if sel.startswith('top'):
        idxs = sorted(range(len(cs)), key=lambda i: -len(best[i]))[:int(sel[3:])]
    elif sel == 'all':
        idxs = list(range(len(cs)))
    else:
        idxs = [int(x) for x in sel.split(',')]
    env = dict(os.environ)
    for kv in envs.split():
        k, v = kv.split('=')
        env[k] = v

    def job(i):
        out = run_job([str(HERE / binary), str(inp), str(i), width, seed] + weights.split(','),
                      capture_output=True, text=True, env=env).stdout.split('\n')
        return i, [l for l in out if l.strip() and l != 'NONE']

    tb = tn = 0
    with ThreadPoolExecutor(int(os.environ.get('JOBS', 3))) as ex:
        for i, prog in ex.map(job, idxs):
            r, pat, count = cs[i]
            ok = bool(prog) and valid(r, pat, count, prog)
            n = len(prog) if ok else 999
            old = len(best[i])
            tb += old
            tn += min(n, len(best[i]))
            mark = ''
            if ok and n < len(best[i]):
                mark = ' IMPROVED'
                if not nosave:
                    best[i] = prog
                    save_best(name, best)
            print('%d: best %d got %s%s' % (i, old, n if ok else 'FAIL', mark), flush=True)
    print('SUM best %d  min(best,new) %d' % (tb, tn), flush=True)


if __name__ == '__main__':
    main()
