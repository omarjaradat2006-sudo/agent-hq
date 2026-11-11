#!/usr/bin/env bash
# WANTED LEVEL (GTA 6 clips) on the Oracle server, no Claude. Cron runs it every hour at :07.
#   before Nov 19: only grows the clip-permission allow-list (nothing is posted)
#   from launch:   verify -> upload one Short (public) -> find CC BY / allowed Twitch clips -> make Shorts -> verify -> report
# Usage: run_wanted.sh            hourly run (cron)
#        run_wanted.sh selftest   offline test of the whole pipeline with fake data (nothing downloaded or uploaded)
#        run_wanted.sh test       END-TO-END test on GTA 5 footage, uploads PRIVATE, deletes files after YouTube confirms
#        run_wanted.sh status     what's ready / allowed
# Keys never live in git: token_wanted.json in ~/yt-secrets (copied by Omar over SSH); Gemini + Twitch keys in ~/.agent-hq.env.
set -u
MODE="${1:-hourly}"
ENGINE=~/wanted-engine
HQ=~/agent-hq-wanted
export AGENT_HQ=$HQ WANTED_DATA=~/wanted-data BOUNCE_SECRETS=~/yt-secrets TZ=America/Toronto
PY=~/bounce-venv/bin/python
export YTDLP=~/bounce-venv/bin/yt-dlp
LOGDIR=~/logs; mkdir -p "$LOGDIR"
exec </dev/null
[ "$MODE" = hourly ] && exec >>"$LOGDIR/wanted-$(date +%F).log" 2>&1
set -a; . ~/.agent-hq.env; set +a
exec 8>/tmp/wanted.lock; flock -n 8 || { echo "another WANTED LEVEL run is going; exiting"; exit 0; }
echo "=== $(date '+%F %T') WANTED LEVEL ($MODE) ==="

git -C "$ENGINE" fetch -q origin main && git -C "$ENGINE" reset -q --hard origin/main || { echo "!! engine git sync failed"; exit 1; }
git -C "$HQ" fetch -q origin main && git -C "$HQ" reset -q --hard origin/main || { echo "!! agent-hq git sync failed"; exit 1; }

[ "$MODE" = hourly ] && [ "$(date +%H)" = 04 ] && $PY -m pip -q install -U yt-dlp   # YouTube/Twitch change often: keep yt-dlp fresh daily
if [ "$MODE" = selftest ]; then $PY "$ENGINE/wanted/selftest.py" "${2:-}"; exit $?; fi

# Each Short's edit takes the shared render lock (/tmp/render.lock) so it never fights Bounce/Ambient for the CPU
(cd "$ENGINE/wanted" && $PY run.py "$MODE")
rc=$?

save_hq() {
  for i in 1 2 3 4; do
    git -C "$HQ" add data/youtube/wanted_report.json data/youtube/state.json 2>/dev/null
    git -C "$HQ" diff --cached --quiet && return 0
    git -C "$HQ" -c user.name="Agent HQ (server)" -c user.email="openclaw@users.noreply.github.com" commit -qm "$1"
    git -C "$HQ" pull -q --rebase origin main && git -C "$HQ" push -q origin HEAD:main && return 0
    git -C "$HQ" rebase --abort 2>/dev/null; sleep 10
  done
  echo "!! couldn't push to agent-hq"; return 1
}
[ "$MODE" != status ] && save_hq "WANTED LEVEL report ($MODE)"
df -h ~ | tail -1
echo "=== $(date '+%F %T') done (code $rc) ==="
find "$LOGDIR" -name 'wanted-*.log' -mtime +14 -delete
exit $rc
