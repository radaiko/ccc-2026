#!/bin/bash
cd /home/user/ccc-2026
while [ "$(TZ=Europe/Vienna date +%H%M)" -lt 1849 ]; do
  sleep 150
  git pull -q --rebase 2>&1 | tail -1
  python3 /tmp/claude-0/-home-user-ccc-2026/18f3af6b-2f71-5cd5-b079-dca4afe470da/scratchpad/export.py | tail -n 1
  if [ -n "$(git status --porcelain levels/level6/output2)" ]; then
    git add levels/level6/output2 && git commit -qm "Level 6: output2 update (cloud agent)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_015ibdNE6L4gnzRThPnLA6wL" && git push -q origin level6-findings-astra-opus && echo pushed $(TZ=Europe/Vienna date +%H:%M)
  fi
done
