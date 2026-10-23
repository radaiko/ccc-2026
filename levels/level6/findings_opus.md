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
