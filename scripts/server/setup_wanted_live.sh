#!/usr/bin/env bash
# One-time: install the WANTED LEVEL live watcher as an always-on service. Safe to run again.
set -e
~/bounce-venv/bin/pip -q install -U streamlink
git -C ~/wanted-engine fetch -q origin main && git -C ~/wanted-engine reset -q --hard origin/main
sudo tee /etc/systemd/system/wanted-live.service >/dev/null <<UNIT
[Unit]
Description=WANTED LEVEL live watcher (clips chat spikes from allow-listed Twitch streamers)
After=network-online.target
Wants=network-online.target

[Service]
User=$USER
ExecStart=/bin/bash $HOME/agent-hq/scripts/server/run_wanted_live.sh
Restart=always
RestartSec=20
Nice=5

[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl daemon-reload
sudo systemctl enable --now wanted-live
sleep 3
systemctl is-active wanted-live && echo "Live watcher is running. Log: ~/logs/wanted-live-$(date +%F).log"
