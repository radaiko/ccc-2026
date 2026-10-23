"""Auto loop around retbeam: per pattern, for NC copies per period, ask for a cycle that beats the current
per-copy cost (K = ceil(per*NC)-1), anchored at the current best program's submission configurations;
repeat while it improves.
Usage: python3 retauto.py <name> <width> [--only i,j] [--ncs 1,2,3] [--w WH,W1,W2,WL,WR] [--seed s]
       [--perpid n] [--free Kf --freew W] [--minper 3]"""
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from harness import LEVEL, cases, load_best, save_best, valid
from retcyc import sim, assemble, run_retbeam, run_free, runin_variants


def main():
    args = sys.argv[1:]

    def opt(name, default):
        if name in args:
            k = args.index(name)
            v = args[k + 1]
            del args[k:k + 2]
            return v
        return default
    only = opt('--only', None)
    ncs = [int(x) for x in opt('--ncs', '1,2,3').split(',')]
    seed = opt('--seed', '1')
    weights = opt('--w', '100,1,0.3,0.5,1').split(',')
    os.environ['PERPID'] = opt('--perpid', '2000')
    freeK = int(opt('--free', '0'))
    freeW = int(opt('--freew', '2000'))
    minper = float(opt('--minper', '2'))
    runinK = int(opt('--runin', '0'))
    kplus = int(opt('--kplus', '0'))
    name, width = args[0], int(args[1])
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    idxs = [int(x) for x in only.split(',')] if only else range(len(cs))

    def job(i):
        r, pat, count = cs[i]
        log = []
        for nc in ncs:
            if nc >= count:
                continue
            while True:
                prog = load_best(name)[i]
                if len(prog) < len(best[i]):
                    best[i] = prog
                prog = best[i]
                subs = sim(r, pat, prog)
                if count < 2:
                    break
                per = (len(prog) - subs[0][0]) / (count - 1)
                K = math.ceil(per * nc - 1e-9) - 1 + kplus
                if K < minper * nc:
                    break
                anchors = {}
                for j, (t, pos, am) in enumerate(subs[:count - 1]):
                    anchors.setdefault((pos, am), []).append((prog[:t], j + 1))
                if freeK:
                    starts = list(anchors.keys())
                    for pid, pos, am, path in run_free(inp, i, freeW, seed, freeK, starts, weights):
                        for pre, cp in anchors[starts[pid]][:2]:
                            if cp + 1 < count and (pos, am) not in anchors:
                                anchors.setdefault((pos, am), []).append((pre + path, cp + 1))
                keys = list(anchors.keys())
                pairs = [(p, a, p, a) for p, a in keys]
                pid, cyc = run_retbeam(inp, i, width, seed, K, nc, pairs, weights)
                if pid is None:
                    log.append('nc%d K%d:-' % (nc, K))
                    break
                bestp = None
                for pre, cp in anchors[keys[pid]]:
                    cand = assemble(r, pat, count, pre, cyc)
                    if cand and (bestp is None or len(cand) < len(bestp)):
                        bestp = cand
                if runinK:
                    alt = runin_variants(inp, i, r, pat, count, keys[pid], cyc, width, seed,
                                         subs[0][0] + runinK, weights, ncs=(1, 2))
                    if alt and (bestp is None or len(alt) < len(bestp)):
                        log.append('runin%d' % len(alt))
                        bestp = alt
                log.append('nc%d K%d:cyc%d->%s' % (nc, K, len(cyc), len(bestp) if bestp else 'x'))
                if bestp and len(bestp) < len(prog) and valid(r, pat, count, bestp):
                    print('pattern %d: %d -> %d (nc %d cycle %d)' % (i, len(prog), len(bestp), nc, len(cyc)),
                          flush=True)
                    best[i] = bestp
                    save_best(name, best)
                else:
                    break
        return i, log

    with ThreadPoolExecutor(int(os.environ.get('JOBS', '2'))) as ex:
        for i, log in ex.map(job, idxs):
            print('pattern %d best %d: %s' % (i, len(best[i]), ' '.join(log)), flush=True)


if __name__ == '__main__':
    main()
