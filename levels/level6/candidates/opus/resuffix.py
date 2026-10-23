"""Suffix re-optimisation: replay the first t lines of the current best program, rerun a wide beam from that
exact state, and keep the spliced program if it is shorter.
Usage: python3 resuffix.py <input-name> <width> <cuts> [--only i,j]
cuts: comma list of 'dN' (cut N lines before the end) or 'fX' (cut at fraction X of the program)."""
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from harness import HERE, LEVEL, cases, load_best, save_best, valid, run_job


def main():
    args = sys.argv[1:]
    only = None
    if '--only' in args:
        i = args.index('--only')
        only = [int(x) for x in args[i + 1].split(',')]
        del args[i:i + 2]
    name, width, cuts = args[0], args[1], args[2].split(',')
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    before = sum(map(len, best))
    tmp = tempfile.mkdtemp()
    jobs = []
    for i in (only if only is not None else range(len(cs))):
        L = len(best[i])
        ts = set()
        for c in cuts:
            t = L - int(c[1:]) if c[0] == 'd' else int(L * float(c[1:]))
            if 0 < t < L - 1:
                ts.add(t)
        for t in sorted(ts):
            path = os.path.join(tmp, '%d_%d.txt' % (i, t))
            with open(path, 'w') as f:
                f.write('\n'.join(best[i][:t]) + '\n')
            jobs.append((i, t, path, L))

    def job(arg):
        i, t, path, L = arg
        env = dict(os.environ, PREFIX=path)
        out = run_job([str(HERE / 'beam_p'), str(inp), str(i), width, '1', '3', '1', '0.3', '0.5', str(L - t)],
                             capture_output=True, text=True, env=env).stdout.split('\n')
        return i, t, [l for l in out if l.strip() and l != 'NONE']

    with ThreadPoolExecutor(int(os.environ.get('JOBS', os.cpu_count()))) as ex:
        for i, t, prog in ex.map(job, jobs):
            r, pat, count = cs[i]
            if prog and len(prog) < len(best[i]) and valid(r, pat, count, prog):
                print('pattern %d (cut %d): %d -> %d' % (i, t, len(best[i]), len(prog)), flush=True)
                best[i] = prog
                save_best(name, best)
    save_best(name, best)
    print('%s: %d -> %d' % (name, before, sum(map(len, best))))


if __name__ == '__main__':
    main()
