# CCC rules so far (through Level 6)

Theme: FAB-42, a nanofabricator that creates matter with laser light on a **hexagonal board of
hexagonal cells**. Six emitters ride on a rail along the border; where beams cross, matter is
created or destroyed; a pick-up arm removes ("submits") a target pattern once it is complete.

## Levels

- **Level 1**: print the empty board for each radius (ASCII art).
- **Level 2**: one emitter digit on the border; its beam turns every cell it crosses into `M`; print board.
- **Level 3**: up to 6 emitter digits + existing matter; hit by exactly 2 beams -> `M`, >=3 -> `O`; print board.
- **Level 4**: radius + program; emitters start at corners, move F/B on the rail, toggle T; print final board.
- **Level 5**: plus a target pattern, submitted when complete with no adjacent matter; print the count.
- **Level 6** (optimization): input is pattern + required count; **output a program** that submits the pattern
  at least that many times. Score = total instruction lines over all programs, lower is better.

## Latest level (Level 6): input format

```
N                    number of patterns
--- repeated N times, one empty line between patterns ---
r rows cols count    board radius, rows = 2r+1, cols = 4r+1, required submissions (count >= 1)
<rows lines>         the pattern, drawn as a full board of radius r: '*' border, 'O' empty, 'M' pattern matter
```

Example input (first of 3 patterns; the others are `3 7 13 1` and `4 9 17 4`):
```
3
3 7 13 3
---*-*-*-*---
--*-O-O-O-*--
-*-O-M-M-O-*-
*-O-M-O-O-O-*
-*-O-M-M-O-*-
--*-O-O-O-*--
---*-*-*-*---
```

## Latest level (Level 6): output format

N programs in input order, **exactly one empty line between programs** (none before the first). Each program
is one or more lines, each line = 6 instructions for emitters 1..6, each one of `F B T -`, separated by single
spaces (L4 program format), e.g. `F - - - - -`, `- - B - - -`, `T - T - - -`.
The sample answer (446 lines: 116 + 56 + 274) is just one valid answer; the accepted solution needs 68 in total.

## Board geometry (Level 1, exact)

- Board of radius `r` = hex cells at hex distance `<= r` from the centre. Distance `r` = border ring `*`
  (6r cells); distance `<= r-1` = interior cells `O` (3r(r-1)+1 cells). Radius counts the border: r=3 -> 7 lines.
- Text: `2r+1` lines, each exactly `4r+1` chars. Line `i`, `k=|i-r|`: `k` dashes + `2r+1-k` cells joined
  by `-` + `k` dashes. Top/bottom lines are all `*`; other lines are `*` + `O`s + `*`. `-` is only padding.
- r=3: `---*-*-*-*---`, `--*-O-O-O-*--`, `-*-O-O-O-O-*-`, `*-O-O-O-O-O-*`, then mirrored.
- Char-grid ("doubled") coordinates: cell `j` of line `i` is at column `c = k + 2j`; cells are exactly the
  positions with `(c+i+r)` even. The 6 hex neighbours of `(i, c)` are `(i, c±2)` and `(i±1, c±1)`.

## Emitters and beams (Levels 2-3, still valid)

- Directions, as (row, col) steps in the char grid: `1` → (0,+2), `2` ↘ (+1,+1), `3` ↙ (+1,-1),
  `4` ← (0,-2), `5` ↖ (-1,-1), `6` ↗ (-1,+1).
- An emitter sits on a border cell. Its beam starts at the next cell in its direction and continues while the
  cell is interior; it stops at the first border cell. Border cells never change. An emitter whose direction
  points along or out of the border (e.g. emitter 1 on the top edge) hits nothing.
- **L3 onward** (L2: one emitter painting its whole beam `M`): all active beams fire simultaneously. Count
  beams per interior cell (matter does not block beams; counts taken before any change): 0 or 1 -> unchanged,
  exactly 2 -> `M`, >= 3 -> `O` (destroyed).

## Rail and programs (Level 4, still valid)

- Each program starts with an empty board (all interior `O`) and 6 emitters, one per direction 1..6,
  all **inactive**, each in its corner: 1 = left (r,0), 2 = top-left (0,r), 3 = top-right (0,3r),
  4 = right (r,4r), 5 = bottom-right (2r,3r), 6 = bottom-left (2r,r).
- Rail = border ring, 6r cells. Clockwise order from the left corner: r steps (-1,+1), r steps (0,+2),
  r steps (+1,+1), r steps (+1,-1), r steps (0,-2), r steps (-1,-1). Emitter k starts at ring index (k-1)·r.
- `F` = one cell clockwise (index+1 mod 6r), `B` = one cell counterclockwise (index-1 mod 6r),
  `T` = toggle active/inactive, `-` = nothing. Emitters never rotate; several may share a cell; moves wrap.
- Clockwise is as seen on screen: F on emitter 1 at the left corner goes up-right.
- Each tick: (1) the 6 instructions of one line are applied simultaneously, (2) every active emitter fires
  once and the 2 / >=3 rule is applied. Active emitters fire **every** tick, also on `- - - - - -` lines.
- One instruction per emitter per tick: an emitter **cannot move and toggle in the same tick**. An emitter
  toggled on fires in that same tick; one toggled off does not.

## Pattern submission (Level 5, still valid)

- Pattern P = the set of `M` cells of the drawing (same radius and coordinates as the board).
- Tick order: (1) execute one instruction line, (2) matter is created/destroyed, (3) if valid, submit.
- Valid iff **every** cell of P is `M` (exact position: no shift, rotation or mirroring) **and** no cell
  outside P that is hex-adjacent to P is `M`. Matter elsewhere (not adjacent to P) is allowed.
- Submit: all cells of P become `O`, count += 1. Other matter stays; emitters keep positions and on/off state.
- At most one submission per tick. Active emitters keep firing, so P can be rebuilt on later ticks.
- L5 input was: N, then per program `r rows cols`, the pattern drawing, `L`, L instruction lines; output = count.

## Level 6 rules

- Each program is simulated from scratch with all rules above (empty board, emitters inactive at corners).
- A program is valid iff it submits the pattern **at least** `count` times (more is fine; official sandbox:
  "Simulation accepts X of Y required patterns" when X < Y). Program length has no stated limit.
- Team validator ASSUMPTION (not in the statement): after the last line **all 6 emitters must be inactive**.
  All sample programs end that way; it costs at most one line (`T` for each still-active emitter).
- Score per input = total number of instruction lines of all N programs; lower is better.

## Constraints seen in the data

- L1-L4: N <= 100, radius 2..19 (L3: 2..6 emitter digits; L4: L <= 100). L5: N <= 200, r 3..9, L 0..2928.
- L6: example 3 / small 10 (r=3) / medium 210 (r 3..5) / large 190 (r 6..8) / enormous 140 (r 9..12)
  patterns; count 1..19 (enormous 1..2); pattern 2..297 cells, always one connected group; only `* - O M`.
- Sizes are tiny: direct simulation is far within PyPy's 5 min CPU/input; accepted L6 runs ~5 s in CPython.

## Judging

- L1-L5: no validator; output must match exactly (L2-L4 borders with or without emitter digits).
- L6: `levels/level6/validator.py` (port of the official sandbox `data/sandbox-level-6.html`) simulates every
  program: any valid set is accepted, score = total lines (`SCORE = 'min'`); example need not equal sample.
- One output file per input file; each input is all-or-nothing. Trailing newline not significant.

## Level 6 accepted strategy (levels/level6/solution.py)

- Use only 2 emitters with non-parallel directions (pairs of 1,2,3; e and e+3 are parallel). Their beams meet
  in exactly one interior cell, which gets 2 hits -> `M`; nothing else changes. So the pair is a cursor that
  paints one cell per tick while both are active.
- Every interior cell has exactly one rail position per direction whose beam hits it. Map each cell of P to
  (a, b) = signed rail offsets of the two emitters from their start corners (in [-3r, 3r)).
- With both active, a tick moving each emitter by -1/0/+1 is safe iff the new (a, b) is a P cell (king move
  in (a, b) space). Longer jumps: switch one beam off (`T`), move, switch it on (`T`); cost
  `max(d_off + 2, d_other)` ticks (gate whichever emitter makes this smaller), the other moving meanwhile.
- Start: each emitter moves to its first position and toggles on as soon as it arrives (the other may still
  be moving). End: one line `T` on both emitters.
- Route: greedy walk over the king-move graph of P cells (next = unvisited neighbour with fewest unvisited
  neighbours; when stuck, BFS back through already painted P cells). Tries 3 pairs x 8 tie-break variants
  x 5 start cells, keeps the shortest program.
- Copies: walk the route forward, then backward, etc. Submission clears the cursor cell too, so one `- -` tick
  repaints it before walking back. So each copy costs about |P| ticks.
- Accepted totals: example 68, small 334, medium 25085, large 21436, enormous 19654 lines.
- Untested idea: 3 active emitters paint up to 3 cells per tick (pairwise intersections), but a cell hit by
  3 beams is destroyed and every extra hit must avoid cells adjacent to P.

## Pitfalls / assumptions seen in solutions

- No accepted solution (levels 1-6) has a `# ASSUMPTION:` comment; the only assumption is the L6 validator's
  "all emitters off at the end".
- Radius includes the border ring; lines have trailing dashes too (width 4r+1).
- One beam alone does nothing since L3; only exactly-2 creates. >=3 destroys even existing matter.
- Two opposite emitters on the same line overlap along the whole line -> every cell there gets 2 hits.
- Check the pattern every tick, after create/destroy; don't stop after the first submission.
- Board outputs (L1-L4): exactly one empty line **between** boards.
- L6: never rest the cursor on a non-P cell while both beams are on (it creates halo/stray matter); revisiting
  an already-`M` P cell is harmless. Count submissions with a simulator (the validator) before trusting output.
- Parsing: inputs split cleanly on whitespace (pattern rows have no spaces). Skip empty lines between blocks.

## Accepted core (levels/level5/solution.py simulates; levels/level6/solution.py generates)

```python
DIRS = [(0, 2), (1, 1), (1, -1), (0, -2), (-1, -1), (-1, 1)]   # emitters 1..6, (drow, dcol)
# ring(r): start (r, 0), r steps each of (-1,1),(0,2),(1,1),(1,-1),(0,-2),(-1,-1); emitter k at index (k-1)*r
# rail offset for 0-based emitter e: from each ring index j step along DIRS[e]; every interior cell
#   reached gets offset (j - e*r + 3r) % 6r - 3r
```
