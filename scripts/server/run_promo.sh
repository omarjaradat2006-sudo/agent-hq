#!/usr/bin/env bash
# LinkedAI Promo Studio research: ONE small chunk per run (max 1 Gemini call), saved to ~/research/promo on this server.
# Cron runs it hourly 3:37-8:37 AM Toronto (after the Gemini daily quota resets). Nothing is pushed to git here:
# the Mon/Wed/Fri build (run_team.sh promo) puts the saved research together and saves it to Agent HQ.
set -u
REPO=~/agent-hq
LOGDIR=~/logs; mkdir -p "$LOGDIR" ~/research/promo
exec >>"$LOGDIR/$(date +%F).log" 2>&1
exec 9>/tmp/agenthq.lock; flock -w 1200 9 || { echo "promo chunk: another job held the lock for 20 min, skipping this hour"; exit 0; }
set -a; . ~/.agent-hq.env; set +a
[ -n "${GEMINI_API_KEY_PROMO:-}" ] && export GEMINI_API_KEY="$GEMINI_API_KEY_PROMO"
cd "$REPO" || exit 1
echo "=== $(date '+%F %T') promo research chunk ==="
git fetch -q origin main && git reset -q --hard origin/main
AGENT_JOB=promo-chunk python3 agents/gemini/promo_studio.py chunk || echo "!! promo chunk failed (will try the next chunk next hour)"
