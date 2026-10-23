# Instructions for agents: CCC 2026 team knowledge repo

This repo collects what our team has learned so far in the **Cloudflight Coding Contest
2026**: the rules of every level played, the accepted solution of each level, and the
findings behind them. Levels build on each other and each new statement usually only
describes what *changed*, so this repo is how you get the full picture before you start
the next level.

Most of it is written automatically by the team's AI race runner (ccc) the moment a level
is solved. Humans add findings by hand.

## The goal

The contest is a race through levels of one growing puzzle. A level counts once its
outputs for all inputs are accepted, and teams are ranked by how many levels they solve
and how fast. Wrong uploads cost time. So:

- **Correct beats clever.** A plain solution that is right on every input wins over an
  elegant one that is wrong on one.
- **Never start from zero.** Everything the team already knows is here. Use it so you only
  have to solve what is new in the level.
- **Help the team.** Your human races in parallel with the team's AI agents. What you find
  out (a tricky rule, an edge case, an approach that was too slow) is worth sharing in
  `FINDINGS.md`, even mid-level.

## What to do on each level

1. `git pull --rebase` to get the latest rules and solutions.
2. Read this repo as described in *How to read it* below: `RULES.md`, then the latest
   `solution.py`.
3. Read the new statement (your human gives you the zip or the text) and work out exactly
   what changed compared to `RULES.md`. Say it in a few lines before you write code.
4. Copy the previous level's `solution.py` to `levels/levelN/candidates/<your-name>.py`
   and extend it. Keep the parsing and output format unless the statement changes them.
5. Run it until the example shows `PASS` and **every** input finishes within the time
   limit (see *Running a solution*). Never special-case the example.
6. Tell your human which files to upload (`levels/levelN/runs/<your-name>/`) and what the
   approach is in one line.
7. Add anything non-obvious to `levels/levelN/FINDINGS.md`, then commit and push
   `FINDINGS.md` and your candidate.

If the statement is ambiguous, pick the reading that matches the example, mark it with an
`# ASSUMPTION:` comment and tell your human. If two readings both fit the example and give
different outputs, ask instead of guessing.

## Layout

```
RULES.md                      complete current rules, input/output formats and pitfalls of ALL levels so far
ccc.py                        runner: runs levels/levelN/solution.py against the inputs (stdlib only)
levels/_template/solution.py  starting point when there is no earlier solution
common/                       helpers the solutions import (`from common import *`): lines, ints, Grid, bfs, dijkstra, ...
levels/levelN/
  problem.md                  the statement of level N (text extracted from the PDF; tables may be scrambled)
  solution.py                 the ACCEPTED solution of level N: defines solve(text) -> str | list of lines
  NOTES.md                    one-line findings the AI agents wrote while solving it (optional)
  validator.py                checks any-valid-answer levels: check(input, output) (optional)
  data/                       the example input and its expected output only (big inputs are not committed)
  FINDINGS.md                 hand-written findings by teammates (optional, never overwritten by ccc)
  candidates/<name>.py        teammates' own solutions (optional, never overwritten by ccc)
```

Everything except `FINDINGS.md`, `candidates/`, `README.md`, `AGENTS.md` and `CLAUDE.md`
is written by ccc and overwritten on the next sync. Never commit changes to those files.
Put corrections in `FINDINGS.md`.

## How to read it before working on level N

1. **`RULES.md` first.** It is the single source of truth for the rules up to the latest
   solved level. Read it completely.
2. Find the latest solved level: the highest `levels/levelK/` that has a `solution.py`.
3. Read `levels/levelK/solution.py`. Level N almost always extends it; start from a copy.
   Keep its structure, parsing and output formatting unless the new statement changes them.
4. Skim `FINDINGS.md` and `NOTES.md` of the last one or two levels for pitfalls (edge
   cases, wrong readings of the statement that cost time, performance traps).
5. Only if `RULES.md` leaves something open, read the earlier `problem.md` files.
6. Then read the new level's statement and inputs, which your human gives you.

Don't read every level's files up front: `RULES.md` plus the latest solution is usually
enough. Go further back only for a specific question.

## Running a solution

The runner expects the contest zip's files in `levels/levelN/data/`
(`in_level-N_*.txt` and `out_level-N_0-example.txt`):

```bash
python3 ccc.py unpack ~/Downloads/level5.zip 5   # extracts into levels/level5/data/ (creates the level)
python3 ccc.py run 5                             # example first (diff on mismatch), then every input
python3 ccc.py zip 5                             # source zip for upload, in submissions/
```

Write your code in `levels/levelN/candidates/<your-name>.py` (start from a copy of the
previous level's `solution.py`) and run it with `python3 ccc.py run N --solution <your-name>`.
Outputs go to `levels/levelN/out/` (or `runs/<your-name>/` with `--solution`, both
gitignored); upload those. The contest judges with PyPy and about 5 minutes of CPU per
input: big inputs need the right algorithm. `ccc.py run` uses PyPy when it is installed.
Use only the Python standard library.

## Contributing back

- Write what you or your human learned into `levels/levelN/FINDINGS.md`: short bullets,
  facts only (a rule that was easy to misread, an edge case in the inputs, an approach
  that was too slow). No full outputs.
- Commit your `candidates/<your-name>.py` if you want to share it.
- `ccc.py unpack` also creates `problem.md`, `solution.py` and the example files of a new
  level. Never commit those. If a later `git pull` refuses because they would be
  overwritten, delete them: ccc's versions are the accepted ones.
- Pull before you start (`git pull --rebase`); ccc pushes several times per level.
