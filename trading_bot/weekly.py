"""7-day paper-test report.

    python -m trading_bot.weekly              build the report (and save it to GitHub)
    python -m trading_bot.weekly --no-push    build it, don't save to GitHub
    python -m trading_bot.weekly --start 2026-11-10T14:30:00Z   pick the start of the week yourself

The week starts at the bot's first run (ledger "startedAt") unless you set it. The server runs this
every evening, so the Trading tab shows "Day N of 7" while the test runs and the FINAL report after.
Writes data/trading/report_7d.json (Trading tab) and data/trading/report_7d.md (readable on GitHub).

Contents: trades, win rate, realised + open P&L, account change vs SPY, max drawdown,
every risk-rule trigger (grouped + full timeline), every error, and how often the bot restarted.
"""
import sys
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from . import config as C
from .util import load_env, read_json, write_json, iso, now_utc, parse_time, read_events, DATA, HttpError

DAYS = 7
LEDGER = DATA / "ledger.json"
OUT_JSON = DATA / "report_7d.json"
OUT_MD = DATA / "report_7d.md"

RULE_LABELS = {
    "stop_loss_-3%": "Stop-loss -3% (on Alpaca's side)", "take_profit_+6%": "Take-profit +6%",
    "stock_3_day_limit": "Stock 3-trading-day limit", "crypto_48h_limit": "Crypto 48h limit",
    "bad_news_exit": "Sold on bad news", "kill_switch": "Kill switch -10% (sold all, locked)",
    "kill_switch_exit": "Closed by the kill switch", "daily_loss_halt": "Daily -3% halt (no new trades)",
    "max_5_positions": "Max 5 open positions", "one_position_per_asset": "Already holding that asset",
    "cash_only_no_margin": "Cash only, no margin (not enough cash)", "stock_entry_window": "Stock entry window (first 10 / last 30 min)",
    "no_stop_loss_possible": "Couldn't place a stop-loss, so sold", "alpaca_account_blocked": "Alpaca account blocked",
    "halal_screen": "Halal screen blocked the asset", "tradingagents_daily_cap": "TradingAgents 5-a-day cap",
    "tradingagents_said_no": "TradingAgents said no", "closed_outside_bot": "Closed outside the bot",
}


def drawdown(points):
    """Max peak-to-trough drop, as a % (negative), from [(t, equity)] in time order."""
    peak, worst, at = None, 0.0, None
    for t, v in points:
        if v is None:
            continue
        peak = v if peak is None else max(peak, v)
        dd = (v - peak) / peak if peak else 0.0
        if dd < worst:
            worst, at = dd, t
    return round(worst * 100, 2), at


def group(evts):
    g = OrderedDict()
    for e in evts:
        x = g.setdefault(e["rule"], {"rule": e["rule"], "label": RULE_LABELS.get(e["rule"], e["rule"].replace("_", " ")),
                                     "kind": e["kind"], "count": 0, "symbols": [], "first": e["t"], "last": e["t"],
                                     "example": e["msg"]})
        x["count"] += 1
        x["last"] = e["t"]
        if e.get("symbol") and e["symbol"] not in x["symbols"]:
            x["symbols"].append(e["symbol"])
    return sorted(g.values(), key=lambda x: -x["count"])


def squash(evts):
    """Timeline with back-to-back repeats (same rule, symbol, message) folded into one line with a count."""
    out = []
    for e in evts:
        if out and (out[-1]["rule"], out[-1].get("symbol"), out[-1]["msg"]) == (e["rule"], e.get("symbol"), e["msg"]):
            out[-1]["times"] += 1
            out[-1]["lastT"] = e["t"]
        else:
            out.append({**e, "times": 1, "lastT": e["t"]})
    return out


def build(alpaca=None, start=None, now=None):
    now = now or now_utc()
    led = read_json(LEDGER, {}) or {}
    start = parse_time(start or (led.get("paperTest") or {}).get("start") or led.get("startedAt"))
    if not start:
        return {"status": "not_started", "updatedAt": iso(now),
                "note": "The bot hasn't made its first run yet, so the 7-day test hasn't started."}
    end = start + timedelta(days=DAYS)
    stop = min(now, end)
    final = now >= end
    in_win = lambda t: t and start <= parse_time(t) <= stop

    trades = [t for t in led.get("trades", []) if t.get("status") != "cancelled" and in_win(t.get("openedAt"))]
    closed = [t for t in trades if t.get("status") == "closed" and in_win(t.get("closedAt"))]
    still_open = [t for t in trades if t.get("status") in ("open", "pending")]
    wins = [t for t in closed if (t.get("pnl") or 0) > 0]
    losses = [t for t in closed if (t.get("pnl") or 0) <= 0]
    by_exit = {}
    for t in closed:
        by_exit[t.get("exitReason", "?")] = by_exit.get(t.get("exitReason", "?"), 0) + 1

    # equity curve: Alpaca's own 15-minute history if we can get it, plus the bot's 30-minute samples
    pts = [(parse_time(p["t"]), p.get("equity")) for p in led.get("equity", []) if in_win(p.get("t"))]
    spy = [p.get("spy") for p in led.get("equity", []) if in_win(p.get("t")) and p.get("spy")]
    source = "bot (every 30 min)"
    if alpaca is not None:
        try:
            h = alpaca.get("/v2/account/portfolio/history", {"timeframe": "15Min", "extended_hours": "true",
                                                              "start": iso(start), "end": iso(stop)})
            hp = [(datetime.fromtimestamp(ts, tz=timezone.utc), float(v))
                  for ts, v in zip(h.get("timestamp") or [], h.get("equity") or []) if v]
            hp = [x for x in hp if start <= x[0] <= stop]
            if len(hp) > 3:
                pts = sorted(pts + hp, key=lambda x: x[0])
                source = "Alpaca 15-min history + bot samples"
        except (HttpError, AttributeError, TypeError, ValueError):
            pass
    pts.sort(key=lambda x: x[0])
    start_eq = led.get("startEquity") or (pts[0][1] if pts else None)
    end_eq = pts[-1][1] if pts else start_eq
    if alpaca is not None and not final:
        try:
            end_eq = float(alpaca.account()["equity"])
        except (HttpError, KeyError, TypeError, ValueError):
            pass
    dd, dd_at = drawdown(([(start, start_eq)] if start_eq else []) + pts)
    spy_pct = round((spy[-1] - led["spyStart"]) / led["spyStart"] * 100, 2) if spy and led.get("spyStart") else None
    total_pct = round((end_eq - start_eq) / start_eq * 100, 2) if start_eq and end_eq else None

    evts = [e for e in read_events() if in_win(e.get("t"))]
    risk = [e for e in evts if e["kind"] in ("risk", "halal", "limit", "ai")]
    errors = [e for e in evts if e["kind"] == "error"]
    restarts = sum(1 for e in evts if e["rule"] == "bot_started")

    rep = {
        "status": "final" if final else "running", "updatedAt": iso(now), "mode": "PAPER",
        "from": iso(start), "to": iso(end), "day": min(DAYS, (stop - start).days + 1), "days": DAYS,
        "trades": {"opened": len(trades), "closed": len(closed), "open": len(still_open), "wins": len(wins),
                   "losses": len(losses), "winRate": round(len(wins) / len(closed) * 100, 1) if closed else None,
                   "realizedPnl": round(sum(t.get("pnl") or 0 for t in closed), 2),
                   "avgPct": round(sum(t.get("pnlPct") or 0 for t in closed) / len(closed), 2) if closed else None,
                   "avgWinPct": round(sum(t["pnlPct"] for t in wins) / len(wins), 2) if wins else None,
                   "avgLossPct": round(sum(t["pnlPct"] for t in losses) / len(losses), 2) if losses else None,
                   "best": max(closed, key=lambda t: t["pnlPct"], default=None) and
                           {k: max(closed, key=lambda t: t["pnlPct"]).get(k) for k in ("symbol", "pnlPct", "pnl")},
                   "worst": min(closed, key=lambda t: t["pnlPct"], default=None) and
                            {k: min(closed, key=lambda t: t["pnlPct"]).get(k) for k in ("symbol", "pnlPct", "pnl")},
                   "byExit": by_exit},
        "account": {"startEquity": start_eq, "endEquity": round(end_eq, 2) if end_eq else None,
                    "pnl": round(end_eq - start_eq, 2) if start_eq and end_eq else None, "pnlPct": total_pct,
                    "spyPct": spy_pct, "vsSpyPct": round(total_pct - spy_pct, 2) if total_pct is not None and spy_pct is not None else None,
                    "maxDrawdownPct": dd, "maxDrawdownAt": iso(dd_at) if dd_at else None, "curveSource": source,
                    "openPnl": round(sum(((t.get("lastPrice") or t["entryPrice"]) - t["entryPrice"]) * (t.get("qty") or 0)
                                         for t in still_open if t.get("entryPrice")), 2)},
        "riskRules": group(risk), "riskTimeline": squash(risk)[-400:],
        "errors": group(errors), "errorTimeline": squash(errors)[-200:],
        "restarts": restarts, "killSwitch": bool(led.get("killed")),
        "tradeList": [{k: t.get(k) for k in ("symbol", "openedAt", "closedAt", "entryPrice", "exitPrice", "qty", "pnl",
                                              "pnlPct", "exitReason", "status")} | {"news": (t.get("news") or {}).get("summary")}
                      for t in sorted(trades, key=lambda t: t["openedAt"])],
        "limits": {"risk": dict(C.RISK)},
        "caveats": ["One week is a very small sample: a few lucky or unlucky trades can swing every number here.",
                    "Paper fills are kinder than real ones (no partial fills, little slippage).",
                    "Use this together with the 6-12 month backtest before deciding anything about real money."],
    }
    return rep


def markdown(r):
    if r.get("status") == "not_started":
        return "# 7-day paper test\n\n" + r["note"] + "\n"
    t, a = r["trades"], r["account"]
    f = lambda v, s="": "—" if v is None else f"{v:+.2f}{s}" if isinstance(v, float) else f"{v}{s}"
    L = [f"# 7-day paper test: {'FINAL' if r['status'] == 'final' else 'day %d of %d (running)' % (r['day'], r['days'])}",
         "", f"PAPER account only. {r['from'][:16].replace('T', ' ')} UTC to {r['to'][:16].replace('T', ' ')} UTC. Updated {r['updatedAt'][:16].replace('T', ' ')} UTC.", "",
         "## Results", "", "| | |", "|---|---|",
         f"| Trades opened / closed / still open | {t['opened']} / {t['closed']} / {t['open']} |",
         f"| Win rate | {'—' if t['winRate'] is None else str(t['winRate']) + '%'} ({t['wins']} won, {t['losses']} lost) |",
         f"| Realised P&L | ${t['realizedPnl']:+,.2f} (avg trade {f(t['avgPct'], '%')}, avg win {f(t['avgWinPct'], '%')}, avg loss {f(t['avgLossPct'], '%')}) |",
         f"| Account change | {'—' if a['pnl'] is None else '$%+.2f' % a['pnl']} ({f(a['pnlPct'], '%')}) vs SPY {f(a['spyPct'], '%')} |",
         f"| Open positions P&L | ${a['openPnl']:+,.2f} |",
         f"| Max drawdown | {f(a['maxDrawdownPct'], '%')} ({a['curveSource']}) |",
         f"| Kill switch | {'ON' if r['killSwitch'] else 'off'} |",
         f"| Bot (re)starts | {r['restarts']} |", ""]
    if t["byExit"]:
        L += ["How trades ended: " + ", ".join(f"{k} x{v}" for k, v in t["byExit"].items()), ""]
    L += ["## Every risk-rule trigger", ""]
    if not r["riskRules"]:
        L += ["None in this window.", ""]
    else:
        L += ["| Rule | Times | Assets | First | Last |", "|---|---|---|---|---|"]
        L += [f"| {g['label']} | {g['count']} | {', '.join(g['symbols'][:8]) or '—'} | {g['first'][:16]} | {g['last'][:16]} |" for g in r["riskRules"]]
        L += ["", "Timeline (repeats in a row folded together):", ""]
        L += [f"- {e['t'][:16].replace('T', ' ')} {RULE_LABELS.get(e['rule'], e['rule'])}{' ' + e['symbol'] if e.get('symbol') else ''}: "
              f"{e['msg']}{' (x%d, until %s)' % (e['times'], e['lastT'][:16].replace('T', ' ')) if e['times'] > 1 else ''}"
              for e in r["riskTimeline"]]
        L += [""]
    L += ["## Errors", ""]
    if not r["errors"]:
        L += ["None in this window.", ""]
    else:
        L += [f"- **{g['rule']}** x{g['count']} (last {g['last'][:16]}): {g['example']}" for g in r["errors"]]
        L += [""]
    L += ["## Trades", ""]
    if not r["tradeList"]:
        L += ["No trades in this window.", ""]
    else:
        L += ["| Asset | Opened (UTC) | Entry | Exit | P&L | Why it ended | News |", "|---|---|---|---|---|---|---|"]
        L += [f"| {x['symbol']} | {(x['openedAt'] or '')[:16]} | {x['entryPrice']} | {x['exitPrice'] or '—'} | "
              f"{'—' if x['pnlPct'] is None else '%+.2f%%' % x['pnlPct']} | {x['exitReason'] or x['status']} | {(x['news'] or '')[:90]} |"
              for x in r["tradeList"]]
        L += [""]
    L += ["## Read this before trusting it", ""] + [f"- {c}" for c in r["caveats"]]
    return "\n".join(L) + "\n"


def run(push=True, start=None):
    load_env()
    a = None
    try:
        from .alpaca import Alpaca
        a = Alpaca()
    except SystemExit:
        a = None
    if start:
        led = read_json(LEDGER, {}) or {}
        led["paperTest"] = {"start": iso(parse_time(start)), "days": DAYS}
        write_json(LEDGER, led)
    r = build(a, start=start)
    write_json(OUT_JSON, r)
    OUT_MD.write_text(markdown(r), encoding="utf-8")
    if push:
        from . import publish
        publish.push(f"Trading bot: 7-day paper report ({r.get('status')}, day {r.get('day', 0)})")
    return r


if __name__ == "__main__":
    args = sys.argv[1:]
    st = args[args.index("--start") + 1] if "--start" in args else None
    r = run(push="--no-push" not in args, start=st)
    print(OUT_MD.read_text(encoding="utf-8"))
