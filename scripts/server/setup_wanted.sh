#!/usr/bin/env bash
# One-time setup of WANTED LEVEL (GTA 6 clips) on the Oracle server. Run AFTER setup_bounce.sh has worked (reuses its deploy key,
# Python venv and ~/yt-secrets). Safe to run again: it skips what's already done.
#   bash ~/agent-hq/scripts/server/setup_wanted.sh
set -eu
[ -d ~/bounce-engine/.git ] || { echo "Run setup_bounce.sh first (it sets up the bounce-engine deploy key)."; exit 1; }
[ -d ~/wanted-engine/.git ] || git clone -q git@github-bounce:omarjaradat2006-sudo/bounce-engine.git ~/wanted-engine
git -C ~/wanted-engine pull -q
[ -d ~/agent-hq-wanted/.git ] || git clone -q "$(git -C ~/agent-hq remote get-url origin)" ~/agent-hq-wanted
echo "code: ok"

sudo apt-get -qq update && sudo apt-get -qq install -y ffmpeg fonts-dejavu-core >/dev/null
~/bounce-venv/bin/pip -q install -U yt-dlp faster-whisper
mkdir -p ~/wanted-data/models ~/logs
~/bounce-venv/bin/python -c "
from faster_whisper import WhisperModel
WhisperModel('base.en', device='cpu', compute_type='int8', download_root='$HOME/wanted-data/models'); print('captions model: ok')"

# Twitch app keys (free, from dev.twitch.tv). Typed here, hidden; saved only in ~/.agent-hq.env (chmod 600).
if ! grep -q '^TWITCH_CLIENT_SECRET=' ~/.agent-hq.env 2>/dev/null; then
  echo; echo "Paste the Twitch Client ID, then press Enter:"; read -r TID
  echo "Paste the Twitch Client Secret (nothing will show), then press Enter:"; read -rs TSEC; echo
  printf 'TWITCH_CLIENT_ID=%s\nTWITCH_CLIENT_SECRET=%s\n' "$TID" "$TSEC" >> ~/.agent-hq.env; chmod 600 ~/.agent-hq.env
fi
set -a; . ~/.agent-hq.env; set +a
curl -sf -X POST "https://id.twitch.tv/oauth2/token" -d "client_id=$TWITCH_CLIENT_ID&client_secret=$TWITCH_CLIENT_SECRET&grant_type=client_credentials" >/dev/null \
  && echo "Twitch keys: ok" || echo "Twitch keys: WRONG. Remove the two TWITCH_ lines from ~/.agent-hq.env (nano ~/.agent-hq.env) and run this again."

if [ -s ~/yt-secrets/token_wanted.json ] && [ -s ~/yt-secrets/client_secret_bounce.json ]; then
  chmod 600 ~/yt-secrets/*; echo "YouTube login for WANTED LEVEL: present"
else
  echo "YouTube login for WANTED LEVEL: MISSING. Copy token_wanted.json into ~/yt-secrets yourself over SSH (scp), never through chat or git."
fi

echo "Offline self-test (fake data, about 2 min):"
bash ~/agent-hq/scripts/server/run_wanted.sh selftest | tail -3
crontab ~/agent-hq/scripts/server/crontab.txt && echo "crontab installed:" && crontab -l | grep -c run_
echo "Setup done. Next: bash ~/agent-hq/scripts/server/run_wanted.sh test"
