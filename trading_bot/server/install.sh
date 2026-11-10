#!/usr/bin/env bash
# One-time install of the PAPER-trading bot on the Oracle server ("openclaw"). Safe to run again.
#   bash ~/agent-hq/trading_bot/server/install.sh
# What it does (nothing here trades or asks for keys):
#   1. makes the bot its own copy of agent-hq at ~/agent-hq-trading (the Gemini team runner hard-resets
#      ~/agent-hq every run, which would wipe the bot's unsaved trade history)
#   2. installs Python + the bot's packages (TradingAgents) into ~/agent-hq-trading/trading_bot/.venv
#   3. installs two systemd units: agenthq-trading.service (the bot, restarts on its own, starts at boot)
#      and agenthq-trading-report.timer (builds the 7-day report every evening at 4:45 PM New York time)
#   The bot is NOT started here. Next: set_keys.sh (hidden key entry), then tb check, then tb start.
set -euo pipefail
SRC=~/agent-hq
REPO=~/agent-hq-trading
echo "== 1/3  Bot's own copy of agent-hq: $REPO"
if [ ! -d "$REPO/.git" ]; then
  git clone -q "$(git -C "$SRC" remote get-url origin)" "$REPO"
else
  git -C "$REPO" pull -q --rebase origin main || true
fi
git -C "$REPO" config user.name "Agent HQ Trading Bot (server)"
git -C "$REPO" config user.email "openclaw@users.noreply.github.com"

echo "== 2/3  Python packages (a few minutes the first time)"
sudo apt-get -qq update
sudo apt-get -qq install -y python3 python3-venv python3-dev build-essential git >/dev/null
cd "$REPO"
[ -x trading_bot/.venv/bin/python ] || python3 -m venv trading_bot/.venv
trading_bot/.venv/bin/pip install -q --upgrade pip
trading_bot/.venv/bin/pip install -q -r trading_bot/requirements.txt
trading_bot/.venv/bin/python -c "import tradingagents; print('   TradingAgents installed')"
rm -f trading_bot/.env      # on the server the keys live in ~/.trading-bot.env (outside any git folder)
chmod +x trading_bot/server/tb trading_bot/server/set_keys.sh
mkdir -p ~/logs

echo "== 3/3  systemd units (installed + enabled at boot, NOT started)"
for u in agenthq-trading.service agenthq-trading-report.service agenthq-trading-report.timer; do
  sed "s#__REPO__#$REPO#g; s#__USER__#$(whoami)#g" "trading_bot/server/$u" | sudo tee "/etc/systemd/system/$u" >/dev/null
done
sudo systemctl daemon-reload
sudo systemctl enable agenthq-trading.service agenthq-trading-report.timer >/dev/null 2>&1
sudo systemctl start agenthq-trading-report.timer
echo
echo "Installed. Next:  bash $REPO/trading_bot/server/set_keys.sh"
