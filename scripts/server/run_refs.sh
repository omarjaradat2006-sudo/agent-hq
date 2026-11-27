#!/usr/bin/env bash
# TikTok Viral references: ONE small research chunk (max 2 Gemini calls). Cron runs it every hour 3:52-8:52 AM,
# after the 3 AM Gemini quota reset. Results are saved on the server in ~/research/tiktok-refs/<date>/;
# the 9:41 TikTok team run puts them on the site (no extra Gemini calls). Zero Claude.
# Check today's progress by hand:  python3 ~/agent-hq/agents/gemini/viral_refs.py status
set -u
REPO=~/agent-hq
LOGDIR=~/logs; mkdir -p "$LOGDIR" ~/research/tiktok-refs
exec >>"$LOGDIR/$(date +%F).log" 2>&1
exec 9>/tmp/agenthq.lock; flock -w 1800 9 || { echo "refs: another job held the lock for 30 min, skipping this chunk"; exit 0; }
set -a; . ~/.agent-hq.env; set +a
cd "$REPO" || exit 1
git fetch -q origin main && git reset -q --hard origin/main     # latest code + any links Omar pasted on the site
export AGENT_JOB=refs
[ -n "${GEMINI_API_KEY_TIKTOK:-}" ] && export GEMINI_API_KEY="$GEMINI_API_KEY_TIKTOK"   # optional own key, like the other teams
[ -x ~/bounce-venv/bin/yt-dlp ] && export YTDLP=~/bounce-venv/bin/yt-dlp
[ "$(date +%H)" = 03 ] && [ -x ~/bounce-venv/bin/pip ] && ~/bounce-venv/bin/pip -q install -U yt-dlp   # TikTok changes often
echo "=== $(date '+%F %T') refs chunk ==="
python3 agents/gemini/viral_refs.py chunk || echo "!! refs chunk failed"
find ~/research/tiktok-refs -maxdepth 1 -type d -name '20*' -mtime +14 -exec rm -rf {} +   # keep 2 weeks of daily files
