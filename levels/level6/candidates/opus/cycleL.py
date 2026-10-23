"""Closed-cycle repeats (large agent): after submission k the state is the emitter config C_k only. Beam a copy
segment from C_k that submits exactly when the config is back at C_k (beamL TARGET), length K; program =
prefix(t_k) + segment*(count-k). Usage: python3 cycleL.py <name> <width> [--only i,j] [--w 100,1,0.3,0.5] [--seed S]
[--slack N] (try K up to (R_k-1)//(count-k) only, i.e. strictly better)."""
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from harness import HERE, LEVEL, cases, load_best, save_best, valid, run_job
from resuffixL import sub_ticks, opt


def config(r, prog):
    m = 6 * r; pos = [0, r, 2 * r, 3 * r, 4 * r, 5 * r]; act = 0
    for line in prog:
        for e, ins in enumerate(line.split()):
            if ins == 'F': pos[e] = (pos[e] + 1) % m
            elif ins == 'B': pos[e] = (pos[e] - 1) % m
            elif ins == 'T': act ^= 1 << e
    return pos, act


def main():
    args = sys.argv[1:]
    only = opt(args, '--only', None)
    only = [int(x) for x in only.split(',')] if only else None
    weights = opt(args, '--w', '100,1,0.3,0.5').split(',')
    seed = opt(args, '--seed', '1')
    binary = opt(args, '--bin', 'beamL')
    name, width = args[0], args[1]
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    before = sum(map(len, best))
    tmp = tempfile.mkdtemp()
    jobs = []
    for i in (only if only is not None else range(len(cs))):
        r, pat, count = cs[i]
        if count < 2: continue
        L = len(best[i])
        st = sub_ticks(r, pat, best[i])
        for k in range(1, count):
            t = st[k - 1]
            R = L - t
            K = (R - 1) // (count - k)
            if K < 1: continue
            pos, act = config(r, best[i][:t])
            path = os.path.join(tmp, '%d_%d.txt' % (i, t))
            with open(path, 'w') as f:
                f.write('\n'.join(best[i][:t]) + '\n')
            jobs.append((i, k, t, K, path, '%s,%d' % (','.join(map(str, pos)), act)))
    jobs.sort(key=lambda j: -j[3])
    print('%d jobs' % len(jobs), flush=True)

    def job(a):
        i, k, t, K, path, tgt = a
        env = dict(os.environ, PREFIX=path, CNTOVR=str(k + 1), TARGET=tgt)
        out = run_job([str(HERE / binary), str(inp), str(i), width, seed] + weights + [str(K)],
                      capture_output=True, text=True, env=env).stdout.split('\n')
        prog = [l for l in out if l.strip() and l != 'NONE']
        return i, k, t, prog

    with ThreadPoolExecutor(int(os.environ.get('JOBS', 3))) as ex:
        for i, k, t, prog in ex.map(job, jobs):
            if not prog: continue
            r, pat, count = cs[i]
            seg = prog[t:]
            full = best[i][:t] + seg * (count - k)
            if len(full) < len(best[i]) and valid(r, pat, count, full):
                print('pattern %d (k=%d, cycle %d): %d -> %d' % (i, k, len(seg), len(best[i]), len(full)), flush=True)
                best[i] = full
                save_best(name, best)
            elif len(full) < len(best[i]):
                print('INVALID cycle', i, k, flush=True)
    save_best(name, best)
    print('%s: %d -> %d' % (name, before, sum(map(len, best))))


if __name__ == '__main__':
    main()
