# Level 6 findings (opus)

- All current team "best" outputs (runs/best, astra, compact, ...) leave emitters ACTIVE at the end, so
  `levels/level6/validator.py` (assumption: all emitters off) rejects them. The official sandbox only counts
  submissions. Scores below follow the same convention (no final toggle-off line).
- Cost split of the 21,797 baseline: medium 85% / large 70% of lines are repeat copies (cycle length per copy),
  enormous is dominated by the first build (~35 lines for ~95 cells).
- Only P cells and their halo matter: restrict all bitsets to P ∪ halo (≤ 7 words even at r=12).
- Hit counting with 3 bit-sliced accumulators (s2 |= s1&L; s1 |= s0&L; s0 |= L) per beam; exactly-two = s1&~s2.
  Enumerating all 4^6 instruction lines with shared prefixes costs ~5.5k bitset updates per state, fast in C++.
- Full-move beam search in C++ (`candidates/opus/beam.cpp`), creating halo matter allowed (it can be erased
  later by 3 hits), score = copies·big + 4·|P∩M| − 3·|halo∩M| + pairs-of-emitters-within-1/2-ticks potential
  on missing cells. Width 1000 on medium: better than the team best on 53/210 patterns, -181 lines; width 300
  on large: -254 lines.

## Score log (merged best over all run dirs, 4 upload inputs, no final toggle-off line)

- Start of my session: 21,797 (small 111, medium 6776, large 7666, enormous 7244).
- After astra's updates + opus beam (medium w=1000, large w=300): 19,775 (small 110, medium 6018, large 6606, enormous 7041).
- Beam + astra's all-six-emitter line-distance tie-break (weight 0.5; sum over emitters of rail moves, +1 if off,
  to the nearest line through a missing cell) cut a 28-pattern large sample from 1169 to 818 lines.
- Merged total 17,223 (small 110, medium 5992, large 5722, enormous 5399), user target now <5k per file.
- Steady state after any submission = emitter configuration only (pattern+halo are empty), so repeats are a
  closed k-line cycle. `opus/cycle.cpp`: SA over (free prefix, closed cycle), valid iff the cycle from empty
  matter submits on its last line AND prefix (or prefix+cycle) submits on its last line. Needs ~2M iterations
  to find 2-cycles reliably.
- Pure row sweep with exact DP for the 4 punchers (`opus/sweepdp.cpp`) leaves ~3 unpunched halo cells per copy
  on a 110-cell r=9 blob; with cleanup it is not better than the beam (43 lines for 2 copies).
- Lower bound per repeat copy: submission clears every P cell, so all of P must be rebuilt in the ticks after
  the previous submission. 1 line/copy needs a static config; otherwise >= 2. Because F<->B and T<->T are
  symmetric, ANY valid 2-tick copy (dirty X then clean Y, X adjacent to Y) is already a period-2 cycle.
  `opus/cyc2.cpp` enumerates clean Y then adjacent X with bitset pruning: exhaustive in seconds for r<=5,
  so "NONE" proves >= 3 lines per copy (e.g. medium 9, 50, 132, 167, 197 have no 2-tick copy).
- Medium copies by current per-copy cost: 99 at 1, 915 at 2, 464 at 3, 146 at 4, 152 at 5, 59 at 6+.
  Even if every 3+ pattern reached 2 lines/copy medium would only save ~1550.
- `opus/total.py` merges every run dir + output/, re-verifies by simulation and rewrites output/ when better.
- [large agent] beam halo weight WH=3 is far too low on large: the beam paints halo and then needs 1 tick per halo erasure (tails of 100+ ticks, often NONE). WH=100 (practically forbid halo) at width 300 FROM SCRATCH beat the merged best on a 12-pattern sample of the most expensive patterns (1168 vs 1237); full large pass with WH=100 w=300: 5351 -> 5274.
- [enormous agent] With WH=3 the beam paints halo early and then never cleans it (no guidance towards dirty halo):
  width 300 returned NONE on many enormous patterns (also thin paths like #2). WH=100 (`beam .. 100 1 0.3 0.5`,
  halo effectively forbidden) full pass at width 300: enormous 5371 -> 5039.
- [enormous agent] Count-2 patterns: copy 2 = copy-1 emitter configurations replayed backwards (F<->B, T<->T,
  candidates/opus/rev_e.py) is often valid and drops copy 1's leading travel ticks: -38 then -4 lines on enormous.
- Goal raised to < 15,000 total (at 16,326: medium 5959, large 5218, enormous 5039). Planned split: medium ~5550,
  large ~4770, enormous ~4550.
- [medium-cycles agent] `opus/retbeam.cpp` + `retauto.py`: return-constrained beam from (anchor config, empty matter)
  that must submit NC copies with the last one exactly at the anchor (hard prune: ring distance + toggle to anchor
  <= ticks left). Anchors = submission configs of the current best. NC=1 cycles (K<=current per copy) are almost
  never found; NC=2/3 multi-copy cycles are: 167 156->126 (2 copies / 14 ticks), 197 75->71, 49 90->85, 132 64->63.
  Medium 5991 -> 5951. Use WH=100 (halo weight) in the beam weights.
- [enormous agent] Weights 100 1 0.3 0.25 (lower line-distance weight WL) beat 100 1 0.3 0.5 on a 20-pattern width-100
  sample (raw 866 vs 964); width-600 pass with them: enormous 5035 -> 4853, reversed copy 2 again -> 4841.
- [enormous agent] beam_e.cpp env HFORBID=1: skip children that create halo matter from a clean parent and prune
  subtrees where a 2-hit halo cell cannot get a 3rd hit from later emitters: 2-2.5x faster, same quality at WH=100.
- [enormous agent] resuf_e.py (resuffix with --w/--bin/--seeds, cuts dN/fX/sK/tK, longest programs first) with
  beam_h (HFORBID) width 2000, weights 100 1 0.3 0.25, cuts d4,d7,d10,d14,s0: enormous 4841 -> 4723 after covering
  only the programs of length >= 35 (stopped to switch to medium); the rest of the patterns still untried.
- [medium-cycles agent] Run-ins into the cycle (retbeam start=initial config, target=any submission config of the
  found cycle, NC=1/2, rotated cycle after it) turn "equal-rate" cycles into wins: 50 122->116, 167 ->122,
  119 85->79, 132 ->54 (NC=3, 28 ticks), 49 ->82, 35 ->86. `retauto.py --kplus 1 --runin 6`.
- [large agent] beamL (WH=100) stalls (NONE or long tails) when emitters sit in a plateau where every improving path needs >2 ticks without visible progress (e.g. 24/28 cells for 180 ticks); tail terms WTM=1 (max over missing cells of 2nd-nearest emitter distance) removed all NONEs on the sample (sample 1169 -> 1124). Two more full w300 passes with WTM=1: 5216 -> 5194. HMODE/WD cell-hardness weights, PCAP, COPYF smoothing, W1=2/WL=1 were neutral or worse.
- Waste profile of the best programs at total 15,936 (scratchpad waste.py): ticks spent on the last 10% of each
  copy's cells: medium 343 / large 815 (16%) / enormous 1054 (22%); one-cell ticks 598 / 651 / 710; start travel
  102 / 157 / 121. Medium's gap is structural (cycle length, proven floor 4895); large/enormous lose most in tails.
- [large agent, medium run-ins] runin.py: exact SAT (satcyc Model) check "any submission at a tick < f" (f = current first submission tick, one query with OR over all submission vars). On the 169 medium patterns with optimal repeat rate: 158 are UNSAT => their programs are provably optimal (first copy at minimum tick, repeats at the floor). For the other 11, exact joint SAT (prefix of T0 ticks with >= j copies ending in the config that closes a (K,m) cycle, j<=2, m<=2) improved 9 patterns by 1 line each (72, 20, 4, 191, 131, 114, 83, 55, 11): medium -9. 106 and 33 can submit earlier but no cycle entry found (j<=5, m<=3).
- [enormous agent, medium] Full medium pass beam_h (HFORBID=1) width 3000 weights 100 1 0.3 0.25: 5901 -> 5855
  (mostly 1-line wins, best -4 on #192); a 30-pattern width-1000 sample with WH=3 vs WH=100 was similar (1681 vs 1687).
- [medium agent] Exact SAT model (candidates/opus/satcyc.py, Z3 SAT core via ctypes from the Android-SDK libz3)
  reproduces cyc2 (2-cycles) in <0.3 s and proves periodic 3-cycles UNSAT for all 20 worst medium patterns in
  <0.3 s each; periodic K=4/5 UNSAT proofs take 5-80 s on r=5. 50/49/35 have no periodic <=5-cycle, but 35's
  5-tick copies come as a period-10 2-copy cycle, and 50 has a 5-tick copy from SOME config (copy 5 SAT, 48 s).
- [medium agent] Segment re-solve (satcyc.py seg: config after submission i -> config at submission j with the
  same submissions in fewer lines, both ends fixed, replaces all identical occurrences) is fast (anchored
  instances solve in ~1 s): 197 68 -> 67. Anchored cycles at the current submission configs of 167/50 are UNSAT
  for every lower rate (the beams' cycles are locally optimal at their anchors). Medium total 5854.
- [large agent, medium run-ins] Any valid 2-tick copy after a submission can be repeated forever (reversible moves), so if no prefix "first copy at T0 + second copy 2 ticks later" exists (runin.py j=2 UNSAT), the total is >= f_min + 1 + 2(c-1)... for 106 and 33 this proves the current programs optimal. After the run-in fixes all 169 non-repeat-gap medium patterns are provably optimal given the per-copy floors.
- [medium-cycles agent] retauto pass 2 (top 20, NC 2/3/1, kplus 1, runin 6): 153 75->58 (2 copies / 6 ticks = 3.0
  per copy), 28 61->57, 26 54->52, 186 ->28, 180 ->50, 58 35->32. Medium 5847.
- [medium agent] MULTI-COPY cycles break the periodic bound: 142 and 105 have no periodic 3-cycle (UNSAT) but a
  6-tick cycle with 2 submissions (3+3) is SAT in ~2 s -> 142 54 -> 44, 105 26 -> 23; 28 K=9 m=2 57 -> 56
  (satcyc.py cycle K m; satscan.py scans (K,m<=3) below the current rate, satbuild.py builds SAT prefix + cycle).
  Segment re-solve also gave 132 54 -> 51, 130 79 -> 76.
- [medium agent] 28: free (K,m) scan found K=13 m=3 then K=8 m=2 (two 4-tick copies; periodic 4 is UNSAT) ->
  57 -> 50; 11/3 and 7/2 UNSAT. Seg re-solve pass over the 41 gap patterns saved 10 more (203, 186, 107 -1).
  Medium 5820.
- [medium-cycles agent] Fixed-anchor SAT (`opus/satanchor.py`, satcyc.Model with the cycle's last config pinned to a
  submission config of the best program, sym off): UNSAT/SAT in ~20 s where free-anchor SAT is 'unknown' after
  120 s (167, K=13 m=2). `satauto.py` drives it (K = ceil(rate*m)-1 down): 50 115->107 (m=2 K=11), 197 67->65,
  132 51->50; anchors of 167 proven to have no (13,2) / (6,1) cycle.
- [large agent 2] l2_bounce.py: after the k-th submission walk the program's own config path BACK and forth inside a window (moves are reversible), turning at every submission, optionally repeating the turning config once (a reversed copy needs the cells of the submission config again). Per copy = the cheapest copy segment of the program. Cheap (1 s for all of large): 143 153->145, 54 70->65, 184 78->74, large -34 together.
- [medium agent] Exact per-copy lower bounds (free copy k from ANY config UNSAT for k=1..rate-1, satscan2.py):
  repeat rate is OPTIMAL for 31, 187, 184, 182, 124, 49, 130, 158, 26, 59 (5/copy) and 107, 207, 77, 192 (4/copy);
  only run-ins can still improve them. 58: copy 5 exists, K=11 m=2 (5+6) -> 32 -> 30; 170 K=14 m=3 20 -> 19;
  50 K=11 m=2 107 -> 106; 186 17/3 and 11/2 UNSAT; 190 10/3 and 3 UNSAT.
- CPU (Apple M5: 4 performance + 6 efficiency cores; load ran at ~23): profile of beam_e4 = evaluate 43%, leaf/child
  build 30%, run/select 21%. PGO+LTO build (-fprofile-instr-generate, llvm-profdata, -flto -fprofile-instr-use)
  of beam_e.cpp: identical output, ~14% less CPU -> swapped in as beam_e4. Same recipe made beam_l2/beamL ~15% SLOWER
  (kept the old builds). Oversubscription + 600 s job timeouts wastes CPU: keep heavy processes <= ~10 in total.
