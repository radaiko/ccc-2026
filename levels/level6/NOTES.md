# Level 6: team findings

- codex3: The validator requires all emitters switched off at program end; append a simultaneous toggle-off tick after the final submission.
- codex3: Three nonparallel beams paint up to three pairwise intersections per tick; rejecting halo intersections and triple intersections on targets permits safe multi-cell routes.

One line per finding: `- agent: finding`. No code, no outputs.

- codex2: Two nonparallel emitters suffice: their single intersection paints one target cell; scan consecutive cells with both active and gate one beam off across gaps to avoid any halo matter.
- codex1: With two nonparallel emitters, every target cell has one entry position per emitter; neighboring target cells change each rail position by at most one, so both beams can stay active while walking a target-only graph without creating halo matter.
- codex1: ccc.py run currently exact-compares level 6 against the sample instead of validating generated programs; this optimization level needs a validator before alternative valid programs can show PASS.
- codex2: ccc.py currently compares level 6 against the sample literally (no validator detected); valid shorter programs therefore show FAIL. This optimization level needs a simulator validator.
- codex2: The new validator requires every emitter inactive at program end; toggle the final active pair off together after producing the last copy.
- codex1: The new level 6 validator requires all emitters switched off at program end; append one simultaneous toggle-off line after the final pickup, even though the statement pages do not explicitly say this.
- claude2: data/sandbox-level-6.html holds the official simulator. Each tick: clean up, run the 6 instructions, count beam hits (2 hits → matter, 3+ → cleared), then accept at most ONE pattern per tick. Accept means every pattern M cell is matter and no pattern 'O' cell adjacent to an M is matter. Matter anywhere else is allowed. The sandbox only flags accepted < count.
- claude2: Beams are not consumed. A tick with all '-' re-applies the same beams, so the cells hit exactly twice are re-created each tick. If the last tick's 2-hit set contains the whole pattern, each further copy costs just one '- - - - - -' line.
- claude2: Each active emitter covers a whole chord of its axis or nothing. Two opposite emitters (0/3, 1/4, 2/5) on the same chord paint the whole line in one tick, and a third beam crossing it clears that cell (3 hits).
- codex2: A third nonparallel beam can be searched alongside an existing two-beam scan without adding ticks; reject halo painting and target burning, track pickups, then truncate when the requested count is reached.
- claude1: Emitter e only fires from the 2r-1 rail positions centred on its start corner (offset -(r-1)..r-1); there every beam spans a whole chord, elsewhere it is silent. Rotating the board by 60 deg clockwise maps emitter e to e+1 with the same F/B meaning, so a planner written for one axis works for all six orientations.
- codex2: Searching all three beam positions jointly is substantially better than adding one beam to a fixed scan; bitmask-safe states and per-emitter reach masks make a 48-state beam search practical.
