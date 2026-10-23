"""Palindromic-walk cycles + beam run-in (large agent 2).
Per pattern (count >= 2): q = ceil(current repeat cost per copy) - 1; SAT (l2_palsat.palwalk) for a walk with
q configs (wait variant, q lines per copy) or q+1 configs (no-wait variant, q lines per copy).  Then run-in:
beamL with TARGET = walk end config and CNTOVR=1 (first copy ending exactly there), else naive travel; append
the bounce; keep if shorter.  Repeats with q-1 while it improves.
Usage: python3 l2_palauto.py <name> [--only i,j] [--tmo ms] [--maxq 8] [--width 2000] [--w 100,1,0.3,0.5]"""
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from harness import HERE, LEVEL, cases, load_best, save_best, valid, run_job
from l2_palsat import palwalk, travel
import satcyc
from l2sim import Model as Fast

WAIT = '- - - - - -'


def bounce_from(r, pat, count, prefix, walk, at_end, nowait):
    """prefix ends with a submission at walk[-1] (at_end) or walk[0]; continue bouncing."""
    fwd = satcyc.lines_between(walk)
    back = satcyc.lines_between(walk[::-1])
    seq = [back, fwd] if at_end else [fwd, back]
    prog = list(prefix)
    fm = Fast(r, pat)
    k = 0
    while True:
        sub = fm.subs(fm.configs(prog))
        if len(sub) >= count:
            return prog[:sub[count - 1] + 1]
        if k > count + 2:
            return None
        prog += ([] if nowait else [WAIT]) + seq[k % 2]
        k += 1


def ringcfg(r, cfg):
    m = 6 * r
    pos = [(e * r + o) % m for e, (o, a) in enumerate(cfg)]
    am = sum(1 << e for e, (o, a) in enumerate(cfg) if a)
    return '%s,%d' % (','.join(map(str, pos)), am)


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
    tmo = int(opt('--tmo', '30000'))
    maxq = int(opt('--maxq', '8'))
    width = opt('--width', '2000')
    weights = opt('--w', '100,1,0.3,0.5').split(',')
    name = args[0]
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    idxs = [int(x) for x in only.split(',')] if only else list(range(len(cs)))
    idxs = [i for i in idxs if cs[i][2] >= 2]

    def job(i):
        r, pat, count = cs[i]
        log = []
        while True:
            prog = load_best(name)[i]
            if len(prog) < len(best[i]):
                best[i] = prog
            prog = best[i]
            fm = Fast(r, pat)
            sub = fm.subs(fm.configs(prog))
            f = sub[0] + 1
            per = (len(prog) - f) / (count - 1)
            q = math.ceil(per - 1e-9) - 1
            if q < 2 or q > maxq:
                log.append('q%d skip' % q)
                break
            found = None
            for nowait in (False, True):
                n = q + (1 if nowait else 0)
                w = palwalk(r, pat, n, tmo, None, nowait)
                log.append('q%d%s:%s' % (q, 'nw' if nowait else 'w', 'U' if w is None else '?' if w == 'unknown' else 'SAT'))
                if isinstance(w, list):
                    found = (w, nowait)
                    break
            if not found:
                break
            walk, nowait = found
            cands = []
            # naive travel run-in
            c = bounce_from(r, pat, count, travel(r, walk[0]) + satcyc.lines_between(walk), walk, True, nowait)
            if c:
                cands.append(c)
            limit = len(prog) - (count - 1) * q - 1
            for at_end in (True, False):
                tgt = ringcfg(r, walk[-1] if at_end else walk[0])
                env = dict(os.environ, CNTOVR='1', TARGET=tgt, WTM=os.environ.get('WTM', '1'))
                env.pop('PREFIX', None)
                if limit < 2:
                    continue
                out = run_job([str(HERE / 'beamL'), str(inp), str(i), width, '1'] + weights + [str(limit)],
                              capture_output=True, text=True, env=env).stdout.split('\n')
                pre = [l for l in out if l.strip() and l != 'NONE']
                if pre:
                    c = bounce_from(r, pat, count, pre, walk, at_end, nowait)
                    if c:
                        cands.append(c)
            cands = [c for c in cands if valid(r, pat, count, c)]
            if not cands:
                log.append('no runin')
                break
            c = min(cands, key=len)
            log.append('cand %d' % len(c))
            if len(c) < len(prog):
                log.append('%d->%d' % (len(prog), len(c)))
                best[i] = c
                save_best(name, best)
            else:
                break
        return i, log

    with ThreadPoolExecutor(int(os.environ.get('JOBS', '2'))) as ex:
        for i, log in ex.map(job, idxs):
            print('pattern %d (%d): %s' % (i, len(best[i]), ' '.join(log)), flush=True)
    save_best(name, best)


if __name__ == '__main__':
    main()
