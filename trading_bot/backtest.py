"""Backtest: Omar's rules over the last N days of real past news (Alpaca/Benzinga archive) and prices.

    python -m trading_bot.backtest            last 30 days
    python -m trading_bot.backtest 45         last 45 days

What it does
  - Gemini triages the past headlines with the same playbook (cached, so re-runs are free)
  - same confirmation rules, risk limits, stop/target, hold limits, position cap and sizing
  - TradingAgents re-checks the top 10 trades on their historical date, to see whether its
    approvals picked the better trades (running it on every trade would blow the free tier)
Honest limits (also shown on the dashboard)
  - the archive has one publisher (Benzinga), so "2 independent sources" = 2 separate articles
  - no past X/Reddit posts exist to replay
  - fills are simulated at the next bar's open; if a bar touches both stop and target we assume the stop
"""
import json, sys
from datetime import timedelta
from . import config as C
from .util import load_env, read_json, write_json, iso, now_utc, parse_time, log, DATA, LOCAL, ET

CACHE = LOCAL / "backtest_cache.json"


def fetch_news(a, symbols, start, end, per_day=150):
    seen, out = set(), []
    chunks = [symbols[i:i + 40] for i in range(0, len(symbols), 40)] + [None]
    for ch in chunks:
        for n in a.news(start=iso(start), end=iso(end), symbols=ch, limit=50, max_pages=80):
            if n["id"] in seen:
                continue
            seen.add(n["id"])
            out.append({"id": f"bz{n['id']}", "publisher": "Benzinga", "kind": "news", "title": n.get("headline", ""),
                        "summary": (n.get("summary") or "")[:200], "url": n.get("url"), "time": n["created_at"],
                        "symbols": n.get("symbols") or []})
    by_day = {}
    for n in sorted(out, key=lambda n: (len(n["symbols"]) or 99, n["time"])):
        d = n["time"][:10]
        if len(by_day.setdefault(d, [])) < per_day:
            by_day[d].append(n)
    return sorted([n for v in by_day.values() for n in v], key=lambda n: n["time"])


def triage_all(items, universe):
    from .triage import triage
    cache = read_json(CACHE, {}) or {}
    events = {}
    for i in range(0, len(items), 70):
        batch = items[i:i + 70]
        key = batch[0]["id"] + "-" + batch[-1]["id"] + f"-{len(batch)}"
        if key not in cache:
            cache[key] = triage(batch, {}, universe, [])
            write_json(CACHE, cache)
        by_id = {b["id"]: b for b in batch}
        for ev in cache[key]:
            if not ev.get("is_market_news", True):
                continue
            its = sorted([by_id[x] for x in ev.get("item_ids") or [] if x in by_id], key=lambda x: x["time"])
            if not its:
                continue
            e = events.setdefault(ev["key"], {"key": ev["key"], "summary": ev.get("summary", ""), "items": [], "assets": {}})
            e["items"].extend(its)
            for a in ev.get("assets") or []:
                e["assets"][a["symbol"]] = a
    for e in events.values():
        e["items"].sort(key=lambda x: x["time"])
        e["firstSeen"] = e["items"][0]["time"]
        # proxy for "2 independent sources": the second separate article about the story
        e["confirmedAt"] = e["items"][1]["time"] if len(e["items"]) >= 2 else None
    return events


def simulate(a, events, start, end):
    from .market import confirm
    from .alpaca import Alpaca  # noqa: F401
    syms = sorted({s for e in events.values() for s, x in e["assets"].items()})
    stocks = [s for s in syms if "/" not in s]
    crypto = [s for s in syms if "/" in s]
    bars = {}
    for i in range(0, len(stocks), 20):
        bars.update(a.stock_bars(stocks[i:i + 20], "5Min", iso(start - timedelta(days=15)), iso(end)))
    if crypto:
        bars.update(a.crypto_bars(crypto, "15Min", iso(start - timedelta(days=8)), iso(end)))
    for s in bars:
        bars[s].sort(key=lambda b: b["t"])

    cands = []
    for e in events.values():
        if not e.get("confirmedAt"):
            continue
        for sym, x in e["assets"].items():
            if x["direction"] != "up" or x.get("confidence", 0) < C.CONFIRM["min_confidence"] or sym not in bars:
                continue
            t0 = parse_time(e["confirmedAt"])
            for k in range(0, C.CONFIRM["event_fresh_hours"] * 4):     # check every 15 minutes while fresh
                t = t0 + timedelta(minutes=15 * k)
                if "/" not in sym:
                    et = t.astimezone(ET)
                    if et.weekday() >= 5 or not ((et.hour, et.minute) >= (9, 40) and (et.hour, et.minute) <= (15, 30)):
                        continue
                past = [b for b in bars[sym] if parse_time(b["t"]) <= t]
                chk = confirm(None, sym, "up", e["firstSeen"], now=t, bars=past)
                if chk["passed"]:
                    nxt = next((b for b in bars[sym] if parse_time(b["t"]) > t), None)
                    if nxt:
                        cands.append({"t": nxt["t"], "symbol": sym, "entry": float(nxt["o"]), "event": e["summary"],
                                      "confidence": x["confidence"], "why": x.get("why", ""), "check": chk["reason"],
                                      "rvol": chk["rvol"], "score": x["confidence"] * min(chk["rvol"] / 1.5, 2)})
                    break
                if "too late" in chk.get("reason", ""):
                    break
    cands.sort(key=lambda c: c["t"])

    downs = sorted([(e["items"][0]["time"], s) for e in events.values() for s, x in e["assets"].items()
                    if x["direction"] == "down" and x.get("confidence", 0) >= C.CONFIRM["sell_min_confidence"]])
    equity, cash, open_, trades, halted_day = 100000.0, 100000.0, [], [], None
    for c in cands:
        t = parse_time(c["t"])
        for o in list(open_):          # close anything that ended before this entry
            if parse_time(o["exitT"]) <= t:
                open_.remove(o); cash += o["qty"] * o["exit"]
        if len(open_) >= C.RISK["max_open_positions"] or any(o["symbol"] == c["symbol"] for o in open_):
            continue
        day = t.astimezone(ET).date()
        day_pnl = sum(x["pnl"] for x in trades if parse_time(x["exitT"]).astimezone(ET).date() == day)
        if halted_day == day or day_pnl <= -C.RISK["daily_loss_halt_pct"] * equity:
            halted_day = day
            continue
        budget = min(equity * C.RISK["max_pct_per_trade"], cash)
        qty = budget / c["entry"] if "/" in c["symbol"] else int(budget // c["entry"])
        if qty <= 0:
            continue
        ex = exit_for(c, bars[c["symbol"]], downs)
        tr = {**c, **ex, "qty": qty, "pnl": round((ex["exit"] - c["entry"]) * qty, 2),
              "pnlPct": round((ex["exit"] - c["entry"]) / c["entry"] * 100, 2)}
        cash -= qty * c["entry"]
        open_.append(tr); trades.append(tr)
        equity += tr["pnl"]   # booked at exit; fine for a sequential summary
    return trades, bars


def exit_for(c, bars, downs):
    stop, target = c["entry"] * (1 - C.RISK["stop_loss_pct"]), c["entry"] * (1 + C.RISK["take_profit_pct"])
    t0 = parse_time(c["t"])
    crypto = "/" in c["symbol"]
    days_seen, last_day = 0, t0.astimezone(ET).date()
    bad = [parse_time(t) for t, s in downs if s == c["symbol"] and parse_time(t) > t0]
    for b in bars:
        bt = parse_time(b["t"])
        if bt <= t0:
            continue
        if bad and bt >= bad[0]:
            return {"exit": float(b["o"]), "exitT": b["t"], "exitReason": "bad news"}
        if float(b["l"]) <= stop:
            return {"exit": min(stop, float(b["o"])), "exitT": b["t"], "exitReason": "stop-loss -3%"}
        if float(b["h"]) >= target:
            return {"exit": max(target, float(b["o"])) if float(b["o"]) > target else target, "exitT": b["t"], "exitReason": "target +6%"}
        if crypto:
            if bt - t0 >= timedelta(hours=C.RISK["crypto_max_hold_hours"]):
                return {"exit": float(b["c"]), "exitT": b["t"], "exitReason": "48h limit"}
        else:
            d = bt.astimezone(ET).date()
            if d != last_day:
                days_seen, last_day = days_seen + 1, d
            et = bt.astimezone(ET)
            if days_seen >= C.RISK["stock_max_hold_trading_days"] and (et.hour, et.minute) >= (15, 45):
                return {"exit": float(b["c"]), "exitT": b["t"], "exitReason": "3 trading-day limit"}
    last = bars[-1]
    return {"exit": float(last["c"]), "exitT": last["t"], "exitReason": "still open at end of test"}


def stats(trades):
    if not trades:
        return {"trades": 0}
    wins = [t for t in trades if t["pnl"] > 0]
    curve, peak, dd, eq = [], 100000.0, 0.0, 100000.0
    for t in sorted(trades, key=lambda t: t["exitT"]):
        eq += t["pnl"]; peak = max(peak, eq); dd = min(dd, (eq - peak) / peak)
        curve.append({"t": t["exitT"], "equity": round(eq, 2)})
    return {"trades": len(trades), "wins": len(wins), "winRate": round(len(wins) / len(trades) * 100, 1),
            "totalPnl": round(sum(t["pnl"] for t in trades), 2), "totalPct": round((eq - 100000) / 1000, 2),
            "avgPct": round(sum(t["pnlPct"] for t in trades) / len(trades), 2), "maxDrawdownPct": round(dd * 100, 2),
            "curve": curve,
            "byExit": {r: sum(1 for t in trades if t["exitReason"] == r) for r in sorted({t["exitReason"] for t in trades})}}


def run(days=30, ta_sample=10):
    load_env()
    from .alpaca import Alpaca
    from . import halal, deep
    a = Alpaca()
    end = now_utc() - timedelta(minutes=20)
    start = end - timedelta(days=days)
    uni = halal.build_universe(a)
    syms = list((uni.get("stocks") or {}).keys())
    log(f"Backtest: fetching {days} days of past news for {len(syms)} halal stocks + crypto", "Backtester")
    items = fetch_news(a, syms + [c.replace("/", "") for c in (uni.get("crypto") or {})], start, end)
    log(f"Backtest: {len(items)} headlines, triaging with Gemini (cached after the first run)", "Backtester")
    events = triage_all(items, uni)
    trades, _ = simulate(a, events, start, end)
    s = stats(trades)
    spy = a.stock_bars(["SPY"], "1Day", iso(start - timedelta(days=4)), iso(end)).get("SPY", [])
    spy_pct = round((float(spy[-1]["c"]) - float(spy[0]["c"])) / float(spy[0]["c"]) * 100, 2) if len(spy) > 1 else None
    # TradingAgents on the strongest trades, at their historical date
    ta = []
    for t in sorted(trades, key=lambda t: t["score"], reverse=True)[:ta_sample]:
        v = deep.run(t["symbol"], trade_date=parse_time(t["t"]).astimezone(ET).date().isoformat(), context=t["event"])
        t["tradingAgents"] = v.get("rating")
        ta.append(t)
    appr = [t for t in ta if t.get("tradingAgents") in C.DEEP["approve_ratings"]]
    rej = [t for t in ta if t.get("tradingAgents") not in C.DEEP["approve_ratings"]]
    avg = lambda xs: round(sum(x["pnlPct"] for x in xs) / len(xs), 2) if xs else None
    out = {"ranAt": iso(), "days": days, "from": iso(start), "to": iso(end), "headlines": len(items),
           "stories": len(events), "summary": {k: v for k, v in s.items() if k != "curve"}, "curve": s.get("curve", []),
           "spyPct": spy_pct,
           "tradingAgents": {"checked": len(ta), "approved": len(appr), "approvedAvgPct": avg(appr), "rejectedAvgPct": avg(rej),
                             "errors": sum(1 for t in ta if t.get("tradingAgents") == "ERROR")},
           "trades": [{k: t.get(k) for k in ("t", "symbol", "event", "why", "confidence", "check", "entry", "exit", "exitT",
                                               "exitReason", "pnl", "pnlPct", "tradingAgents")} for t in trades][-150:],
           "caveats": ["Past news comes from one publisher (Benzinga), so '2 sources' = 2 separate articles.",
                       "No past X/Reddit posts exist to replay.",
                       "Fills are simulated at the next bar; a bar touching both stop and target counts as a stop.",
                       f"TradingAgents was only re-checked on the top {ta_sample} trades (free-tier limit).",
                       "A few weeks of history is a small sample. Treat this as a sanity check, not proof."]}
    write_json(DATA / "backtest.json", out)
    s2 = out["summary"]
    log(f"Backtest done: {s2.get('trades', 0)} trades, win rate {s2.get('winRate', 0)}%, total {s2.get('totalPct', 0):+}% "
        f"vs SPY {spy_pct:+}%" if spy_pct is not None else "Backtest done", "Backtester")
    return out


if __name__ == "__main__":
    out = run(int(sys.argv[1]) if len(sys.argv) > 1 else 30)
    print(json.dumps(out["summary"], indent=1))
    from . import publish
    publish.push("Trading bot: backtest results")
