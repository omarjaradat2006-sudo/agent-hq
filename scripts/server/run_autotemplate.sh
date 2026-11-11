#!/usr/bin/env bash
# Weekly (Saturday 1:17 PM): the best new Bounce Theory idea on the YouTube board becomes a real template, no Claude.
# Gemini writes it -> safety check -> test render -> saved in agent-hq data/youtube/auto_templates -> smoke-tested -> menu.
# Usage: run_autotemplate.sh            weekly run (cron)
#        run_autotemplate.sh <idea-id>  build this idea now
set -u
ENGINE=~/bounce-engine
HQ=~/agent-hq-bounce
export AGENT_HQ=$HQ BOUNCE_VERIFIED=~/bounce-data/verified.json TZ=America/Toronto
PY=~/bounce-venv/bin/python
LOGDIR=~/logs; mkdir -p "$LOGDIR"
exec </dev/null >>"$LOGDIR/autotemplate-$(date +%F).log" 2>&1
set -a; . ~/.agent-hq.env; set +a
export GEMINI_API_KEY="${GEMINI_API_KEY_YOUTUBE:-${GEMINI_API_KEY_VIDEO:-$GEMINI_API_KEY}}"
exec 8>/tmp/bounce.lock; flock 8                     # never while the Bounce batch runs (same engine + agent-hq clone)
echo "=== $(date '+%F %T') auto template ==="
git -C "$ENGINE" fetch -q origin main && git -C "$ENGINE" reset -q --hard origin/main || exit 1
git -C "$HQ" fetch -q origin main && git -C "$HQ" reset -q --hard origin/main || exit 1
( flock 7; $PY "$ENGINE/templates/autobuild.py" ${1:+--idea "$1"} ) 7>/tmp/render.lock
$PY "$ENGINE/templates/smoke.py" --missing                       # the new template must pass the same check as every other
$PY "$ENGINE/templates/catalog.py" menu "$HQ/data/youtube/bounce_templates.json" >/dev/null
for i in 1 2 3 4; do
  git -C "$HQ" add data/youtube
  git -C "$HQ" diff --cached --quiet && break
  git -C "$HQ" -c user.name="Agent HQ (server)" -c user.email="openclaw@users.noreply.github.com" commit -qm "Weekly auto template (server, no Claude)"
  git -C "$HQ" pull -q --rebase origin main && git -C "$HQ" push -q origin HEAD:main && break
  git -C "$HQ" rebase --abort 2>/dev/null; sleep 10
done
echo "=== $(date '+%F %T') done ==="
