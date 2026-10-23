"""Beam-based fixed-junction run-ins (beamL TARGET/CNTOVR): prefix with q copies ending exactly in C_s, then the
(periodically extended) continuation of the best program from submission s. Complements runin2 (exact SAT).
Usage: python3 runin3.py <name> <idx,..|@file> <width> [--seeds 1,2] [--w 100,1,0.3,0.5] [--smax 8] [--qspan 1]"""
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

from harness import HERE, LEVEL, cases, load_best, save_best, valid, run_job
import satcyc
from resuffixL import sub_ticks, opt
from runin2 import detect_cycle, configs


def main():
    args = sys.argv[1:]
    seeds = opt(args, '--seeds', '1').split(',')
    weights = opt(args, '--w', '100,1,0.3,0.5').split(',')
    smax = int(opt(args, '--smax', '8'))
    qspan = int(opt(args, '--qspan', '1'))
    name, sel, width = args[0], args[1], args[2]
    if sel.startswith('@'):
        sel = open(sel[1:]).read().strip()
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    idxs = [int(x) for x in sel.split(',')]
    tasks = []
    info = {}
    for i in idxs:
        r, pat, count = cs[i]
        B = best[i]
        L = len(B)
        st = sub_ticks(r, pat, B)
        cyc = detect_cycle(B, st)
        E = list(B)
        if cyc:
            P = cyc[2]
            while len(E) < L + (count + 2) * P:
                E.append(E[len(E) - P])
        stE = sub_ticks(r, pat, E)
        info[i] = (B, E, st)
        cf = configs(r, B, st)
        for s in range(min(len(st), smax + 1)):
            pos, act = cf[st[s]]
            am = sum(1 << e for e in range(6) if act[e])
            tgt = '%s,%d' % (','.join(map(str, pos)), am)
            for q in range(max(1, s + 1 - qspan), s + 2 + qspan):
                n = count - q
                if n < 0 or s + n >= len(stE):
                    continue
                cont = (stE[s + n] - st[s]) if n > 0 else 0
                T0max = L - 1 - cont
                if T0max < q:
                    continue
                for sd in seeds:
                    tasks.append((i, s, q, cont, T0max, tgt, sd))
    print('%d tasks' % len(tasks), flush=True)

    def job(a):
        i, s, q, cont, T0max, tgt, sd = a
        env = dict(os.environ, CNTOVR=str(q), TARGET=tgt)
        env.pop('PREFIX', None)
        out = run_job([str(HERE / 'beamL'), str(inp), str(i), width, sd] + weights + [str(T0max)],
                      capture_output=True, text=True, env=env).stdout.split('\n')
        return a, [l for l in out if l.strip() and l != 'NONE']

    saved = 0
    with ThreadPoolExecutor(int(os.environ.get('JOBS', 2))) as ex:
        for a, prog in ex.map(job, tasks):
            i, s, q, cont, T0max, tgt, sd = a
            if not prog:
                continue
            r, pat, count = cs[i]
            B, E, st = info[i]
            full = satcyc.truncate(r, pat, count, prog + E[st[s]:st[s] + cont])
            cur = load_best(name)[i]
            if full and len(full) < len(cur) and valid(r, pat, count, full):
                saved += len(cur) - len(full)
                print('pattern %d (s=%d q=%d prefix %d): %d -> %d' % (i, s, q, len(prog), len(cur), len(full)),
                      flush=True)
                b = load_best(name)
                b[i] = full
                save_best(name, b)
    print('saved', saved)


if __name__ == '__main__':
    main()
