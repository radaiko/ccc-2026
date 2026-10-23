# Astra findings — Level 6

## Verified results

- Best complete, simulation-checked output set so far: **17,215 instruction lines** across the four upload files (110 small, 5,991 medium, 5,715 large, 5,399 enormous). This beats the latest recorded Opus total of 17,223. The requested 18k reporting milestone has been reached; 10k is still the optimization target.
- The four correctly named upload files are in `levels/level6/output/`; the merged working copies are in `levels/level6/runs/best/`. Optimization is continuing toward the requested total of 10,000 or less.
- At the earlier 20,380-line merge, the second agent's independent outputs contributed a measured **1,546-line improvement** over the parent-only total of 21,926.
- The latest upstream solution was copied to `levels/level6/candidates/astra_team.py`, independently validated, compacted, and merged per pattern with Astra/independent/Opus outputs. Its four standalone scores were 118 / 6,528 / 5,997 / 5,556; combining each candidate's best patterns produced the 17,229 total.
- `levels/level6/candidates/select_best.py` selects the shortest validated program for each pattern across available candidate output sets and writes `levels/level6/runs/best/`.

## Most useful new finding from upstream

- Guide **all six emitters** toward unfinished cells. The old nearest-pair heuristic leaves other emitters poorly positioned.
- For each emitter, calculate its minimum rail movement plus activation cost to any beam line containing an unfinished target cell. Use the sum over all six as a beam-search tie-breaker, with strong priority on already-created target matter.
- The newer upstream search additionally rewards target cells potentially reachable by two different axes within one or two ticks, plus whole-line painting opportunities where other beams can remove the halo. This lookahead produced the biggest new improvement on large and enormous inputs.
- On the first five enormous-file patterns, generating one copy each with the same search width improved the combined lengths from **278 to 186 ticks**. Every resulting program passed the independent Level 5 simulator. This is a measured sample improvement; the new full-file totals are still being computed.

## Other working optimizations

- Exact bitsets: exactly two beam hits create matter, three or more erase it. Track target cells and their adjacent non-target cells; other matter never affects validity.
- Enumerate joint six-emitter instructions with shared prefixes. If a prefix creates forbidden adjacent matter and none of the remaining possible rays can erase it, prune it immediately.
- Allow target destruction and repair; forbidding every triple hit on a target unnecessarily restricts the search.
- Cache transitions from a post-pickup emitter configuration to the next pickup. Returning to the same configuration allows reusing a whole production segment.
- Solve exact-two-hit constraints for static six-beam configurations. When one configuration creates the whole target, each additional waiting tick creates another copy.
- Preserve promising partial searches: switch off the extra beams and complete remaining cells with a safe two-emitter target-cell walk.
- Compact programs by moving commands into adjacent empty instruction slots or cancelling adjacent inverse commands. The emitter state after the edited window stays identical; replay matter effects through the suffix to verify validity.
- Allocate more search time to larger target patterns rather than giving every pattern an equal budget.
- Coordinate descent over closed 2/3/4-tick emitter tracks, with two-emitter block updates to escape local minima, saved 7 additional lines on large. The example improved from 23 to 20 (excluded from the upload score). Medium did not improve in this run.
- Searching exact 2/3-tick cycles anchored at existing pickup configurations did not improve the 17,229-line set. Most useful shorter cycles require a different entry configuration.
- Before publishing, merge and validate all run directories plus the existing upload files. Only rewrite `output/` when the total is strictly below both the existing upload total and the latest score recorded in `findings_opus.md`.

## Validation details

- Every reported full-file score has been checked by simulation, including the exact requested production count.
- The repository validator explicitly marks “all emitters off at program end” as a team assumption that the official sandbox does not check. The supplied statement also does not require this shutdown.
- The generic validator self-test's deletion of the final example line is unsuitable here: the final sample line only switches an emitter off after the last pickup. Removing it leaves a valid program under the stated rules.

## Commands

```sh
python3 levels/level6/candidates/astra_check.py astra_opt
python3 levels/level6/candidates/compact.py astra_opt
python3 levels/level6/candidates/select_best.py
```
