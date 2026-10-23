#!/bin/bash
# Commit opus code, findings and the current upload outputs to branch level6-findings-astra-opus and push.
# Usage: commit_progress.sh "message"   (safe to call concurrently: serialized by a lock)
set -e
SRC=/Users/laurenzwurdinger/Documents/dev/CodingContest/ccc-2026
WT=/private/tmp/claude-501/-Users-laurenzwurdinger-Documents-dev-CodingContest/5e9e1394-2f05-4762-ad31-a81358130714/scratchpad/wt
python3 - "$1" <<'PY'
import fcntl, subprocess, sys, shutil, glob, os
src = '/Users/laurenzwurdinger/Documents/dev/CodingContest/ccc-2026'
wt = '/private/tmp/claude-501/-Users-laurenzwurdinger-Documents-dev-CodingContest/5e9e1394-2f05-4762-ad31-a81358130714/scratchpad/wt'
msg = sys.argv[1] if len(sys.argv) > 1 else 'Level 6 opus progress'
with open(os.path.join(wt, '..', '.commit.pylock'), 'w') as lock:
    fcntl.flock(lock, fcntl.LOCK_EX)
    os.makedirs(os.path.join(wt, 'levels/level6/candidates/opus'), exist_ok=True)
    os.makedirs(os.path.join(wt, 'levels/level6/output'), exist_ok=True)
    for f in glob.glob(os.path.join(src, 'levels/level6/candidates/opus/*')):
        if f.endswith(('.cpp', '.py', '.sh', '.md', '.h')):
            shutil.copy(f, os.path.join(wt, 'levels/level6/candidates/opus/'))
    os.makedirs(os.path.join(wt, 'levels/level6/candidates/opus/tools'), exist_ok=True)
    for f in glob.glob(os.path.join(src, 'levels/level6/candidates/opus/tools/*')):
        shutil.copy(f, os.path.join(wt, 'levels/level6/candidates/opus/tools/'))
    for f in ['levels/level6/findings_opus.md', 'levels/level6/findigs_astra.md']:
        if os.path.exists(os.path.join(src, f)):
            shutil.copy(os.path.join(src, f), os.path.join(wt, f))
    for f in glob.glob(os.path.join(src, 'levels/level6/output/out_level-6_*.txt')):
        shutil.copy(f, os.path.join(wt, 'levels/level6/output/'))
    subprocess.run(['git', '-C', wt, 'add', '-A', 'levels/level6'], check=True)
    if subprocess.run(['git', '-C', wt, 'diff', '--cached', '--quiet']).returncode == 0:
        print('nothing to commit'); sys.exit(0)
    subprocess.run(['git', '-C', wt, 'commit', '-q', '-m', msg + '\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'], check=True)
    pr = subprocess.run(['git', '-C', wt, 'pull', '-q', '--rebase', 'origin', 'level6-findings-astra-opus'])
    if pr.returncode != 0:
        # never leave the worktree stuck mid-rebase: abort and fall back to a merge (findings merge as union)
        subprocess.run(['git', '-C', wt, 'rebase', '--abort'])
        mr = subprocess.run(['git', '-C', wt, 'pull', '-q', '--no-rebase', '--no-edit', 'origin', 'level6-findings-astra-opus'])
        if mr.returncode != 0:
            subprocess.run(['git', '-C', wt, 'merge', '--abort'])
            print('commit ok, PUSH FAILED (merge conflict with remote)'); sys.exit(0)
    r = subprocess.run(['git', '-C', wt, 'push', '-q', 'origin', 'HEAD:level6-findings-astra-opus'])
    print('committed and pushed' if r.returncode == 0 else 'commit ok, PUSH FAILED')
PY
