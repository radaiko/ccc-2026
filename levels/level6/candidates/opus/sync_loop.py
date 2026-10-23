"""Periodic sync: fetch origin (report new teammate commits/notes), merge + verify all results into
levels/level6/output/ (total.py), commit + push to level6-findings-astra-opus when the total changed.
Prints one line per event (for a Monitor). Usage: python3 sync_loop.py [interval_seconds] [report_step]"""
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
interval = int(sys.argv[1]) if len(sys.argv) > 1 else 300
step = int(sys.argv[2]) if len(sys.argv) > 2 else 200


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=600, **kw)


def total():
    out = sh([sys.executable, 'total.py'], cwd=HERE).stdout
    t = [l for l in out.splitlines() if l.startswith('TOTAL')]
    return int(t[0].split()[1]) if t else None, out


seen_remote = sh(['git', '-C', str(REPO), 'rev-parse', 'origin/main']).stdout.strip()
last_commit_total, _ = total()
last_reported = int(sys.argv[3]) if len(sys.argv) > 3 else last_commit_total
print('SYNC start total %s' % last_commit_total, flush=True)
while True:
    time.sleep(interval)
    try:
        sh(['git', '-C', str(REPO), 'fetch', '-q', 'origin'])
        head = sh(['git', '-C', str(REPO), 'rev-parse', 'origin/main']).stdout.strip()
        if head and head != seen_remote:
            log = sh(['git', '-C', str(REPO), 'log', '--format=%h %s', '%s..%s' % (seen_remote, head)]).stdout
            notes = sh(['git', '-C', str(REPO), 'diff', seen_remote, head, '--', 'levels/level6/NOTES.md',
                        'levels/level6/FINDINGS.md']).stdout
            added = [l[1:].strip() for l in notes.splitlines() if l.startswith('+') and not l.startswith('+++')
                     and l[1:].strip()]
            print('REMOTE %d new commit(s): %s | new notes: %s' % (
                len(log.splitlines()), '; '.join(log.splitlines()[:3]), ' || '.join(added)[:1500]), flush=True)
            seen_remote = head
        t, out = total()
        # commit every round (no-op when nothing changed): code and findings get pushed too
        msg = 'Level 6: merged total %d (auto-sync)' % t if t != last_commit_total else 'Level 6: code/findings (auto-sync)'
        r = sh([str(HERE / 'commit_progress.sh'), msg], cwd=HERE)
        if 'FAILED' in r.stdout:
            print('PUSH FAILED at total %s' % t, flush=True)
        last_commit_total = t
        if t is not None and last_reported - t >= step:
            parts = ', '.join(l for l in out.splitlines() if l[:1].isdigit())
            print('TOTAL %d (%s) %s' % (t, parts, r.stdout.strip()), flush=True)
            last_reported = t
    except Exception as e:  # keep the loop alive
        print('SYNC error %r' % e, flush=True)
