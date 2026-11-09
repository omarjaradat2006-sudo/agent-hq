#!/usr/bin/env bash
# One-time setup of the Bounce Theory batch on the Oracle server. Safe to run again: it skips what's already done.
#   bash ~/agent-hq/scripts/server/setup_bounce.sh
# Step 1 makes a read-only deploy key for the private bounce-engine repo and prints its PUBLIC half for GitHub.
set -eu
KEY=~/.ssh/bounce_engine
if [ ! -f "$KEY" ]; then
  ssh-keygen -q -t ed25519 -N "" -C "openclaw bounce-engine (read-only)" -f "$KEY"
fi
if ! grep -q "Host github-bounce" ~/.ssh/config 2>/dev/null; then
  printf '\nHost github-bounce\n  HostName github.com\n  User git\n  IdentityFile ~/.ssh/bounce_engine\n  IdentitiesOnly yes\n' >> ~/.ssh/config
  chmod 600 ~/.ssh/config
fi
if [ ! -d ~/bounce-engine/.git ]; then
  if ! git clone -q git@github-bounce:omarjaradat2006-sudo/bounce-engine.git ~/bounce-engine 2>/dev/null; then
    echo
    echo "Add this PUBLIC key on GitHub: bounce-engine -> Settings -> Deploy keys -> Add deploy key"
    echo "Title: openclaw server   ·   leave 'Allow write access' UNTICKED"
    echo
    cat "$KEY.pub"
    echo
    echo "Then run this script again."
    exit 0
  fi
fi
echo "bounce-engine cloned."
[ -d ~/agent-hq-bounce/.git ] || git clone -q "$(git -C ~/agent-hq remote get-url origin)" ~/agent-hq-bounce
echo "agent-hq-bounce cloned."

sudo apt-get -qq update && sudo apt-get -qq install -y ffmpeg python3-venv >/dev/null
[ -x ~/bounce-venv/bin/python ] || python3 -m venv ~/bounce-venv
~/bounce-venv/bin/pip -q install --upgrade pip
~/bounce-venv/bin/pip -q install numpy opencv-python-headless pillow scipy soundfile pymunk google-api-python-client google-auth-oauthlib
~/bounce-venv/bin/python -c "import numpy, cv2, PIL, scipy, googleapiclient; print('python packages ok')"
ffmpeg -version | head -1

mkdir -p ~/logs ~/yt-secrets ~/bounce-studio ~/bounce-data/logs ~/bounce-data/uploaded && chmod 700 ~/yt-secrets
if ls ~/yt-secrets/token_bounce.json ~/yt-secrets/client_secret_bounce.json >/dev/null 2>&1; then
  chmod 600 ~/yt-secrets/*; echo "YouTube secrets: present"
else
  echo "YouTube secrets: MISSING. Copy client_secret_bounce.json and token_bounce.json from the laptop into ~/yt-secrets (see SETUP note)."
fi

# Template smoke test on this machine (ARM): only templates that pass here are used
if [ ! -f ~/bounce-data/verified.json ]; then
  echo "Smoke-testing every template on this server (about 20-30 min) ..."
  (cd ~/bounce-engine && BOUNCE_VERIFIED=~/bounce-data/verified.json SMOKE_WORKERS=3 ~/bounce-venv/bin/python templates/smoke.py </dev/null > ~/logs/smoke.log 2>&1; tail -1 ~/logs/smoke.log)
fi
crontab ~/agent-hq/scripts/server/crontab.txt && echo "crontab installed:" && crontab -l | grep -c run_
echo "Setup done."
