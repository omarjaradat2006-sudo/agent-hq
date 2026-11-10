#!/usr/bin/env bash
# Fight & Court Intelligence on the Oracle server: research + recommendations only, never bets, never logs into a sportsbook.
# Usage: run_fight.sh picks nba | picks ufc | grade | report | check   (add --force to redo today's picks)
# Keys live in ~/.agent-hq.env (GEMINI_API_KEY, ODDS_API_KEY), never in git.
set -u
REPO=~/agent-hq
BACKUP=~/fight-backup               # last saved ledger, in case a push ever fails
LOGDIR=~/logs; mkdir -p "$LOGDIR" "$BACKUP"
LOG="$LOGDIR/$(date +%F).log"
[ "${1:-}" = check ] || exec >>"$LOG" 2>&1
exec 9>/tmp/agenthq.lock; flock 9          # one job at a time (shared with the teams)
set -a; . ~/.agent-hq.env; set +a
cd "$REPO" || exit 1
echo "=== $(date '+%F %T') fight $* ==="
git fetch -q origin main && git reset -q --hard origin/main

# If the last run saved locally but couldn't push, bring that newer ledger back.
python3 - "$BACKUP/ledger.json" data/fight/ledger.json <<'PY'
import json, shutil, sys
b, r = sys.argv[1], sys.argv[2]
ts = lambda p: (json.load(open(p)).get("savedAt") or "") if __import__("os").path.exists(p) else ""
if ts(b) > ts(r):
    shutil.copy(b, r); print("restored newer ledger from backup")
PY

python3 agents/fight/run.py "$@"; RC=$?
[ -f data/fight/ledger.json ] && cp data/fight/ledger.json "$BACKUP/ledger.json"
git add data/fight
if ! git diff --cached --quiet; then
  git -c user.name="Agent HQ (server)" -c user.email="openclaw@users.noreply.github.com" commit -qm "Fight & Court (server): $*"
  for i in 1 2 3; do
    git pull -q --rebase origin main && git push -q origin HEAD:main && { echo "saved"; break; }
    echo "push failed, retry $i"; sleep 5
  done
fi
echo "=== $(date '+%F %T') fight $* done (rc=$RC) ==="
exit $RC
