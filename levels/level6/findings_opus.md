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
