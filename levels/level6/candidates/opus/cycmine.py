"""Cycle mining: beam proposes many (K, m) cycles through many different anchors (retbeam ALL mode over an anchor
pool = submission configs of the best program + one-copy beam continuations of them), then fixed-anchor SAT
tries to shorten each proposal (K-1, K-2, ...) through the same anchor. Splice prefix-to-anchor + cycle
(+ beam run-ins into the cycle phases); save improvements; record cycles that beat the current rate.
Usage: python3 cycmine.py <name> <idx,..> [--ms 2,3] [--width 20000] [--all 200] [--perpid 50] [--kplus 0]
       [--sat 30] [--tmo 30000] [--freeK +3] [--freew 3000] [--w ...]"""
import json
import fcntl
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from harness import HERE, LEVEL, cases, load_best, save_best, valid, run_job
from retcyc import sim, assemble, run_free, runin_variants
from satanchor import anchored
import tempfile


def run_all(inp, i, width, seed, K, nc, pairs, weights, nall, perpid):
    with tempfile.NamedTemporaryFile('w', suffix='.pairs', delete=False) as f:
        for sp, sa, tp, ta in pairs:
            f.write(' '.join(map(str, list(sp) + [sa] + list(tp) + [ta])) + '\n')
        fn = f.name
    out = run_job([str(HERE / 'retbeam'), str(inp), str(i), str(width), str(seed), str(K), str(nc), fn] + weights,
                  capture_output=True, text=True,
                  env=dict(os.environ, ALL=str(nall), PERPID=str(perpid))).stdout.split('\n')
    os.unlink(fn)
    res = []
    j = 0
    while j < len(out):
        if out[j].startswith('CYCLE'):
            pid, d = map(int, out[j].split()[1:3])
            res.append((pid, out[j + 1:j + 1 + d]))
            j += 1 + d
        else:
            j += 1
    return res


def record(name, rec):
    with open(LEVEL / 'runs' / 'opus' / ('cycles_%s.jsonl' % name), 'a') as cf:
        fcntl.flock(cf, fcntl.LOCK_EX)
        cf.write(json.dumps(rec) + '\n')


def main():
    args = sys.argv[1:]

    def opt(name, default):
        if name in args:
            k = args.index(name)
            v = args[k + 1]
            del args[k:k + 2]
            return v
        return default
    ms = [int(x) for x in opt('--ms', '2,3').split(',')]
    width = int(opt('--width', '20000'))
    nall = int(opt('--all', '200'))
    perpid = int(opt('--perpid', '50'))
    kplus = int(opt('--kplus', '0'))
    nsat = int(opt('--sat', '30'))
    tmo = int(opt('--tmo', '30000'))
    freeK = int(opt('--freeK', '3'))
    freeW = int(opt('--freew', '3000'))
    seed = opt('--seed', '1')
    weights = opt('--w', '100,1,0.3,0.5,1').split(',')
    name, sel = args[0], args[1]
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    idxs = [int(x) for x in sel.split(',')]

    def job(i):
        r, pat, count = cs[i]
        log = []
        prog = load_best(name)[i]
        subs = sim(r, pat, prog)
        rate = (len(prog) - subs[0][0]) / (count - 1)
        anchors = {}
        for j, (t, pos, am) in enumerate(subs[:count - 1]):
            anchors.setdefault((pos, am), []).append((prog[:t], j + 1))
        if freeK:
            starts = list(anchors.keys())
            for pid, pos, am, path in run_free(inp, i, freeW, seed, math.ceil(rate) + freeK, starts, weights):
                if (pos, am) in anchors:
                    continue
                src = min(anchors[starts[pid]], key=lambda x: len(x[0]) - rate * x[1])
                if src[1] + 1 < count:
                    anchors[(pos, am)] = [(src[0] + path, src[1] + 1)]
        keys = list(anchors.keys())
        pairs = [(p, a, p, a) for p, a in keys]
        props = []
        for m in ms:
            if m >= count:
                continue
            K = math.ceil(rate * m - 1e-9) + kplus
            for pid, cyc in run_all(inp, i, width, seed, K, m, pairs, weights, nall, perpid):
                props.append((len(cyc) / m, m, pid, cyc))
        props.sort(key=lambda x: x[0])
        log.append('anchors %d proposals %d (best rate %s)' % (len(keys), len(props),
                                                             '%.2f' % props[0][0] if props else '-'))
        cur = load_best(name)[i]
        satcalls = 0

        def consider(cyc, m, key, tag):
            nonlocal cur
            cands = [assemble(r, pat, count, pre, cyc) for pre, cp in anchors[key]]
            if len(cyc) / m < rate - 1e-9:
                alt = runin_variants(inp, i, r, pat, count, key, cyc, width, seed, subs[0][0] + 6, weights,
                                     ncs=(1, 2))
                cands.append(alt)
            cands = [c for c in cands if c]
            bp = min(cands, key=len) if cands else None
            if len(cyc) / m < rate - 1e-9:
                record(name, {'pattern': i, 'nc': m, 'K': len(cyc), 'anchor': [list(key[0]), key[1]],
                              'cycle': cyc, 'assembled': len(bp) if bp else None, 'src': tag})
            if bp and len(bp) < len(cur) and valid(r, pat, count, bp):
                print('pattern %d: %d -> %d (%s m %d K %d)' % (i, len(cur), len(bp), tag, m, len(cyc)), flush=True)
                b = load_best(name)
                b[i] = bp
                save_best(name, b)
                cur = bp
            return bp

        for rt, m, pid, cyc in props:
            key = keys[pid]
            if rt < rate - 1e-9:
                consider(cyc, m, key, 'beam')
            K = len(cyc) - 1
            while satcalls < nsat and K >= 2 * m:
                satcalls += 1
                res = anchored(r, pat, K, m, key, tmo)
                if not isinstance(res, list):
                    log.append('m%d K%d:%s' % (m, K, 'U' if res is None else res[:1]))
                    break
                log.append('m%d K%d:SAT' % (m, K))
                consider(res, m, key, 'sat')
                K -= 1
            if satcalls >= nsat:
                break
        return i, log

    with ThreadPoolExecutor(int(os.environ.get('JOBS', '2'))) as ex:
        for i, log in ex.map(job, idxs):
            print('pattern %d best %d: %s' % (i, len(load_best(name)[i]), ' '.join(log)), flush=True)


if __name__ == '__main__':
    main()
