#!/usr/bin/env bash
# Daily Bounce Theory batch on the Oracle server, no Claude: lineup -> templates -> render -> check -> upload -> mark Agent HQ -> clean.
# Cron runs it at 7:05 AM Toronto. If the YouTube team hasn't planned today yet, it waits and retries until noon.
# Usage: run_bounce.sh            full run
#        run_bounce.sh plan       plan only (job file + queue), no render/upload (for checking)
#        run_bounce.sh noupload   plan + render + checks, stop before uploading
# Keys never live in git: YouTube tokens in ~/yt-secrets (chmod 600), Gemini key in ~/.agent-hq.env.
set -u
MODE="${1:-full}"
ENGINE=~/bounce-engine
HQ=~/agent-hq-bounce                      # its own agent-hq clone, so the Gemini team runner's resets never touch it
export AGENT_HQ=$HQ
export BOUNCE_STUDIO=~/bounce-studio
export BOUNCE_LOGS=~/bounce-data/logs
export BOUNCE_UPLOADED=~/bounce-data/uploaded
export BOUNCE_SECRETS=~/yt-secrets
export BOUNCE_HEADLESS=1
export BOUNCE_VERIFIED=~/bounce-data/verified.json
export TZ=America/Toronto
PY=~/bounce-venv/bin/python
LOGDIR=~/logs; mkdir -p "$LOGDIR" "$BOUNCE_STUDIO" "$BOUNCE_LOGS" "$BOUNCE_UPLOADED"
LOG="$LOGDIR/bounce-$(date +%F).log"
[ "$MODE" = full ] && exec >>"$LOG" 2>&1 </dev/null    # test modes print to the screen
exec 8>/tmp/bounce.lock; flock -n 8 || { echo "another Bounce run is going; exiting"; exit 0; }
echo "=== $(date '+%F %T') Bounce Theory batch ($MODE) ==="

sync_repos() {
  git -C "$ENGINE" fetch -q origin main && git -C "$ENGINE" reset -q --hard origin/main || return 1
  git -C "$HQ" fetch -q origin main && git -C "$HQ" reset -q --hard origin/main || return 1
}
save_hq() {   # commit data/youtube changes to agent-hq, retrying around the Gemini teams' pushes
  local msg="$1"
  for i in 1 2 3 4; do
    git -C "$HQ" add data/youtube
    git -C "$HQ" diff --cached --quiet && return 0
    git -C "$HQ" -c user.name="Agent HQ (server)" -c user.email="openclaw@users.noreply.github.com" commit -qm "$msg"
    git -C "$HQ" pull -q --rebase origin main && git -C "$HQ" push -q origin HEAD:main && return 0
    git -C "$HQ" rebase --abort 2>/dev/null; sleep 10
  done
  echo "!! couldn't push to agent-hq"; return 1
}

sync_repos || { echo "!! git sync failed"; exit 1; }
# First run on this server: start from the laptop's upload log, so nothing already uploaded is remade
[ -f "$BOUNCE_LOGS/BounceTheory_uploaded_log.json" ] || cp "$ENGINE/Upload Tool/logs/"* "$BOUNCE_LOGS/"

# New formats since the last run? Smoke-test just those (a few minutes)
$PY "$ENGINE/templates/smoke.py" --missing </dev/null

# Publish the template menu for the YouTube team (only when it changed)
$PY "$ENGINE/templates/catalog.py" menu "$HQ/data/youtube/bounce_templates.json" >/dev/null && save_hq "Bounce template menu (server)"

# 0) Yesterday hit YouTube's daily limit? Upload what's left first (planning refuses to overwrite a non-empty queue)
Q="$BOUNCE_STUDIO/2 Bounce Theory - Upload Today/queue.json"
if [ -s "$Q" ] && [ "$(tr -d ' \n' < "$Q")" != "[]" ] && [ "$MODE" = full ]; then
  echo "leftover queue from an earlier day: uploading it first"
  (cd "$ENGINE/Upload Tool" && $PY upload.py bounce --yes)
fi

# 1) Plan. Exit 3 = today's lineup isn't there yet: wait for the YouTube team (until noon)
while :; do
  $PY "$ENGINE/templates/daily.py"; rc=$?
  [ $rc -eq 0 ] && break
  if [ $rc -eq 3 ] && [ "$(date +%H)" -lt 12 ]; then echo "waiting 20 min for today's lineup"; sleep 1200; sync_repos; continue; fi
  echo "!! planning stopped (code $rc)"; exit $rc
done
[ "$MODE" = plan ] && { rm -f "$BOUNCE_STUDIO/2 Bounce Theory - Upload Today/queue.json"; echo "plan only: nothing rendered"; exit 0; }

# 2) Render (finished videos are skipped if this is re-run)
cd "$ENGINE/Local Render" && $PY render.py bounce; RENDER_OK=$([ $? -eq 0 ] && echo 1 || echo 0)
if [ "$MODE" = noupload ]; then   # test run: report, then clear the test videos so the 7 AM run never uploads them
  OUTD="$BOUNCE_STUDIO/2 Bounce Theory - Upload Today"
  for f in "$OUTD"/*.mp4; do [ -f "$f" ] && echo "  $(ffprobe -v error -show_entries format=duration:stream=width,height -of csv=p=0 "$f" | tr '\n' ' ') $(basename "$f")"; done
  rm -f "$OUTD"/*.mp4 "$OUTD"/*.jpg "$OUTD"/queue.json; rm -rf "$ENGINE/Local Render/work"
  echo "noupload: test videos checked and deleted; nothing was uploaded"; exit 0
fi

# 3) Upload + schedule (5 PM - 8 AM window, one at a time). Broken/missing files are skipped by upload.py.
cd "$ENGINE/Upload Tool" && $PY upload.py bounce --yes

# 4) Mark Agent HQ, save history + report
sync_repos >/dev/null 2>&1 || git -C "$HQ" pull -q --rebase origin main
$PY "$ENGINE/templates/mark.py" "$RENDER_OK" && save_hq "Bounce Theory batch made on the server (templates, no Claude)"

# 5) Clean up only when everything uploaded (anything still in queue.json is never deleted)
if [ "$(cat "$BOUNCE_STUDIO/2 Bounce Theory - Upload Today/queue.json" 2>/dev/null)" = "[]" ]; then
  cd "$ENGINE/Local Render" && $PY render.py clean --yes
  rm -rf "$BOUNCE_UPLOADED/2 Bounce Theory - Upload Today"
fi
df -h ~ | tail -1
echo "=== $(date '+%F %T') done ==="
find "$LOGDIR" -name 'bounce-*.log' -mtime +30 -delete
