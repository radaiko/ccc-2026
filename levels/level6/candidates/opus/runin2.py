"""Run-in optimisation with fixed junctions (large agent, medium run-ins).
For a best program B (submission ticks st, config C_s after submission s) the state after a submission is the
emitter config only, so B[st[s]:] is a valid continuation from C_s with empty matter. If B's tail is periodic,
B is extended periodically (E) so continuations can produce any number of further copies.
Search (exact SAT, satcyc.Model): a prefix of T0 lines with >= q submissions, the last on line T0, ending
exactly in C_s; new program = prefix + E[st[s]:st_E[s + count - q]]. Also a joint search (prefix with q copies +
any (K,m)-cycle, K/m = the detected cycle) via runin.joint.
Usage: python3 runin2.py <name> <idx,..|@file> [timeout_ms]   env: TMAXS (max st[s] considered, default 40),
QSPAN (q in s+1-QSPAN .. s+1+QSPAN, default 1), JQ (joint q max, default 2)."""
import os
import sys
from concurrent.futures import ThreadPoolExecutor

from harness import LEVEL, cases, load_best, save_best, valid
import satcyc
import z3sat
from resuffixL import sub_ticks
from runin import joint, any_sub_before


def detect_cycle(prog, st):
    for j in range(len(st)):
        for m in range(1, 5):
            if j + m >= len(st):
                break
            P = st[j + m] - st[j]
            t = st[j]
            tail = prog[t:]
            if all(tail[x] == tail[x - P] for x in range(P, len(tail))):
                return j, m, P
    return None


def configs(r, prog, ticks):
    m = 6 * r
    pos = [0, r, 2 * r, 3 * r, 4 * r, 5 * r]
    act = [False] * 6
    out = {}
    want = set(ticks)
    if 0 in want:
        out[0] = (list(pos), list(act))
    for t, line in enumerate(prog, 1):
        for e, ins in enumerate(line.split()):
            if ins == 'F': pos[e] = (pos[e] + 1) % m
            elif ins == 'B': pos[e] = (pos[e] - 1) % m
            elif ins == 'T': act[e] = not act[e]
        if t in want:
            out[t] = (list(pos), list(act))
    return out


def to_offsets(r, cfg):
    pos, act = cfg
    m = 6 * r
    res = []
    for e in range(6):
        o = (pos[e] - e * r) % m
        if o > m // 2:
            o -= m
        if not -r <= o <= r:
            return None
        res.append((o, act[e]))
    return res


def prefix_q(r, pat, T0, q, target, tmo):
    md = satcyc.Model(r, pat)
    start = md.fixed_start()
    pre = [md.config() for _ in range(T0)]
    prev, M, Ss = start, None, []
    for t in range(T0):
        md.trans(prev, pre[t])
        M, S = md.tick(pre[t], M)
        Ss.append(S)
        prev = pre[t]
    md.add([Ss[-1]])
    if q > 1:
        satcyc.atleast(md, Ss[:-1], q - 1)
    for e in range(6):
        pos, act = pre[-1][e]
        o, a = target[e]
        md.add([pos[md.offs.index(o)]])
        md.add([act if a else -act])
    res = z3sat.solve(md.nv, md.cl, tmo)
    if res is None or res == 'unknown':
        return res
    st = md.decode(res, start)
    return satcyc.lines_between([st] + [md.decode(res, c) for c in pre])


def work(i, r, pat, count, B, tmo):
    L = len(B)
    st = sub_ticks(r, pat, B)
    cyc = detect_cycle(B, st)
    E = list(B)
    if cyc:
        j, m, P = cyc
        while len(E) < L + (count + 2) * P:
            E.append(E[len(E) - P])
    stE = sub_ticks(r, pat, E)
    msgs = ['L %d f %d cyc %s' % (L, st[0], cyc)]
    TMAXS = int(os.environ.get('TMAXS', '40'))
    QSPAN = int(os.environ.get('QSPAN', '1'))
    cf = configs(r, B, st)
    bestp = None
    tasks = []
    for s in range(len(st)):
        if st[s] > TMAXS:
            break
        tgt = to_offsets(r, cf[st[s]])
        if tgt is None:
            continue
        for q in range(max(1, s + 1 - QSPAN), s + 2 + QSPAN):
            n = count - q  # copies still needed from C_s
            if n < 0:
                continue
            if s + n >= len(stE):
                continue
            cont = (stE[s + n] - st[s]) if n > 0 else 0
            T0max = L - 1 - cont
            if T0max < q:
                continue
            tasks.append((T0max, s, q, cont, tgt))
    for T0max, s, q, cont, tgt in tasks:
        T0 = min(T0max, (len(bestp) if bestp else L) - 1 - cont)
        while T0 >= q:
            p = prefix_q(r, pat, T0, q, tgt, tmo)
            if p is None or p == 'unknown':
                if p == 'unknown':
                    msgs.append('s=%d q=%d T0=%d unknown' % (s, q, T0))
                break
            full = satcyc.truncate(r, pat, count, p + E[st[s]:st[s] + cont])
            if full and (bestp is None or len(full) < len(bestp)) and len(full) < L:
                bestp = full
                msgs.append('s=%d q=%d T0=%d -> %d' % (s, q, T0, len(full)))
            T0 -= 1
    if cyc and os.environ.get('JOINT', '1') == '1':
        j, m, P = cyc
        for q in range(1, min(count, int(os.environ.get('JQ', '2'))) + 1):
            cur = len(bestp) if bestp else L
            # T0 + (count - q) copies at rate P/m must beat cur
            hi = cur - 1 - ((count - q) * P) // m
            for T0 in range(min(hi, TMAXS), q - 1, -1):
                p = joint(r, pat, count, P, m, T0, q, tmo)
                if p == 'unknown':
                    msgs.append('joint q=%d T0=%d unknown' % (q, T0))
                    break
                if p is None:
                    continue
                if len(p) < (len(bestp) if bestp else L):
                    bestp = p
                    msgs.append('joint q=%d T0=%d -> %d' % (q, T0, len(p)))
    return i, bestp, ' | '.join(msgs)


def main():
    name, sel = sys.argv[1], sys.argv[2]
    tmo = int(sys.argv[3]) if len(sys.argv) > 3 else 60000
    if sel.startswith('@'):
        sel = open(sel[1:]).read().strip()
    inp = LEVEL / 'data' / ('in_level-6_%s.txt' % name)
    cs = list(cases(inp.read_text()))
    best = load_best(name)
    idxs = [int(x) for x in sel.split(',')]
    saved = 0
    with ThreadPoolExecutor(int(os.environ.get('JOBS', 2))) as ex:
        futs = [ex.submit(work, i, *cs[i], best[i], tmo) for i in idxs]
        for fu in futs:
            i, p, msg = fu.result()
            print('pattern %d: %s' % (i, msg), flush=True)
            r, pat, count = cs[i]
            if p and valid(r, pat, count, p):
                cur = load_best(name)[i]
                if len(p) < len(cur):
                    saved += len(cur) - len(p)
                    print('pattern %d: %d -> %d' % (i, len(cur), len(p)), flush=True)
                    b = load_best(name)
                    b[i] = p
                    save_best(name, b)
            elif p:
                print('INVALID', i, flush=True)
    print('saved', saved)


if __name__ == '__main__':
    main()
