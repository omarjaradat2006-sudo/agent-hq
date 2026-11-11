#!/usr/bin/env bash
# Daily Ambient Escape batch on the Oracle server, no Claude:
#   lineup -> Gemini writes each video's spec -> refs checked against the Quran/hadith texts -> render -> upload (scheduled 5 PM-8 AM)
#   -> YouTube confirms each upload -> only then the video file is deleted -> mark Agent HQ -> clean temp files.
# Cron runs it at 7:20 AM Toronto (after the YouTube team at 6:13). Rendering waits for Bounce Theory's render (shared CPU lock).
# Usage: run_ambient.sh            full run
#        run_ambient.sh plan       plan only (Gemini specs + checks, job file + queue), no render/upload
#        run_ambient.sh noupload   plan + render + checks, stop before uploading (test videos are then deleted)
#        run_ambient.sh bench      time a reminder Short, an explainer Short and a 30-minute long on this server
# Keys never live in git: YouTube tokens in ~/yt-secrets (chmod 600, copied by Omar over SSH), Gemini key in ~/.agent-hq.env.
set -u
MODE="${1:-full}"
ENGINE=~/ambient-engine                   # its own bounce-engine checkout: Bounce's run resets ~/bounce-engine and its job files
HQ=~/agent-hq-ambient                     # its own agent-hq clone, so other runners' resets never touch it
export AGENT_HQ=$HQ
export BOUNCE_STUDIO=~/bounce-studio
export BOUNCE_LOGS=~/bounce-data/logs
export BOUNCE_UPLOADED=~/bounce-data/uploaded
export BOUNCE_SECRETS=~/yt-secrets
export BOUNCE_HEADLESS=1
export RENDER_WORK=~/ambient-data/work
export AMBIENT_REFS=~/ambient-data/refs
export KOKORO_DIR=~/ambient-data/kokoro
export TZ=America/Toronto
PY=~/bounce-venv/bin/python
OUTD="$BOUNCE_STUDIO/1 Ambient Escape - Upload Today"
LOGDIR=~/logs; mkdir -p "$LOGDIR" "$OUTD" "$BOUNCE_LOGS" "$BOUNCE_UPLOADED" "$RENDER_WORK"
LOG="$LOGDIR/ambient-$(date +%F).log"
exec </dev/null                                         # never let keystrokes reach ffmpeg
[ "$MODE" = full ] && exec >>"$LOG" 2>&1               # test modes print to the screen
set -a; . ~/.agent-hq.env; set +a                      # GEMINI_API_KEY
[ -n "${GEMINI_API_KEY_VIDEO:-}" ] && export GEMINI_API_KEY="$GEMINI_API_KEY_VIDEO"   # videos use their own key (own Google project) if set
export BOUNCE_WORKERS=${BOUNCE_WORKERS:-2}              # 2 at a time on the 2-OCPU server
exec 8>/tmp/ambient.lock; flock -n 8 || { echo "another Ambient run is going; exiting"; exit 0; }
echo "=== $(date '+%F %T') Ambient Escape batch ($MODE) ==="

sync_repos() {
  git -C "$ENGINE" fetch -q origin main && git -C "$ENGINE" reset -q --hard origin/main || return 1
  git -C "$HQ" fetch -q origin main && git -C "$HQ" reset -q --hard origin/main || return 1
}
save_hq() {   # commit data/youtube changes to agent-hq, retrying around the other runners' pushes
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
render() {    # one render at a time on the server (Bounce and Ambient share /tmp/render.lock)
  ( flock 7; cd "$ENGINE/Local Render" && $PY render.py ambient ) 7>/tmp/render.lock
}

if [ "$MODE" = full ] && ! [ -s ~/yt-secrets/token_ambient.json ]; then
  echo "!! ~/yt-secrets/token_ambient.json is missing: copy it from the laptop over SSH first. Nothing was made."; exit 2
fi
if [ "$MODE" = full ] && ! [ -f ~/ambient-data/tested ]; then
  echo "!! no supervised test yet: run  run_ambient.sh noupload  once first. Nothing was made."; exit 2
fi
sync_repos || { echo "!! git sync failed"; exit 1; }
[ -f "$BOUNCE_LOGS/AmbientEscape_uploaded_log.json" ] || cp "$ENGINE/Upload Tool/logs/AmbientEscape_"* "$BOUNCE_LOGS/"

if [ "$MODE" = bench ]; then
  ( flock 7; cd "$ENGINE" && $PY ambient/bench.py ) 7>/tmp/render.lock; exit $?
fi

# 0) Yesterday hit YouTube's daily limit? Upload what's left first (planning refuses to overwrite a non-empty queue)
$PY "$ENGINE/ambient/plan.py" --reconcile           # drop anything YouTube already has from the queue
if [ -s "$OUTD/queue.json" ] && [ "$(tr -d ' \n' < "$OUTD/queue.json")" != "[]" ] && [ "$MODE" = full ]; then
  echo "leftover queue from an earlier day: uploading it first"
  (cd "$ENGINE/Upload Tool" && $PY upload.py ambient --yes)
  $PY "$ENGINE/ambient/plan.py" --reconcile
  (cd "$ENGINE/Upload Tool" && $PY verify.py ambient)
fi

# 1) Plan. Exit 3 = today's lineup isn't there yet: wait for the YouTube team (until noon)
while :; do
  $PY "$ENGINE/ambient/plan.py"; rc=$?
  [ $rc -eq 0 ] && break
  if [ $rc -eq 3 ] && [ "$(date +%H)" -lt 12 ]; then echo "waiting 20 min for today's lineup"; sleep 1200; sync_repos; continue; fi
  echo "!! planning stopped (code $rc)"; exit $rc
done
if [ "$MODE" = plan ]; then
  cat "$OUTD/UPLOAD SHEET.txt"; rm -f "$OUTD/queue.json"; echo "plan only: nothing rendered"; exit 0
fi

# 2) Render (finished videos are skipped if this is re-run)
T0=$(date +%s); render; RENDER_OK=$([ $? -eq 0 ] && echo 1 || echo 0); MINS=$(( ($(date +%s) - T0) / 60 ))
echo "render took $MINS min (including any wait for Bounce Theory's render)"
if [ "$MODE" = noupload ]; then   # test run: report, then clear the test videos so the 7:20 run never uploads them
  for f in "$OUTD"/*.mp4; do [ -f "$f" ] && echo "  $(ffprobe -v error -show_entries format=duration:stream=width,height -of csv=p=0 "$f" | tr '\n' ' ') $(basename "$f")"; done
  cp "$OUTD/UPLOAD SHEET.txt" ~/logs/ambient-test-sheet.txt 2>/dev/null
  rm -f "$OUTD"/*.mp4 "$OUTD"/*.jpg "$OUTD"/queue.json; rm -rf "$RENDER_WORK"
  [ "$RENDER_OK" = 1 ] && date -Is > ~/ambient-data/tested    # the daily cron only runs after one good supervised test
  echo "noupload: test videos checked and deleted; nothing was uploaded (sheet kept in ~/logs/ambient-test-sheet.txt)"; exit 0
fi

# 3) Upload + schedule (5 PM - 8 AM window, one at a time). Broken/missing files are skipped by upload.py.
cd "$ENGINE/Upload Tool" && $PY upload.py ambient --yes
$PY "$ENGINE/ambient/plan.py" --reconcile           # queue.json keeps only what YouTube doesn't have yet

# 4) Delete each uploaded video ONLY after YouTube confirms it has it (anything unconfirmed is kept and reported)
cd "$ENGINE/Upload Tool" && $PY verify.py ambient

# 5) Mark Agent HQ, save history + report
git -C "$HQ" fetch -q origin main && git -C "$HQ" reset -q --hard origin/main
$PY "$ENGINE/ambient/mark.py" "$RENDER_OK" "$MINS" && save_hq "Ambient Escape batch made on the server (Gemini specs, no Claude)"

# 6) Temp files (clips, loop pieces, beds) only when nothing is left to upload
if [ "$(cat "$OUTD/queue.json" 2>/dev/null)" = "[]" ]; then
  cd "$ENGINE/Local Render" && $PY render.py clean --work-only --yes
fi
df -h ~ | tail -1
echo "=== $(date '+%F %T') done ==="
find "$LOGDIR" -name 'ambient-*.log' -mtime +30 -delete
