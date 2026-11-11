#!/usr/bin/env bash
# Runs one Gemini team (or "all") on the Oracle server and saves the result to Agent HQ.
# Usage: run_team.sh <tiktok|youtube|linkedai|growth|upgrades|opps|lab|repos|chief|all>
# Keys live in ~/.agent-hq.env (chmod 600), never in git.
set -u
REPO=~/agent-hq
LOGDIR=~/logs; mkdir -p "$LOGDIR"
LOG="$LOGDIR/$(date +%F).log"
exec >>"$LOG" 2>&1
exec 9>/tmp/agenthq.lock; flock 9          # one team at a time
set -a; . ~/.agent-hq.env; set +a
cd "$REPO" || exit 1

[ "${1:-}" = all ] && LIST="tiktok youtube linkedai growth upgrades opps lab repos chief" || LIST="$1"
FAILED=""
for TEAM in $LIST; do
  echo "=== $(date '+%F %T') $TEAM ==="
  git fetch -q origin main && git reset -q --hard origin/main
  if [ "$TEAM" = tiktok ]; then CMD="python3 agents/gemini/tiktok_team.py"; else CMD="python3 agents/gemini/team.py $TEAM"; fi
  # The YouTube team plans both channels' daily lineups: it uses its own key (own Google project) first, then the shared key.
  KEYS="$GEMINI_API_KEY"
  [ "$TEAM" = youtube ] && [ -n "${GEMINI_API_KEY_YOUTUBE:-}" ] && KEYS="$GEMINI_API_KEY_YOUTUBE $GEMINI_API_KEY"
  OK=no
  for K in $KEYS; do
    [ "$K" != "$GEMINI_API_KEY" ] && echo "(using the YouTube team's own Gemini key)" || { [ "$KEYS" != "$GEMINI_API_KEY" ] && echo "(falling back to the shared Gemini key)"; }
    if GEMINI_API_KEY="$K" $CMD; then OK=yes; break; fi
  done
  if [ $OK = no ]; then echo "!! $TEAM failed"; FAILED="$FAILED $TEAM"; continue; fi
  SAVED=no
  for i in 1 2 3; do
    git fetch -q origin main && git reset -q --hard origin/main
    python3 agents/gemini/apply_patch.py "$TEAM" || break
    git add data
    if git diff --cached --quiet; then SAVED=yes; break; fi
    git -c user.name="Agent HQ (server)" -c user.email="openclaw@users.noreply.github.com" \
      commit -qm "$TEAM team (Gemini, server): daily work"
    git push -q origin HEAD:main && { SAVED=yes; break; }
    sleep 5
  done
  [ $SAVED = yes ] || { echo "!! $TEAM could not save"; FAILED="$FAILED $TEAM"; }
  if [ "$TEAM" = youtube ] && [ -n "${PEXELS_API_KEY:-}${PIXABAY_API_KEY:-}" ]; then
    git fetch -q origin main && git reset -q --hard origin/main
    python3 collectors/footage.py && python3 collectors/batch_brief.py && git add data/youtube && \
    { git diff --cached --quiet || { git -c user.name="Agent HQ (server)" -c user.email="openclaw@users.noreply.github.com" \
      commit -qm "Footage fetcher (server): clips for today's lineup" && git push -q origin HEAD:main; }; }
  fi
done
echo "=== $(date '+%F %T') done. Failed:${FAILED:- none} ==="
find "$LOGDIR" -name '*.log' -mtime +30 -delete
[ -z "$FAILED" ]
