#!/usr/bin/env bash
# LinkedAI Cheap Growth agent (Gemini free tier). Never posts, messages or spends anything.
#   run_cheap_growth.sh chunk     hourly Sat+Sun from 3:11 AM: research ONE topic, save to ~/research/cheap-growth (no git)
#   run_cheap_growth.sh assemble  Sunday 12:41 PM: saved research -> ranked weekly plan -> Agent HQ LinkedAI floor
# Uses GEMINI_API_KEY_GROWTH first if it exists in ~/.agent-hq.env, then the shared GEMINI_API_KEY.
set -u
REPO=~/agent-hq
LOGDIR=~/logs; mkdir -p "$LOGDIR"
exec >>"$LOGDIR/$(date +%F).log" 2>&1
set -a; . ~/.agent-hq.env; set +a
cd "$REPO" || exit 1
export AGENT_JOB="cheap-growth-${1:-chunk}"
KEYS="${GEMINI_API_KEY_GROWTH:-} $GEMINI_API_KEY"
echo "=== $(date '+%F %T') cheap growth ${1:-chunk} ==="

if [ "${1:-chunk}" = chunk ]; then
  # Chunks never touch git (another job may be mid-run in the repo), so they don't wait for the team lock.
  for K in $KEYS; do GEMINI_API_KEY="$K" python3 agents/gemini/cheap_growth.py chunk && exit 0; done
  exit 1
fi

exec 9>/tmp/agenthq.lock; flock -w 3600 9        # one git writer at a time
git fetch -q origin main && git reset -q --hard origin/main
OK=no
for K in $KEYS; do GEMINI_API_KEY="$K" python3 agents/gemini/cheap_growth.py assemble && { OK=yes; break; }; done
[ $OK = yes ] || { echo "!! cheap growth plan failed"; exit 1; }
for i in 1 2 3; do
  git fetch -q origin main && git reset -q --hard origin/main
  python3 agents/gemini/cheap_growth.py apply || exit 1
  git add data/linkedai
  git diff --cached --quiet && exit 0
  git -c user.name="Agent HQ (server)" -c user.email="openclaw@users.noreply.github.com" \
    commit -qm "Cheap Growth (Gemini, server): weekly plan" && git push -q origin HEAD:main && { echo "saved"; exit 0; }
  sleep 5
done
echo "!! cheap growth could not save"; exit 1
