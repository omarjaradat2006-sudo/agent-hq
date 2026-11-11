"""What would different entry rules have done THIS week? Replays the logged decisions against real past prices.

    python -m trading_bot.replay            (tb replay)

For every story the bot logged as "waiting" or "skipped", it re-checks the source rule, then price + volume
every 15 minutes while the story was fresh (same as live), then buys at the next bar and exits with the SAME
stop-loss -3% / target +6% / time limits / 5 positions / -3% day halt / -10% kill switch.
Not replayed: TradingAgents (it can still say no; max 5 checks a day), so treat the result as the most it could have done.
"""
import re, sys
from datetime import timedelta
from . import config as C
from .util import load_env, read_json, parse_time, now_utc, iso, DATA, ET
from .backtest import simulate, stats

SRC = re.compile(r"only \d+ source\(s\) so far: (.*)")


def stories(decisions, since):
    out = {}
    for d in sorted(decisions, key=lambda d: d["t"]):
        if d["outcome"] not in ("waiting", "skipped") or parse_time(d["t"]) < since:
            continue
        k = (d["symbol"], d.get("event") or "")
        x = out.setdefault(k, {"symbol": d["symbol"], "event": d.get("event") or "", "t0": d["t"], "pubs": None, "whys": []})
        x["whys"].append(d["why"])
        m = SRC.match(d["why"])
        if m:
            x["pubs"] = [p.strip() for p in m.group(1).split(",") if p.strip()]
    return list(out.values())


def events_for(rows, mode):
    R = C.confirm_rules(mode)
    ev = {}
    for i, x in enumerate(rows):
        if x["pubs"] is not None:            # it stopped at the source rule: would this mode accept the sources?
            pubs = set(x["pubs"])
            ok, _ = C.sources_ok(pubs, pubs - C.SOCIAL_PUBLISHERS, R)
            if not ok:
                continue
        ev[f"r{i}"] = {"key": f"r{i}", "summary": x["event"], "firstSeen": x["t0"], "confirmedAt": x["t0"],
                       "items": [{"time": x["t0"]}], "assets": {x["symbol"]: {"direction": "up", "confidence": 0.7}}}
    return ev


def run(days=None):
    load_env()
    from .alpaca import Alpaca
    a = Alpaca()
    led = read_json(DATA / "ledger.json", {}) or {}
    since = parse_time(led.get("startedAt")) or (now_utc() - timedelta(days=days or 7))
    if days:
        since = now_utc() - timedelta(days=days)
    rows = stories(led.get("decisions", []), since)
    print(f"\nReplay of {len(rows)} stories the bot logged since {since.astimezone(ET):%a %b %d %I:%M %p} ET "
          f"(paper, $100,000, same stop-loss / halt / kill switch)\n")
    res = {}
    for mode in ("strict", "loose", "any"):
        ev = events_for(rows, mode)
        trades, rules = simulate(a, ev, since, now_utc(), rules=C.confirm_rules(mode)) if ev else ([], {})
        s = stats(trades)
        res[mode] = (trades, s)
        label = {"strict": "STRICT (now: 2 sources, volume 1.5x)", "loose": "LOOSE (1 reputable source, volume 1.2x)",
                 "any": "ANY (1 news source of any kind, volume 1.2x)"}[mode]
        if not trades:
            print(f"{label}: 0 trades  ({len(ev)} stories passed the source rule)")
            continue
        print(f"{label}: {s['trades']} trades, {s['wins']} won ({s['winRate']}%), P&L ${s['totalPnl']:+,.2f} "
              f"({s['totalPct']:+.2f}%), worst drawdown {s['maxDrawdownPct']}%")
        for t in sorted(trades, key=lambda t: t["t"]):
            print(f"   {t['t'].astimezone(ET):%a %I:%M %p}  BUY {t['symbol']:<8} at {t['entry']:>10,.2f} -> "
                  f"{t['exitReason']:<26} {t['pnlPct']:+6.2f}%  ${t['pnl']:+9,.2f}   {t['event'][:60]}")
    print("\nNot replayed: TradingAgents (it may still say no, max 5 checks a day). Stop-loss -3%, 5% per trade,"
          " max 5 positions, -3% day halt and -10% kill switch were applied exactly as live.")
    print("Switch on:  tb rules loose   (or: tb rules any)      Switch back:  tb rules strict\n")
    return res


if __name__ == "__main__":
    a = sys.argv[1:]
    run(int(a[0]) if a and a[0].isdigit() else None)
