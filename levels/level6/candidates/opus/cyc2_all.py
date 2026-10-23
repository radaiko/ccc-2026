"""Exact static / 2-tick cycles for every pattern; assemble prefix + cycle programs and keep improvements.
Usage: python3 cyc2_all.py <input-name> [maxSolutions] [timeout] [--only i,j]"""
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

from harness import HERE, LEVEL, cases, load_best, save_best, valid


def offs(r, e, p):
    return (p - e * r + 3 * r) % (6 * r) - 3 * r


def program(r, count, configs):
    """configs: list of (pos[6], act[6]); first fires on the prefix's last tick, then cycle."""
    pos0, act0 = configs[0]
    need = [abs(offs(r, e, pos0[e])) + act0[e] for e in range(6)]
    m = max(max(need), 1)
    pre = [['-'] * 6 for _ in range(m)]
    for e in range(6):
        d = offs(r, e, pos0[e])
        start = m - need[e]
        for s in range(abs(d)):
            pre[start + s][e] = 'F' if d > 0 else 'B'
        if act0[e]:
            pre[m - 1][e] = 'T'
    cyc = []
    k = len(configs)
    for i in range(k):
        (pa, aa), (pb, ab) = configs[i], configs[(i + 1) % k]
        line = []
        for e in range(6):
            if aa[e] != ab[e]:
                line.append('T')
            elif pb[e] == (pa[e] + 1) % (6 * r):
                line.append('F')
            elif pb[e] == (pa[e] - 1) % (6 * r):
                line.append('B')
            else:
                line.append('-')
        cyc.append(line)
    prog = pre[:]
    if k == 1:
        prog += [['-'] * 6] * (count - 1)
    else:
        # after the prefix the first configuration has fired; continue with the rest of the cycle
        while True:
            for line in cyc:
                prog.append(line)
            if len(prog) > m + k * count + 2:
                break
    return [' '.join(l) for l in prog]


def main():
    args = sys.argv[1:]
    only = None
    if '--only' in args:
        i = args.index('--only')
        only = [int(x) for x in args[i + 1].split(',')]
        del args[i:i + 2]
    name = args[0]
    maxsol = args[1] if len(args) > 1 else '20'
    timeout = float(args[2]) if len(args) > 2 else 120
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    before = sum(map(len, best))
    idxs = only if only is not None else range(len(cs))

    def job(i):
        try:
            out = subprocess.run([str(HERE / 'cyc2'), str(inp), str(i), maxsol], capture_output=True, text=True,
                                 timeout=timeout).stdout
        except subprocess.TimeoutExpired as ex:
            out = ex.stdout.decode() if isinstance(ex.stdout, bytes) else (ex.stdout or '')
            if not out:
                return i, 'TIMEOUT', []
        sols = []
        lines = out.split('\n')
        j = 0
        while j < len(lines):
            if lines[j] in ('STATIC', 'CYCLE2'):
                k = 1 if lines[j] == 'STATIC' else 2
                cfgs = []
                for t in range(k):
                    if j + 1 + t >= len(lines) or not lines[j + 1 + t].strip():
                        break
                    v = list(map(int, lines[j + 1 + t].split()))[1:]
                    cfgs.append((v[0::2], v[1::2]))
                if len(cfgs) == k:
                    sols.append(cfgs)
                j += 1 + k
            else:
                j += 1
        return i, 'NONE' if 'NONE' in lines else 'OK', sols

    with ThreadPoolExecutor(int(os.environ.get('JOBS', os.cpu_count()))) as ex:
        for i, status, sols in ex.map(job, idxs):
            r, pat, count = cs[i]
            bestprog = None
            for cfgs in sols:
                prog = program(r, count, cfgs)
                # trim to the needed copies
                from levels.level6.candidates.astra import simulate
                lo = None
                for L in range(1, len(prog) + 1):
                    if simulate(r, pat, [l.split() for l in prog[:L]]) >= count:
                        lo = L
                        break
                if lo is None:
                    continue
                prog = prog[:lo]
                if bestprog is None or len(prog) < len(bestprog):
                    bestprog = prog
            kinds = {len(c) for c in sols}
            print('pattern %d: %s %s best %d -> %s' % (i, status, sorted(kinds), len(best[i]),
                                                      len(bestprog) if bestprog else '-'), flush=True)
            if bestprog and len(bestprog) < len(best[i]) and valid(r, pat, count, bestprog):
                best[i] = bestprog
                save_best(name, best)
    save_best(name, best)
    print('%s: %d -> %d' % (name, before, sum(map(len, best))))


if __name__ == '__main__':
    main()
