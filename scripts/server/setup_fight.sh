#!/usr/bin/env bash
# One-time setup for Fight & Court Intelligence on the Oracle server.
# 1. Get a FREE key at https://the-odds-api.com (Starter plan: 500 credits/month, no card).
# 2. On the server: bash ~/agent-hq/scripts/server/setup_fight.sh   (it asks for the key; nothing is echoed)
set -eu
cd ~/agent-hq && git pull -q
touch ~/.agent-hq.env && chmod 600 ~/.agent-hq.env
if grep -q '^ODDS_API_KEY=' ~/.agent-hq.env; then
  echo "ODDS_API_KEY is already set (edit ~/.agent-hq.env to change it)."
else
  read -rsp "Paste your Odds API key, then press Enter: " K; echo
  [ -n "$K" ] || { echo "No key entered, nothing changed."; exit 1; }
  printf 'ODDS_API_KEY=%s\n' "$K" >> ~/.agent-hq.env
  echo "Saved to ~/.agent-hq.env (only you can read it)."
fi
chmod +x scripts/server/run_fight.sh
crontab scripts/server/crontab.txt && echo "Schedule installed (crontab -l to see it)."
bash scripts/server/run_fight.sh check
bash scripts/server/run_fight.sh report && echo "Agent HQ updated: open the Fight & Court room."
