"""Run by systemd before the bot starts: refuse to start unless the bot points at Alpaca's PAPER account.
The live URL is never used anywhere; this is a second lock on the door."""
import sys
from . import config as C

PAPER = "https://paper-api.alpaca.markets"

if __name__ == "__main__":
    if C.ALPACA_TRADING_URL != PAPER:
        sys.exit(f"REFUSING TO START: trading URL is {C.ALPACA_TRADING_URL}, not the paper URL.")
    from .util import load_env
    import os
    load_env()
    if os.environ.get("ALPACA_API_KEY", "").startswith("AK"):
        sys.exit("REFUSING TO START: ALPACA_API_KEY looks like a LIVE key (starts with AK). Paper keys only.")
    print("paper guard: OK (Alpaca paper account only)")
