#!/usr/bin/env bash
# Every 3 days: Omar's Inspo inbox (Agent HQ -> YouTube -> Inspo) -> Gemini watches each video -> Engine 2 template
# -> test render -> judged against the inspo -> sample video on Agent HQ for Omar to approve. No Claude.
# Approved items go live in the next Bounce batch (run_bounce.sh runs inspo.py promote).
set -u
ENGINE=~/bounce-engine
HQ=~/agent-hq-bounce
export AGENT_HQ=$HQ TZ=America/Toronto BOUNCE_PY=~/bounce-venv/bin/python
PY=~/bounce-venv/bin/python
LOGDIR=~/logs; mkdir -p "$LOGDIR"
exec </dev/null >>"$LOGDIR/inspo-$(date +%F).log" 2>&1
set -a; . ~/.agent-hq.env; set +a
export GEMINI_API_KEY="${GEMINI_API_KEY_YOUTUBE:-${GEMINI_API_KEY_VIDEO:-$GEMINI_API_KEY}}"
exec 8>/tmp/bounce.lock; flock 8                     # never while the Bounce batch / auto template runs
echo "=== $(date '+%F %T') inspo ==="
$PY -m yt_dlp --version >/dev/null 2>&1 || $PY -m pip install -q yt-dlp
git -C "$HQ" fetch -q origin main && git -C "$HQ" reset -q --hard origin/main || exit 1
( flock 7; $PY "$(dirname "$0")/../../agents/gemini/inspo.py" run ) 7>/tmp/render.lock
for i in 1 2 3 4; do
  git -C "$HQ" add data/youtube
  git -C "$HQ" diff --cached --quiet && break
  git -C "$HQ" -c user.name="Agent HQ (server)" -c user.email="openclaw@users.noreply.github.com" commit -qm "Inspo inbox: samples ready for Omar (server, no Claude)"
  git -C "$HQ" pull -q --rebase origin main && git -C "$HQ" push -q origin HEAD:main && break
  git -C "$HQ" rebase --abort 2>/dev/null; sleep 10
done
rm -rf ~/inspo-work
echo "=== $(date '+%F %T') done ==="
