# CCC rules so far (through Level 1)

Theme: FAB-42, a nanofabricator that "creates matter with laser light, one hexagonal cell at a
time". The board is a big **hexagon made of hexagonal cells**. Level 1 only teaches the machine
what its board looks like; later levels will most likely place or move things on this board.

## Levels

- **Level 1**: for each given radius, print the board as ASCII art (`*` border ring, `O` inner
  cells, `-` indentation/spacing), boards separated by one empty line.

## Latest level (Level 1): input format

```
N            number of radii
r_1          one integer per line, repeated N times
...
r_N
```

Example input:
```
3
3
6
4
```

## Latest level (Level 1): output format

For each radius, in input order, print the board (2r+1 lines). Put exactly **one empty line
between consecutive boards** ("Mandatory empty line between boards"); nothing before the first
board, no blank line needed after the last one.

Example output for radius 3 (the first board of the example):
```
---*-*-*-*---
--*-O-O-O-*--
-*-O-O-O-O-*-
*-O-O-O-O-O-*
-*-O-O-O-O-*-
--*-O-O-O-*--
---*-*-*-*---
```
Radius 4:
```
----*-*-*-*-*----
---*-O-O-O-O-*---
--*-O-O-O-O-O-*--
-*-O-O-O-O-O-O-*-
*-O-O-O-O-O-O-O-*
-*-O-O-O-O-O-O-*-
--*-O-O-O-O-O-*--
---*-O-O-O-O-*---
----*-*-*-*-*----
```

## Board rules (exact)

- Board of radius `r` = all hex cells at hex distance `<= r` from the centre cell.
  - Cells at distance exactly `r` form the **border ring**, printed `*`.
  - Cells at distance `<= r-1` are **board cells**, printed `O` (letter O, not zero).
  - So radius 3 has **4 cells per side** (r+1), radius 1 would be just a ring of 6 `*` around one `O`.
  - Total cells: `3r(r+1)+1`; border cells: `6r`; `O` cells: `3r(r-1)+1`.
- Layout ("pointy rows", rows are horizontal):
  - `2r+1` lines, every line exactly `4r+1` characters wide.
  - Line `i` (0-based, top to bottom): let `k = |i - r|`. It has `2r+1-k` cells.
  - Line = `k` dashes + the cells joined by single `-` + `k` dashes (padding on **both** sides).
  - Top line (i=0) and bottom line (i=2r) are all `*` (part of the border ring).
  - Every other line is `*` + `O`s + `*` (first and last cell are border).
  - Middle line (i=r) has no indentation: `*-O-...-O-*`, `2r+1` cells.
- `-` is only spacing; it is not a cell.
- Character-grid coordinates (useful for later levels): line `i`, cell `j` (0-based within the
  line) sits at column `c = k + 2j`. Cells occupy exactly the positions with
  `(c + i + r)` even; the six neighbours of the cell at `(i, c)` are `(i, c±2)` and `(i±1, c±1)`
  ("doubled" hex coordinates).

## Constraints seen in the data

| file | N | radii |
|---|---|---|
| example | 3 | 3, 6, 4 |
| 1-small | 10 | 3..9 |
| 2-large | 100 | 3..19 |

- Radii are positive integers (min seen 3, max seen 19); trivial size, no performance concern.

## Judging

- Level 1 has **no validator**: output must match the expected output **exactly** (characters,
  line breaks, the empty line between boards).
- The example output file ends with an extra trailing empty line; the accepted `solution.py`
  does not print it and still passes, so trailing whitespace/newlines are not significant.
- One output file per input file, uploaded to the contest platform; each input is all-or-nothing.

## Pitfalls / assumptions seen in solutions

- Don't forget the **trailing** dashes on each line (lines are symmetric, width `4r+1`).
- "Radius" counts the border ring: radius 3 → 7 lines, 4 border cells on each edge, not 3.
- Blank line goes only **between** boards, not after each one (accepted solution: separator
  before every board except the first).
- Read input with a whitespace-tolerant integer parser (`ints(text)`): N first, then N radii.
- No `# ASSUMPTION:` comments were needed in the accepted Level 1 solution.

## Accepted Level 1 core (for reference)

```python
def board(r):
    rows = []
    for i in range(2 * r + 1):
        k = abs(i - r)
        n = 2 * r + 1 - k
        cells = ['*'] * n if k == r else ['*'] + ['O'] * (n - 2) + ['*']
        rows.append('-' * k + '-'.join(cells) + '-' * k)
    return rows
```
