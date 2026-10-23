# CCC 2026: team knowledge

Shared state of our team in the Cloudflight Coding Contest 2026: the rules of every level
so far, each level's accepted solution, and the findings behind them. It is filled
automatically by our AI race runner (ccc) whenever a level is solved, so it's always at
the latest solved level.

**For teammates who prompt by hand:** point your agent (Claude Code, Codex, Cursor, ...) at
this repo. `AGENTS.md` (and `CLAUDE.md`, which includes it) tells it how to read the repo,
so it starts every level knowing all the rules and solutions of the levels before.

```bash
git pull --rebase          # before every level
```

A good first prompt for a new level:

> Read AGENTS.md and follow it. Then solve level N: statement and inputs are in
> levels/levelN/ (I unpacked the zip with `python3 ccc.py unpack`).

Add your own insights to `levels/levelN/FINDINGS.md` and push them; ccc never touches that file.
See `AGENTS.md` for the layout.
