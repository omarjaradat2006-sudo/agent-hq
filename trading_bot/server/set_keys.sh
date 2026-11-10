#!/usr/bin/env bash
# Type the Alpaca PAPER keys into the server without them showing on screen, in chat, in shell history or in git.
#   bash ~/agent-hq-trading/trading_bot/server/set_keys.sh
# Saves them to ~/.trading-bot.env, readable only by you (chmod 600). The Gemini key is NOT asked for:
# the bot reuses the one the agent teams already have in ~/.agent-hq.env.
set -euo pipefail
F=~/.trading-bot.env
echo "Alpaca -> make sure the top-left switch says PAPER -> API Keys -> Generate."
echo "Paste each key and press Enter. Nothing will show while you paste: that's on purpose."
read -rsp "Alpaca PAPER API Key ID: " K; echo
read -rsp "Alpaca PAPER Secret Key: " S; echo
K="$(printf '%s' "$K" | tr -d '[:space:]')"; S="$(printf '%s' "$S" | tr -d '[:space:]')"
[ -n "$K" ] && [ -n "$S" ] || { echo "One of the keys was empty. Nothing saved."; exit 1; }
case "$K" in PK*) ;; AK*) echo "That key starts with AK = a LIVE key. This bot is paper only. Nothing saved."; exit 1;;
  *) echo "(Note: paper key IDs usually start with PK.)";; esac
umask 077
{ printf '# Alpaca PAPER keys for the trading bot. Never commit or share this file.\n'
  printf 'ALPACA_API_KEY=%s\n' "$K"
  printf 'ALPACA_SECRET_KEY=%s\n' "$S"; } > "$F"
chmod 600 "$F"
unset K S
echo "Saved to $F (only you can read it): $(stat -c '%A %U' "$F")"
grep -qE '^(export )?GEMINI_API_KEY=.+' ~/.agent-hq.env 2>/dev/null && echo "Gemini key: found in ~/.agent-hq.env" \
  || echo "Gemini key: NOT found in ~/.agent-hq.env (the agent teams' file). Tell Claude."
echo "Next:  ~/agent-hq-trading/trading_bot/server/tb check"
