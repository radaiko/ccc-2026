"""Fixed-anchor SAT cycles over patterns: anchors = distinct submission configurations of the current best
program; for m copies per period try K = ceil(rate*m)-1 downwards (SAT anchored at that exact config, cheap
compared with free-anchor SAT); splice old prefix + cycle, also beam run-ins into the cycle phases.
Usage: python3 satauto.py <name> <idx,idx,..> [--ms 2,3,1] [--tmo 60000] [--maxa 4] [--runin 6]"""
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from harness import LEVEL, cases, load_best, save_best, valid
from retcyc import sim, assemble, runin_variants
from satanchor import anchored


def main():
    args = sys.argv[1:]

    def opt(name, default):
        if name in args:
            k = args.index(name)
            v = args[k + 1]
            del args[k:k + 2]
            return v
        return default
    ms = [int(x) for x in opt('--ms', '2,3,1').split(',')]
    tmo = int(opt('--tmo', '60000'))
    maxa = int(opt('--maxa', '4'))
    runinK = int(opt('--runin', '6'))
    name, sel = args[0], args[1]
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    idxs = [int(x) for x in sel.split(',')]
    weights = '100,1,0.3,0.5,1'.split(',')
    os.environ.setdefault('PERPID', '2000')

    def job(i):
        r, pat, count = cs[i]
        log = []
        for m in ms:
            if m >= count:
                continue
            while True:
                prog = load_best(name)[i]
                subs = sim(r, pat, prog)
                rate = (len(prog) - subs[0][0]) / (count - 1)
                K = math.ceil(rate * m - 1e-9) - 1
                if K < 2 * m:
                    break
                anchors = []
                for j, (t, pos, am) in enumerate(subs[:count - 1]):
                    if (pos, am) not in [a[0] for a in anchors]:
                        anchors.append(((pos, am), t))
                # prefer anchors late in the program (inside the steady cycle)
                anchors = sorted(anchors, key=lambda a: -a[1])[:maxa]
                improved = False
                anyunk = False
                for anchor, t in anchors:
                    res = anchored(r, pat, K, m, anchor, tmo)
                    if res is None or res == 'skip':
                        log.append('m%d K%d t%d:%s' % (m, K, t, 'U' if res is None else 'skip'))
                        continue
                    if res == 'unknown':
                        anyunk = True
                        log.append('m%d K%d t%d:?' % (m, K, t))
                        continue
                    cyc = res
                    cands = [assemble(r, pat, count, prog[:tt], cyc)
                             for jj, (tt, p2, a2) in enumerate(subs[:count - 1]) if (p2, a2) == anchor]
                    alt = runin_variants(inp, i, r, pat, count, anchor, cyc, 20000, '1', subs[0][0] + runinK,
                                         weights, ncs=(1, 2))
                    cands = [c for c in cands + [alt] if c]
                    bestp = min(cands, key=len) if cands else None
                    log.append('m%d K%d t%d:SAT->%s' % (m, K, t, len(bestp) if bestp else 'x'))
                    if len(cyc) / m < rate - 1e-9:
                        import json, fcntl
                        with open(LEVEL / 'runs' / 'opus' / ('cycles_%s.jsonl' % name), 'a') as cf:
                            fcntl.flock(cf, fcntl.LOCK_EX)
                            cf.write(json.dumps({'pattern': i, 'nc': m, 'K': len(cyc), 'anchor': [list(anchor[0]),
                                     anchor[1]], 'cycle': cyc, 'assembled': len(bestp) if bestp else None,
                                     'src': 'satanchor'}) + '\n')
                    if bestp and len(bestp) < len(prog) and valid(r, pat, count, bestp):
                        print('pattern %d: %d -> %d (sat anchored m %d K %d)' % (i, len(prog), len(bestp), m, K),
                              flush=True)
                        b = load_best(name)
                        b[i] = bestp
                        save_best(name, b)
                        improved = True
                        break
                if not improved:
                    break
        return i, log

    with ThreadPoolExecutor(int(os.environ.get('JOBS', '2'))) as ex:
        for i, log in ex.map(job, idxs):
            print('pattern %d best %d: %s' % (i, len(load_best(name)[i]), ' '.join(log)), flush=True)


if __name__ == '__main__':
    main()
