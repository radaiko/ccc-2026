# CCC rules so far (through Level 5)

Theme: FAB-42, a nanofabricator that creates matter with laser light on a **hexagonal board of
hexagonal cells**. Six emitters ride on a rail along the border; where beams cross, matter is
created or destroyed; a pick-up arm removes ("submits") a target pattern once it is complete.

## Levels

- **Level 1**: print the empty board for each radius (ASCII art).
- **Level 2**: board with one emitter digit on the border; its beam turns every cell it crosses into `M`; print board.
- **Level 3**: up to 6 emitter digits + existing matter; cell hit by exactly 2 beams -> `M`, by >=3 -> `O`; print board.
- **Level 4**: input is only radius + program; 6 emitters start at their corners, move F/B along the border,
  toggle T; one instruction line per tick, active emitters fire every tick; print final board.
- **Level 5**: plus a target pattern; after each tick, if the pattern is present exactly and with no adjacent
  matter, it is removed and counted; print the count per program.

## Latest level (Level 5): input format

```
N                    number of programs
--- repeated N times, one empty line between programs ---
r rows cols          board radius, rows = 2r+1, cols = 4r+1
<rows lines>         the pattern, drawn as a full board of radius r: '*' border, 'O' empty, 'M' pattern matter
L                    number of instruction lines (L = 0 occurs)
<L lines>            6 instructions separated by spaces, for emitters 1..6, each one of F B T -
```

Example input (complete):
```
2
3 7 13
---*-*-*-*---
--*-O-O-O-*--
-*-O-M-M-O-*-
*-O-M-O-O-O-*
-*-O-M-M-O-*-
--*-O-O-O-*--
---*-*-*-*---
7
F T T F - -
T - - T - -
T B - B T -
T F - F T -
T B - B T -
T F - F T -
T B - B T -

3 7 13
---*-*-*-*---
--*-O-O-O-*--
-*-O-O-O-O-*-
*-O-O-M-O-O-*
-*-O-M-M-O-*-
--*-O-O-O-*--
---*-*-*-*---
6
B - - - - -
T T T - - -
- - - - - -
- - - - - -
- - - - - -
- - - - - -
```

## Latest level (Level 5): output format

N lines, one integer each: how many patterns were submitted while running that program.
Example output: `3` then `5` (two lines).

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
- An emitter sits on a border cell (in L2/L3 its digit replaces that `*`; L3 emitters may be anywhere on the
  border, not only corners). The beam starts at the next cell in its direction and continues while the cell
  is `O` or `M`; it stops at the first border cell (`*` or digit) or the edge of the grid. Border cells never change.
- An emitter whose direction points along or out of the border (e.g. emitter 1 on the top edge) hits nothing.
- **L2 only:** single emitter at full power, every cell the beam crosses becomes `M`.
- **L3 onward:** all active beams fire simultaneously. Count beams per interior cell (matter does not block
  beams; counts are taken before any change): 0 or 1 -> unchanged, exactly 2 -> `M`, >= 3 -> `O` (destroyed).

## Rail and programs (Level 4, still valid)

- Each program starts with an empty board (all interior `O`) and 6 emitters, one per direction 1..6,
  all **inactive**, each in its corner: 1 = left (r,0), 2 = top-left (0,r), 3 = top-right (0,3r),
  4 = right (r,4r), 5 = bottom-right (2r,3r), 6 = bottom-left (2r,r).
- Rail = border ring, 6r cells. Clockwise order from the left corner: r steps (-1,+1), r steps (0,+2),
  r steps (+1,+1), r steps (+1,-1), r steps (0,-2), r steps (-1,-1). Emitter k starts at ring index (k-1)·r.
- `F` = one cell clockwise (index+1 mod 6r), `B` = one cell counterclockwise (index-1 mod 6r),
  `T` = toggle active/inactive, `-` = nothing. Emitters never rotate; several may share a cell; moves wrap.
- Clockwise is as seen on screen: F on emitter 1 at the left corner goes up-right; B on emitter 5 on the
  bottom edge moves it right.
- Each tick: (1) the 6 instructions of one line are applied simultaneously, (2) every active emitter fires
  once and the 2 / >=3 rule is applied. Active emitters fire **every** tick, also on `- - - - - -` lines.
- L4 output: the final board of each program, empty line between boards.

## Pattern submission (Level 5)

- Pattern P = the set of `M` cells of the given drawing (same radius and coordinates as the board).
  Seen in data: always one connected group of 2..140 cells; drawings contain only `* - O M`.
- Tick order: (1) execute one instruction line, (2) matter is created/destroyed, (3) if a valid pattern is
  present it is submitted.
- Valid iff **every** cell of P is `M` on the board (exact position: no shift, rotation or mirroring) **and**
  no cell outside P that is hex-adjacent to a cell of P is `M`. Matter elsewhere is allowed.
- Submit: all cells of P become `O`, count += 1. Other matter stays; emitters keep positions and on/off state.
- At most one submission per tick (one fixed pattern). Because active emitters keep firing, the pattern can be
  rebuilt and submitted on consecutive ticks: example program 2 builds it at tick 2 and again at ticks 3-6 -> 5.

## Constraints seen in the data

| level | N (example/small/large) | radius | other |
|---|---|---|---|
| 1 | 3 / 10 / 100 | 3..19 | |
| 2 | 6 / 10 / 100 | 3..19 | exactly 1 emitter per board |
| 3 | 3 / 10 / 100 | 3..19 | 2..6 emitters, no duplicate digits, pre-existing `M` |
| 4 | 3 / 10 / 100 | 2..19 | L = 3..6 / 10 / 100 |
| 5 | 2 / 20 / 200 | 3..9 | L = 0..2928, pattern 2..140 cells, answers 0..9 (many 0) |

- Sizes are tiny: direct simulation (≤ 6 beams of length ≤ 2r per tick) is far within PyPy's 5 min CPU/input.

## Judging

- No `validator.py` in any level so far: output must match the expected output **exactly**.
- L2-L4: the border may be printed with or without emitter digits (both judged correct). Accepted L2/L3
  solutions keep the digits from the input; the accepted L4 solution prints a plain `*` border.
- Board outputs need exactly one empty line **between** boards (none before the first). Trailing newline
  at the end of the file is not significant.
- One output file per input file; each input is all-or-nothing.

## Pitfalls / assumptions seen in solutions

- No accepted solution (levels 1-5) needed a `# ASSUMPTION:` comment; all rules above matched the examples.
- Radius includes the border ring; lines have trailing dashes too (width 4r+1).
- One beam alone does nothing since L3; only exactly-2 creates. >=3 destroys even existing matter.
- The beam starts at the cell after the emitter; it never touches `*`/digits, so L2/L3 border digits survive.
- Check the pattern every tick, after create/destroy, even if nothing changed; don't stop after the first
  submission, and keep emitter states after a submission.
- Adjacency check uses all 6 neighbours `(i, c±2)`, `(i±1, c±1)`; border cells are never `M`, so just bound-check.
- Parsing: L4/L5 input splits cleanly on whitespace (pattern rows have no spaces; `-` is its own token).
  L2/L3 board rows contain no spaces either; skip empty lines between blocks. L = 0 -> answer 0.

## Accepted core (levels/level5/solution.py is the full reference)

```python
DIRS = [(0, 2), (1, 1), (1, -1), (0, -2), (-1, -1), (-1, 1)]   # emitters 1..6, (drow, dcol)
NB = [(0, 2), (0, -2), (1, 1), (1, -1), (-1, 1), (-1, -1)]     # hex neighbours
# ring(r): start (r, 0), r steps each of (-1,1),(0,2),(1,1),(1,-1),(0,-2),(-1,-1); emitter k at index (k-1)*r
# per tick: apply F/B/T; cnt[cell] = #active beams through it; 2 -> 'M', >=3 -> 'O';
# then if all P are 'M' and no neighbour-of-P outside P is 'M': set P to 'O', count += 1
```
