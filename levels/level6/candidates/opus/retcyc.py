"""Return-constrained cycles: for each pattern take the configurations at the submission ticks of the current
best program as cycle anchors c0, search (retbeam) a K-tick path from (c0, empty matter) that submits NC copies,
the last exactly at c0, then assemble best-prefix-up-to-that-submission + repeated cycle.
Usage: python3 retcyc.py <name> <width> <K list e.g. 4,5,6> [--nc 1] [--seed 1] [--only i,j] [--w WH,W1,W2,WL,WR]
       [--nb] (also neighbour anchors reached via a fresh run-in, see runin)"""
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from harness import HERE, LEVEL, cases, load_best, save_best, valid, run_job
from levels.level6.candidates.astra import board, ring, DIRS, NB


def sim(r, pat, prog, start=None):
    """Return list of (tick, pos tuple, actmask) at each submission (tick = number of lines executed).
    start = (pos tuple, actmask) to begin at that configuration with empty matter (default: initial state)."""
    g = board(r)
    h, w = 2 * r + 1, 4 * r + 1
    rg = ring(r)
    m = len(rg)
    pc = [(y, x) for y in range(h) for x in range(w) if pat[y][x] == 'M']
    ps = set(pc)
    halo = {(y + dy, x + dx) for y, x in pc for dy, dx in NB
            if (y + dy, x + dx) not in ps and 0 <= y + dy < h and 0 <= x + dx < w and g[y + dy][x + dx] in 'OM'}
    pos = [0, r, 2 * r, 3 * r, 4 * r, 5 * r]
    act = [False] * 6
    if start is not None:
        pos = list(start[0])
        act = [bool(start[1] >> e & 1) for e in range(6)]
    subs = []
    for t, line in enumerate(prog):
        if isinstance(line, str):
            line = line.split()
        for e, ins in enumerate(line):
            if ins == 'F':
                pos[e] = (pos[e] + 1) % m
            elif ins == 'B':
                pos[e] = (pos[e] - 1) % m
            elif ins == 'T':
                act[e] = not act[e]
        cnt = {}
        for e in range(6):
            if not act[e]:
                continue
            dy, dx = DIRS[e]
            y, x = rg[pos[e]]
            y += dy
            x += dx
            while 0 <= y < h and 0 <= x < w and g[y][x] in 'OM':
                cnt[(y, x)] = cnt.get((y, x), 0) + 1
                y += dy
                x += dx
        for (y, x), k in cnt.items():
            if k == 2:
                g[y][x] = 'M'
            elif k >= 3:
                g[y][x] = 'O'
        if all(g[y][x] == 'M' for y, x in pc) and not any(g[y][x] == 'M' for y, x in halo):
            for y, x in pc:
                g[y][x] = 'O'
            subs.append((t + 1, tuple(pos), sum(1 << e for e in range(6) if act[e])))
    return subs


def assemble(r, pat, count, prefix, cycle):
    """prefix ends with a submission at the cycle's anchor; repeat cycle and trim to count submissions."""
    prog = list(prefix)
    while True:
        s = sim(r, pat, prog)
        if len(s) >= count:
            return prog[:s[count - 1][0]]
        before = len(s)
        prog += cycle
        if len(sim(r, pat, prog)) == before:
            return None


def run_free(inp, i, width, seed, K, starts, weights):
    """One-copy beam from each start config (no return constraint); returns list of (pid, pos, am, path)."""
    with tempfile.NamedTemporaryFile('w', suffix='.pairs', delete=False) as f:
        for sp, sa in starts:
            f.write(' '.join(map(str, list(sp) + [sa] + list(sp) + [sa])) + '\n')
        fn = f.name
    out = run_job([str(HERE / 'retbeam'), str(inp), str(i), str(width), str(seed), str(K), '1', fn] + weights,
                  capture_output=True, text=True, env=dict(os.environ, FREE='1')).stdout.split('\n')
    os.unlink(fn)
    res = []
    j = 0
    while j < len(out):
        if out[j].startswith('ANCHOR'):
            v = list(map(int, out[j].split()[1:]))
            pid, d = v[0], v[1]
            res.append((pid, tuple(v[2:8]), v[8], out[j + 1:j + 1 + d]))
            j += 1 + d
        else:
            j += 1
    return res


def run_retbeam(inp, i, width, seed, K, nc, pairs, weights):
    with tempfile.NamedTemporaryFile('w', suffix='.pairs', delete=False, dir=None) as f:
        for sp, sa, tp, ta in pairs:
            f.write(' '.join(map(str, list(sp) + [sa] + list(tp) + [ta])) + '\n')
        fn = f.name
    out = run_job([str(HERE / 'retbeam'), str(inp), str(i), str(width), str(seed), str(K), str(nc), fn] + weights,
                  capture_output=True, text=True).stdout.split('\n')
    os.unlink(fn)
    if not out or not out[0].startswith('FOUND'):
        return None, None
    pid = int(out[0].split()[1])
    return pid, [l for l in out[1:] if l.strip()]


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
    nc = int(opt('--nc', '1'))
    seed = opt('--seed', '1')
    weights = opt('--w', '3,1,0.3,0.5,1').split(',')
    name, width, Ks = args[0], int(args[1]), [int(x) for x in args[2].split(',')]
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    idxs = [int(x) for x in only.split(',')] if only else range(len(cs))

    freeK = int(opt('--free', '0'))
    freeW = int(opt('--freew', '2000'))
    gens = int(opt('--gen', '1'))
    perpid = opt('--perpid', '0')
    os.environ['PERPID'] = perpid

    def job(i):
        r, pat, count = cs[i]
        prog = best[i]
        subs = sim(r, pat, prog)
        # anchor config -> list of (prefix lines, copies done)
        anchors = {}
        for j, (t, pos, am) in enumerate(subs[:count - 1]):
            anchors.setdefault((pos, am), []).append((prog[:t], j + 1))
        frontier = list(anchors.keys())
        per = (len(prog) - subs[0][0]) / max(1, count - 1)
        for g in range(gens if freeK else 0):
            starts = frontier
            found = run_free(inp, i, freeW, seed, freeK, starts, weights)
            frontier = []
            for pid, pos, am, path in found:
                src = anchors[starts[pid]]
                key = (pos, am)
                new = key not in anchors
                for pre, cp in src:
                    if cp + 1 < count:
                        anchors.setdefault(key, []).append((pre + path, cp + 1))
                if new and key in anchors:
                    frontier.append(key)
            # keep the best few prefixes per anchor (value = length - per * copies)
            for k in anchors:
                anchors[k] = sorted(anchors[k], key=lambda x: len(x[0]) - per * x[1])[:3]
        keys = list(anchors.keys())
        pairs = [(p, a, p, a) for p, a in keys]
        res = []
        for K in Ks:
            pid, cyc = run_retbeam(inp, i, width, seed, K, nc, pairs, weights)
            if pid is None:
                res.append((K, None))
                continue
            bestp = None
            for pre, cp in anchors[keys[pid]]:
                cand = assemble(r, pat, count, pre, cyc)
                if cand and (bestp is None or len(cand) < len(bestp)):
                    bestp = cand
            res.append((K, (len(cyc), bestp)))
        return i, res, len(keys)

    with ThreadPoolExecutor(int(os.environ.get('JOBS', '2'))) as ex:
        for i, res, na in ex.map(job, idxs):
            r, pat, count = cs[i]
            msg = []
            for K, v in res:
                if v is None:
                    msg.append('K%d:-' % K)
                    continue
                L, p = v
                msg.append('K%d:cyc%d->%s' % (K, L, len(p) if p else 'x'))
                if p and len(p) < len(best[i]) and valid(r, pat, count, p):
                    print('pattern %d: %d -> %d (cycle %d)' % (i, len(best[i]), len(p), L), flush=True)
                    best[i] = p
                    save_best(name, best)
            print('pattern %d best %d anchors %d: %s' % (i, len(best[i]), na, ' '.join(msg)), flush=True)


if __name__ == '__main__':
    main()


def runin_variants(inp, i, r, pat, count, anchor, cyc, width, seed, K, weights, ncs=(1,)):
    """Run-ins from the initial state that submit nc copies exactly at a phase configuration of the cycle,
    followed by the rotated cycle. Returns the shortest assembled program (or None)."""
    phases = sim(r, pat, cyc, start=anchor)
    init = (tuple(e * r for e in range(6)), 0)
    targets = []
    for tau, pos, am in phases:
        if (pos, am) not in [t[1] for t in targets]:
            targets.append((tau, (pos, am)))
    best = None
    for nc in ncs:
        if nc >= count:
            continue
        pairs = [(init[0], init[1], c[0], c[1]) for _, c in targets]
        pid, path = run_retbeam(inp, i, width, seed, K, nc, pairs, weights)
        if pid is None:
            continue
        tau = targets[pid][0]
        rot = cyc[tau:] + cyc[:tau]
        cand = assemble(r, pat, count, path, rot)
        if cand and (best is None or len(cand) < len(best)):
            best = cand
    return best
