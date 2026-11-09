#!/usr/bin/env bash
# Move the bot to the Oracle server (Ubuntu). Run from the repo root:  bash trading_bot/server/install.sh
# Then copy trading_bot/.env from the laptop, and stop the laptop's autostart (remove_autostart.bat)
# so only one copy trades.
set -euo pipefail
cd "$(dirname "$0")/../.."
sudo apt-get update -y && sudo apt-get install -y python3 python3-venv git
python3 -m venv trading_bot/.venv
trading_bot/.venv/bin/pip install -q --upgrade pip
trading_bot/.venv/bin/pip install -q -r trading_bot/requirements.txt
[ -f trading_bot/.env ] || cp trading_bot/.env.example trading_bot/.env
# Move the laptop's trade history + settings over (they're in data/trading, already in git) and the
# private working memory if you have it: scp laptop:.../trading_bot/local/state.json trading_bot/local/
sed "s#__REPO__#$(pwd)#g; s#__USER__#$(whoami)#g" trading_bot/server/agenthq-trading.service | sudo tee /etc/systemd/system/agenthq-trading.service >/dev/null
sudo systemctl daemon-reload
sudo systemctl enable --now agenthq-trading
echo "Running. Logs: journalctl -u agenthq-trading -f   Check: trading_bot/.venv/bin/python -m trading_bot.bot check"
