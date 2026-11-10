"""`python -m trading_bot.bot check`: tests every connection. Places no orders."""
import os, shutil, subprocess, sys
from .util import ROOT, HttpError


def line(ok, what, detail=""):
    mark = "OK  " if ok else ("SKIP" if ok is None else "FAIL")
    print(f"  [{mark}] {what}" + (f": {detail}" if detail else ""), flush=True)
    return ok


def run():
    print("\nAgent HQ paper-trading bot: connection check (no orders are placed)\n")
    bad = 0
    # Alpaca
    try:
        from .alpaca import Alpaca
        a = Alpaca()
        acct = a.account()
        line(True, "Alpaca PAPER account", f"equity ${float(acct['equity']):,.2f}, cash ${float(acct['cash']):,.2f}")
        line(True, "Market clock", "open now" if a.clock().get("is_open") else "closed now")
        p = a.latest_price("SPY")
        line(bool(p), "Stock prices (free IEX feed)", f"SPY ${p}")
        n = a.news(start="2026-01-01T00:00:00Z", limit=3, max_pages=1)
        line(bool(n), "Alpaca news", f"{len(n)} headlines")
    except SystemExit as e:
        bad += 1; line(False, "Alpaca", str(e))
    except HttpError as e:
        bad += 1; line(False, "Alpaca", f"{e} (check they are PAPER keys: laptop trading_bot/.env, server ~/.trading-bot.env)")
    # SEC (the halal screen reads company filings from the SEC; without it no company stock can be traded)
    try:
        from . import halal
        t = halal._sec("https://www.sec.gov/files/company_tickers.json")
        line(len(t) > 1000, "SEC filings (halal screen)", f"{len(t):,} companies listed")
    except HttpError as e:
        bad += 1; line(False, "SEC filings (halal screen)", halal._short(e) + " (coins + Shariah ETFs still trade)")
    # Gemini
    try:
        sys.path.insert(0, str(ROOT / "agents" / "gemini"))
        import gemini
        if not gemini.KEY:
            gemini.KEY = os.environ.get("GEMINI_API_KEY", "").strip()
        txt, _ = gemini.generate("Reply with the single word OK.", temperature=0)
        line("OK" in txt.upper(), "Gemini", gemini.model())
    except Exception as e:  # noqa: BLE001
        bad += 1; line(False, "Gemini", str(e)[:160])
    # TradingAgents
    try:
        import tradingagents  # noqa: F401
        line(True, "TradingAgents installed")
    except ImportError:
        bad += 1; line(False, "TradingAgents", "not installed: run setup.bat again")
    # Agent Reach
    from .news import reach_cmd
    cmd = reach_cmd()
    if not cmd:
        line(None, "Agent Reach (X/Reddit)", "not installed: bot will use news feeds only (run setup_x_reddit.bat)")
    else:
        for ch in ("twitter", "reddit"):
            r = subprocess.run([*cmd, "check", ch], capture_output=True, text=True, timeout=180)
            line(r.returncode == 0, f"Agent Reach {ch}", "logged in" if r.returncode == 0 else
                 f"run: agent-reach login {ch}   (sign in with your SECONDARY account)")
    # GitHub saving
    r = subprocess.run(["git", "-C", str(ROOT), "push", "--dry-run", "-q", "origin", "HEAD:main"], capture_output=True, text=True, timeout=90)
    if not line(r.returncode == 0, "Save results to GitHub", "" if r.returncode == 0 else r.stderr.strip()[:160]):
        bad += 1
    nxt = "Double-click start_trading_bot.bat to run it." if sys.platform == "win32" else "Start it with:  tb start"
    print(f"\nAll good. {nxt}\n" if not bad else f"\n{bad} problem(s) above to fix first.\n")
    return bad
