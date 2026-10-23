# Level 6 optimisation brief (opus team)

Repo: /Users/laurenzwurdinger/Documents/dev/CodingContest/ccc-2026 (shared checkout: NEVER git checkout/stash/reset/
commit there). Code: levels/level6/candidates/opus/. Inputs: levels/level6/data/in_level-6_{1-small,2-medium,3-large,
4-enormous}.txt. Rules: RULES.md (repo root) + levels/level6/findings_opus.md + levels/level6/findigs_astra.md +
levels/level6/NOTES.md. Score = total lines; programs need NOT switch emitters off at the end (team convention).

## Best-program store
- `harness.py` load_best(name) merges runs/*/out_*, output/ and runs/opus/best_<name>.json (per pattern min);
  save_best merges with disk under a lock -> safe for concurrent writers. valid() = astra simulate >= count.
- `python3 total.py` re-merges, re-verifies, rewrites levels/level6/output/ when better, prints totals.
- `./commit_progress.sh "msg"` copies opus code, findings files and output/ to branch level6-findings-astra-opus and
  pushes (locked, safe concurrently). Call it after every real improvement (run total.py first).

## Tools (C++ built with: clang++ -O3 -march=native -std=c++17 -o X X.cpp)
- beam.cpp: full 4^6-move beam search. `beam <in> <idx> <width> <seed> WH W1 W2 WL [maxDepth] [forcedSchedule]`.
  Best weights so far: 3 1 0.3 0.5 (very sensitive; seeds vary a lot -> portfolio/min over runs).
  env PREFIX=<file of lines> replays a prefix first (binary beam_p has this; rebuild beam from beam.cpp to get it).
- harness.py <name> <width> <seed> [weights..] [--only i,j] [--bin cycle|beam] : runs over patterns, keeps improvements.
- resuffix.py <name> <width> <cuts> : cut best program at N lines before end (dN) / fraction (fX), re-beam the suffix
  wide from the exact replayed state, splice if shorter. Very effective on large (-200 in one pass).
- cycle.cpp: SA over (free prefix, closed k-line cycle). cyc2.cpp: EXACT static/2-tick cycle search (r<=5 in secs).
  cyc3.cpp: exact periodic 3-tick cycles (new, being tested). cyc2_all.py assembles prefix+cycle programs.
- polish.cpp/polish_all.py: delete/merge-line local search (found nothing on current bests).
- sweepdp.cpp / sweep2.py: row-sweep with DP-planned punchers: clearly WORSE than beam, abandoned.

## Facts
- After a submission P and halo are empty -> state = emitter config only. All of P must be rebuilt after each
  submission. Any valid 2-tick copy is automatically a period-2 cycle (moves are reversible).
- Medium: 92/210 patterns provably need >=3 lines/copy (cyc2 NONE); repeats floor ~4391 -> medium < 5000 infeasible.
- Best programs never create halo matter; big patterns lose many ticks in the TAIL (last 5-15% of cells).
- Tail heuristic in beam (env WTM/WTS) made things worse.

## CPU
10 cores shared by 3 agents + coordinator: use at most JOBS=3 parallel worker processes (export JOBS=3) and never
start more than one heavy batch at a time.

## Timeouts (added by coordinator)
Every driver (harness, resuffix, sweep*, polish_all, tune) now runs each worker through harness.run_job, which kills
it after JOB_TIMEOUT seconds (env, default 600) and skips it ("TIMEOUT ..." in the log). Set JOB_TIMEOUT higher only
deliberately; for your own subprocess calls use run_job too. Never leave a single exploratory process running > 15 min.

## satcyc.py (exact SAT search, medium agent)
Exact model of the rules (only P+halo cells, emitter offsets -R..R around the corner, one F/B/T per tick) as CNF,
solved by Z3's SAT core via ctypes (z3sat.py loads the libz3 dylib from the Android SDK; no install needed).
- `python3 satcyc.py <in> <idx> cycle K [m]` : periodic K-tick cycle from empty matter, submission on tick K and
  >= m submissions per cycle -> SAT + K lines / UNSAT (proof: no such periodic cycle) / UNKNOWN.
- `python3 satcyc.py <in> <idx> copy K` : one copy in exactly K ticks from ANY emitter config (copy 1..k all UNSAT
  => every copy needs > k ticks).
- `python3 satcyc.py <in> <idx> auto <file with current best program> [tmo_ms=30000] [cycle_tmo_ms=8000]` : tries
  (K,m) cycles from the current rate downwards, then shortest prefix into the cycle (fixed cycle and joint model);
  prints a shorter program on stdout (log on stderr) or nothing.
- `python3 satdrive.py 2-medium <i,j,..|all> [tmo_ms] [cycle_tmo_ms]` : runs auto via run_job (JOBS, JOB_TIMEOUT),
  verifies and saves improvements with save_best.
Functions for own scripts: cycle_only(r,pat,K,m,tmo,free,want_cfg), prefix_to(r,pat,T0,target_cfg,tmo),
prog_with_prefix(r,pat,count,K,m,T0,tmo). UNSAT near the optimum is slow (K=5 on r=5 ~1 min), SAT is fast.
