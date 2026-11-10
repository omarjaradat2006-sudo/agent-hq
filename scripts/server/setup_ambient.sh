#!/usr/bin/env bash
# One-time setup of the Ambient Escape batch on the Oracle server. Run AFTER setup_bounce.sh has worked (it reuses its deploy key,
# Python venv and folders). Safe to run again: it skips what's already done.
#   bash ~/agent-hq/scripts/server/setup_ambient.sh
set -eu
[ -d ~/bounce-engine/.git ] || { echo "Run setup_bounce.sh first (it sets up the bounce-engine deploy key)."; exit 1; }
[ -d ~/ambient-engine/.git ] || git clone -q git@github-bounce:omarjaradat2006-sudo/bounce-engine.git ~/ambient-engine
echo "ambient-engine cloned."
[ -d ~/agent-hq-ambient/.git ] || git clone -q "$(git -C ~/agent-hq remote get-url origin)" ~/agent-hq-ambient
echo "agent-hq-ambient cloned."

# Explainer Shorts: cairo drawing + Kokoro voice (Apache-2.0). Arabic text shaping for the text Shorts.
sudo apt-get -qq update && sudo apt-get -qq install -y libcairo2-dev pkg-config python3-dev >/dev/null
~/bounce-venv/bin/pip -q install pycairo kokoro-onnx onnxruntime soundfile arabic-reshaper python-bidi
~/bounce-venv/bin/python -c "import cairo, kokoro_onnx, onnxruntime, arabic_reshaper, bidi; print('python packages ok')"
mkdir -p ~/ambient-data/kokoro ~/ambient-data/refs ~/ambient-data/work
for f in kokoro-v1.0.int8.onnx voices-v1.0.bin; do
  [ -s ~/ambient-data/kokoro/$f ] || curl -sfL -o ~/ambient-data/kokoro/$f "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/$f"
done
ls -la ~/ambient-data/kokoro

# Quran + hadith reference texts (cached; used to check every reference)
(cd ~/ambient-engine && AMBIENT_REFS=~/ambient-data/refs ~/bounce-venv/bin/python -c "
import sys; sys.path.insert(0, 'ambient'); import refs
print(refs.ayah(2, 153)['ref'], 'ok')
for c in ('bukhari', 'muslim', 'abudawud', 'tirmidhi', 'nasai', 'ibnmajah'): print(refs.hadith(c, 1)['ref'] if refs.hadith(c, 1).get('ref') else c, 'ok')")

if ls ~/yt-secrets/token_ambient.json ~/yt-secrets/client_secret_ambient.json >/dev/null 2>&1; then
  chmod 600 ~/yt-secrets/*; echo "YouTube secrets for Ambient Escape: present"
else
  echo "YouTube secrets for Ambient Escape: MISSING. Copy client_secret_ambient.json and token_ambient.json from the laptop"
  echo "into ~/yt-secrets yourself over SSH (scp), never through chat or git."
fi
crontab ~/agent-hq/scripts/server/crontab.txt && echo "crontab installed:" && crontab -l | grep -c run_
echo "Setup done. Next: bash ~/agent-hq/scripts/server/run_ambient.sh bench   then   run_ambient.sh noupload"
