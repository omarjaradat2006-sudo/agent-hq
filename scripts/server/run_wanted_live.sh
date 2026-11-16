#!/usr/bin/env bash
# WANTED LEVEL live watcher (systemd service "wanted-live" runs this; it restarts by itself if it stops).
# Watches allow-listed streamers live in GTA, reads their chat, clips chat spikes and uploads them within minutes.
# It exits when the engine code changes (the hourly run updates it) and systemd starts it again with the new code.
set -u
export AGENT_HQ=~/agent-hq-wanted WANTED_DATA=~/wanted-data BOUNCE_SECRETS=~/yt-secrets TZ=America/Toronto
export YTDLP=~/bounce-venv/bin/yt-dlp STREAMLINK=~/bounce-venv/bin/streamlink
set -a; . ~/.agent-hq.env; set +a
exec </dev/null
mkdir -p ~/logs
cd ~/wanted-engine/wanted && exec ~/bounce-venv/bin/python -u run.py live >>~/logs/wanted-live-$(date +%F).log 2>&1
