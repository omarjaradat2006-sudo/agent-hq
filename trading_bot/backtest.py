"""Backtest: Omar's rules over past news (Alpaca/Benzinga archive) and past prices. Paper maths only, no orders.

    python -m trading_bot.backtest                 last 30 days
    python -m trading_bot.backtest 365             last 12 months
    python -m trading_bot.backtest 180 --max-calls 150 --ta 10 --per-day 80

Built to run for 6-12 months on the free Gemini tier:
  - past news is saved month by month in trading_bot/local/bt_news/ (fetched once)
  - Gemini reads each day's headlines once and the answer is cached per day, so a run that stops on the
    daily quota (or the --max-calls budget, default 150) just continues where it left off next time.
    Triage uses Flash-Lite only, so it never spends the Flash quota the 9 agent teams use.
  - results so far are published every run; the Backtest tab says PARTIAL until every day is read.
Same rules as live: confirmation (2 articles, volume 1.5x, move +0.3% to +3%), 5% per trade, max 5 positions,
cash only, -3% stop / +6% target, 3-trading-day stock limit, 48h crypto limit, -3% day halt, -10% kill switch.
TradingAgents re-checks the --ta strongest trades (default 10) once the whole period has been read.
"""
import bisect, json, sys
from datetime import datetime, timedelta, timezone
from . import config as C
from .util import load_env, read_json, write_json, iso, now_utc, parse_time, log, DATA, LOCAL, ET

CACHE = LOCAL / "backtest_cache.json"        # Gemini triage answers, per day
NEWS_DIR = LOCAL / "bt_news"                 # past headlines, per calendar month
START_CASH = 100000.0


class QuotaStop(Exception):
    pass


# ------------------------------------------------------------------ news
def _months(start, end):
    m = datetime(start.year, start.month, 1, tzinfo=timezone.utc)
    while m < end:
        nxt = datetime(m.year + (m.month == 12), m.month % 12 + 1, 1, tzinfo=timezone.utc)
        yield m, nxt
        m = nxt


def _item(n):
    return {"id": f"bz{n['id']}", "publisher": "Benzinga", "kind": "news", "title": n.get("headline", ""),
            "summary": (n.get("summary") or "")[:200], "url": n.get("url"), "time": n["created_at"],
            "symbols": n.get("symbols") or []}


def _fetch_window(a, symbols, s, e, seen, out, stats, general=True):
    chunks = [symbols[i:i + 40] for i in range(0, len(symbols), 40)]
    # symbol news in 10-day slices (each slice can hold up to 4,000 articles per 40 symbols)
    t = s
    while t < e:
        u = min(e, t + timedelta(days=10))
        for ch in chunks:
            got = a.news(start=iso(t), end=iso(u), symbols=ch, limit=50, max_pages=80)
            if len(got) >= 50 * 80:
                stats["truncated"] += 1
            for n in got:
                if n["id"] not in seen:
                    seen.add(n["id"]); out.append(_item(n))
        t = u
    # general market news (war, Fed, oil...) one day at a time, newest 200 per day
    d = s if general else e
    while d < e:
        for n in a.news(start=iso(d), end=iso(min(e, d + timedelta(days=1))), limit=50, max_pages=4):
            if n["id"] not in seen:
                seen.add(n["id"]); out.append(_item(n))
        d += timedelta(days=1)


def fetch_news(a, symbols, start, end, per_day=150):
    """Headlines between start and end, capped at per_day a day (company-specific news first)."""
    NEWS_DIR.mkdir(parents=True, exist_ok=True)
    items, stats = [], {"truncated": 0}
    for m0, m1 in _months(start, end):
        f = NEWS_DIR / f"{m0:%Y-%m}.json"
        c = read_json(f, {}) or {}
        want_to = min(m1, end)
        have_to = parse_time(c.get("fetchedTo"))
        have_syms = set(c.get("symbols") or [])
        missing = [x for x in symbols if x not in have_syms]       # e.g. the halal list was empty last time
        if not have_to or have_to < want_to or missing:
            seen = {x["id"][2:] if x["id"].startswith("bz") else x["id"] for x in c.get("items", [])}
            seen = {int(x) if str(x).isdigit() else x for x in seen}
            out = list(c.get("items", []))
            if have_to and missing:     # past part of the month: only the symbols we didn't have
                _fetch_window(a, missing, m0, min(have_to, want_to), seen, out, stats, general=False)
            if not have_to or have_to < want_to:
                _fetch_window(a, symbols, have_to or m0, want_to, seen, out, stats)
            c = {"fetchedTo": iso(max(want_to, have_to or want_to)), "symbols": sorted(have_syms | set(symbols)), "items": out}
            write_json(f, c)
            log(f"Backtest: {m0:%b %Y} news saved ({len(out)} headlines)", "Backtester")
        items.extend(x for x in c["items"] if start <= parse_time(x["time"]) < end)
    by_day = {}
    for n in sorted(items, key=lambda n: (len(n["symbols"]) or 99, n["time"])):
        d = n["time"][:10]
        if len(by_day.setdefault(d, [])) < per_day:
            by_day[d].append(n)
    return {d: sorted(v, key=lambda n: n["time"]) for d, v in sorted(by_day.items())}, stats


# ------------------------------------------------------------------ triage (cached per day, budgeted)
def triage_all(by_day, universe, max_calls=150):
    from .triage import triage
    cache = read_json(CACHE, {}) or {}
    calls, done_days, stopped = 0, 0, None
    ufp = f"u{len(universe.get('stocks') or {})}-{len(universe.get('crypto') or {})}"   # new halal list -> read again
    events = {}
    for day, items in by_day.items():
        day_ok = True
        for i in range(0, len(items), 70):
            batch = items[i:i + 70]
            key = f"{day}|{ufp}|{batch[0]['id']}|{batch[-1]['id']}|{len(batch)}"
            if key not in cache:
                if stopped or calls >= max_calls:
                    stopped = stopped or f"used this run's budget of {max_calls} Gemini calls"
                    day_ok = False
                    break
                res = None
                for attempt in range(2):
                    try:
                        calls += 1
                        res = triage(batch, {}, universe, [], raise_on_fail=True)
                        break
                    except ValueError:            # Gemini sent broken JSON: try once more, then skip this batch
                        res = [] if attempt else None
                    except Exception as e:  # noqa: BLE001  quota / network: stop, keep what we have
                        stopped = f"Gemini stopped answering ({str(e)[:120]})"
                        break
                if res is None:
                    day_ok = False
                    break
                cache[key] = res
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
        done_days += day_ok
    for e in events.values():
        e["items"].sort(key=lambda x: x["time"])
        e["firstSeen"] = e["items"][0]["time"]
        # proxy for "2 independent sources": the second separate article about the story
        e["confirmedAt"] = e["items"][1]["time"] if len(e["items"]) >= 2 else None
    return events, {"calls": calls, "daysRead": done_days, "days": len(by_day), "stopped": stopped}


# ------------------------------------------------------------------ simulation
def _prep(bars):
    for b in bars:
        if not isinstance(b["t"], datetime):
            b["t"] = parse_time(b["t"])
    bars.sort(key=lambda b: b["t"])
    return bars


def simulate(a, events, start, end, rules=None):
    from .market import confirm
    syms = sorted({s for e in events.values() if e.get("confirmedAt") for s, x in e["assets"].items() if x["direction"] == "up"}
                  | {s for e in events.values() for s, x in e["assets"].items() if x["direction"] == "down"})
    stocks = [s for s in syms if "/" not in s]
    crypto = [s for s in syms if "/" in s]
    bars = {}
    for i in range(0, len(stocks), 20):
        bars.update(a.stock_bars(stocks[i:i + 20], "5Min", iso(start - timedelta(days=16)), iso(end)))
    if crypto:
        bars.update(a.crypto_bars(crypto, "15Min", iso(start - timedelta(days=9)), iso(end)))
    times = {}
    for s in bars:
        _prep(bars[s])
        times[s] = [b["t"] for b in bars[s]]

    cands = []
    for e in events.values():
        if not e.get("confirmedAt"):
            continue
        for sym, x in e["assets"].items():
            if x["direction"] != "up" or x.get("confidence", 0) < C.CONFIRM["min_confidence"] or sym not in bars:
                continue
            look = timedelta(days=8 if "/" in sym else 16)
            t0 = parse_time(e["confirmedAt"])
            for k in range(0, C.CONFIRM["event_fresh_hours"] * 4):     # check every 15 minutes while fresh
                t = t0 + timedelta(minutes=15 * k)
                if "/" not in sym:
                    et = t.astimezone(ET)
                    if et.weekday() >= 5 or not ((et.hour, et.minute) >= (9, 40) and (et.hour, et.minute) <= (15, 30)):
                        continue
                i0, i1 = bisect.bisect_left(times[sym], t - look), bisect.bisect_right(times[sym], t)
                chk = confirm(None, sym, "up", e["firstSeen"], now=t, bars=bars[sym][i0:i1], rules=rules)
                if chk["passed"]:
                    if i1 < len(bars[sym]):
                        nxt = bars[sym][i1]
                        cands.append({"t": nxt["t"], "symbol": sym, "entry": float(nxt["o"]), "event": e["summary"],
                                      "confidence": x["confidence"], "why": x.get("why", ""), "check": chk["reason"],
                                      "rvol": chk["rvol"], "score": x["confidence"] * min(chk["rvol"] / 1.5, 2), "_i": i1})
                    break
                if "too late" in chk.get("reason", ""):
                    break
    cands.sort(key=lambda c: c["t"])

    downs = {}
    for e in events.values():
        for s, x in e["assets"].items():
            if x["direction"] == "down" and x.get("confidence", 0) >= C.CONFIRM["sell_min_confidence"]:
                downs.setdefault(s, []).append(parse_time(e["items"][0]["time"]))
    for v in downs.values():
        v.sort()

    rules = {}
    hit = lambda r: rules.__setitem__(r, rules.get(r, 0) + 1)
    realized, cash, open_, trades, killed = START_CASH, START_CASH, [], [], False
    for c in cands:
        t = c["t"]
        for o in sorted([o for o in open_ if o["exitT"] <= t], key=lambda o: o["exitT"]):   # book exits up to now
            open_.remove(o); cash += o["qty"] * o["exit"]; realized += o["pnl"]
        if killed:
            hit("kill switch (locked)"); continue
        if realized <= START_CASH * (1 - C.RISK["total_loss_kill_pct"]):
            killed = True; hit("kill switch -10%"); continue
        if any(o["symbol"] == c["symbol"] for o in open_):
            hit("already holding it"); continue
        if len(open_) >= C.RISK["max_open_positions"]:
            hit("max 5 positions"); continue
        day = t.astimezone(ET).date()
        day_pnl = sum(x["pnl"] for x in trades if x["exitT"] <= t and x["exitT"].astimezone(ET).date() == day)
        if day_pnl <= -C.RISK["daily_loss_halt_pct"] * realized:
            hit("daily -3% halt"); continue
        budget = min(realized * C.RISK["max_pct_per_trade"], cash)
        qty = budget / c["entry"] if "/" in c["symbol"] else int(budget // c["entry"])
        if qty <= 0:
            hit("cash only (no money left)"); continue
        ex = exit_for(c, bars[c["symbol"]], downs.get(c["symbol"], []), start_idx=c.pop("_i"))
        tr = {**c, **ex, "qty": qty, "pnl": round((ex["exit"] - c["entry"]) * qty, 2),
              "pnlPct": round((ex["exit"] - c["entry"]) / c["entry"] * 100, 2)}
        hit({"stop-loss -3%": "stop-loss -3%", "target +6%": "take-profit +6%", "3 trading-day limit": "stock 3-day limit",
             "48h limit": "crypto 48h limit", "bad news": "sold on bad news"}.get(ex["exitReason"], ex["exitReason"]))
        cash -= qty * c["entry"]
        open_.append(tr); trades.append(tr)
    return trades, rules


def exit_for(c, bars, downs, start_idx=0):
    stop, target = c["entry"] * (1 - C.RISK["stop_loss_pct"]), c["entry"] * (1 + C.RISK["take_profit_pct"])
    t0 = parse_time(c["t"])
    crypto = "/" in c["symbol"]
    days_seen, last_day = 0, t0.astimezone(ET).date()
    bad = [d for d in (parse_time(x) for x in downs) if d > t0]
    for b in bars[start_idx:]:
        bt = parse_time(b["t"])
        if bt <= t0:
            continue
        if bad and bt >= bad[0]:
            return {"exit": float(b["o"]), "exitT": bt, "exitReason": "bad news"}
        if float(b["l"]) <= stop:
            return {"exit": min(stop, float(b["o"])), "exitT": bt, "exitReason": "stop-loss -3%"}
        if float(b["h"]) >= target:
            return {"exit": max(target, float(b["o"])), "exitT": bt, "exitReason": "target +6%"}
        if crypto:
            if bt - t0 >= timedelta(hours=C.RISK["crypto_max_hold_hours"]):
                return {"exit": float(b["c"]), "exitT": bt, "exitReason": "48h limit"}
        else:
            d = bt.astimezone(ET).date()
            if d != last_day:
                days_seen, last_day = days_seen + 1, d
            et = bt.astimezone(ET)
            if days_seen >= C.RISK["stock_max_hold_trading_days"] and (et.hour, et.minute) >= (15, 45):
                return {"exit": float(b["c"]), "exitT": bt, "exitReason": "3 trading-day limit"}
    last = bars[-1]
    return {"exit": float(last["c"]), "exitT": parse_time(last["t"]), "exitReason": "still open at end of test"}


def stats(trades):
    if not trades:
        return {"trades": 0}
    trades = sorted(trades, key=lambda t: parse_time(t["exitT"]))
    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    curve, peak, dd, eq = [], START_CASH, 0.0, START_CASH
    for t in trades:
        eq += t["pnl"]; peak = max(peak, eq); dd = min(dd, (eq - peak) / peak)
        curve.append({"t": iso(parse_time(t["exitT"])), "equity": round(eq, 2)})
    gross_loss = -sum(t["pnl"] for t in losses)
    return {"trades": len(trades), "wins": len(wins), "winRate": round(len(wins) / len(trades) * 100, 1),
            "totalPnl": round(sum(t["pnl"] for t in trades), 2), "totalPct": round((eq - START_CASH) / START_CASH * 100, 2),
            "avgPct": round(sum(t["pnlPct"] for t in trades) / len(trades), 2),
            "avgWinPct": round(sum(t["pnlPct"] for t in wins) / len(wins), 2) if wins else None,
            "avgLossPct": round(sum(t["pnlPct"] for t in losses) / len(losses), 2) if losses else None,
            "profitFactor": round(sum(t["pnl"] for t in wins) / gross_loss, 2) if gross_loss else None,
            "maxDrawdownPct": round(dd * 100, 2), "curve": curve,
            "byExit": {r: sum(1 for t in trades if t["exitReason"] == r) for r in sorted({t["exitReason"] for t in trades})}}


def months(trades):
    m = {}
    for t in trades:
        k = parse_time(t["t"]).astimezone(ET).strftime("%Y-%m")
        x = m.setdefault(k, {"month": k, "trades": 0, "wins": 0, "pnl": 0.0})
        x["trades"] += 1; x["wins"] += t["pnl"] > 0; x["pnl"] = round(x["pnl"] + t["pnl"], 2)
    for x in m.values():
        x["winRate"] = round(x["wins"] / x["trades"] * 100, 1) if x["trades"] else None
    return [m[k] for k in sorted(m)]


def _jsonable(t):
    return {k: (iso(v) if isinstance(v, datetime) else v) for k, v in t.items()}


def run(days=30, ta_sample=10, max_calls=150, per_day=None):
    load_env()
    from .alpaca import Alpaca
    from . import halal, deep
    a = Alpaca()
    per_day = per_day or (150 if days <= 45 else 80)
    end = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)   # whole days only (cache-friendly)
    start = end - timedelta(days=days)
    uni = halal.build_universe(a)
    if uni.get("partial") or not uni.get("stocks"):
        uni = halal.build_universe(a, force=True)
    syms = list((uni.get("stocks") or {}).keys())
    if uni.get("partial"):
        log(f"Backtest: halal screen incomplete ({uni.get('problem')}), so only coins + Shariah ETFs are tested", "Backtester")
    log(f"Backtest: {days} days ({start:%Y-%m-%d} to {end:%Y-%m-%d}), {len(syms)} halal stocks + crypto", "Backtester")
    by_day, fstats = fetch_news(a, syms + [c.replace("/", "") for c in (uni.get("crypto") or {})], start, end, per_day)
    n_items = sum(len(v) for v in by_day.values())
    log(f"Backtest: {n_items} headlines over {len(by_day)} days; Gemini reads them (cached, max {max_calls} calls this run)", "Backtester")
    events, tri = triage_all(by_day, uni, max_calls)
    complete = tri["daysRead"] >= tri["days"]
    trades, rules = simulate(a, events, start, end)
    s = stats(trades)
    spy = a.stock_bars(["SPY"], "1Day", iso(start - timedelta(days=4)), iso(end)).get("SPY", [])
    spy_pct = round((float(spy[-1]["c"]) - float(spy[0]["c"])) / float(spy[0]["c"]) * 100, 2) if len(spy) > 1 else None
    ta = []
    if complete and ta_sample:
        for t in sorted(trades, key=lambda t: t["score"], reverse=True)[:ta_sample]:
            v = deep.run(t["symbol"], trade_date=t["t"].astimezone(ET).date().isoformat(), context=t["event"])
            t["tradingAgents"] = v.get("rating")
            ta.append(t)
    appr = [t for t in ta if t.get("tradingAgents") in C.DEEP["approve_ratings"]]
    rej = [t for t in ta if t.get("tradingAgents") not in C.DEEP["approve_ratings"]]
    avg = lambda xs: round(sum(x["pnlPct"] for x in xs) / len(xs), 2) if xs else None
    pct_read = round(tri["daysRead"] / tri["days"] * 100, 1) if tri["days"] else 0
    out = {"ranAt": iso(), "days": days, "from": iso(start), "to": iso(end), "headlines": n_items,
           "stories": len(events), "complete": complete, "triagedPct": pct_read, "geminiCallsThisRun": tri["calls"],
           "stoppedBecause": tri["stopped"], "summary": {k: v for k, v in s.items() if k != "curve"}, "curve": s.get("curve", []),
           "months": months(trades), "riskRules": rules, "spyPct": spy_pct,
           "tradingAgents": {"checked": len(ta), "approved": len(appr), "approvedAvgPct": avg(appr), "rejectedAvgPct": avg(rej),
                             "errors": sum(1 for t in ta if t.get("tradingAgents") == "ERROR")},
           "trades": [_jsonable({k: t.get(k) for k in ("t", "symbol", "event", "why", "confidence", "check", "entry", "exit",
                                                         "exitT", "exitReason", "pnl", "pnlPct", "tradingAgents")})
                      for t in sorted(trades, key=lambda t: t["t"])][-300:],
           "caveats": ([] if complete else [f"PARTIAL: Gemini has read {pct_read}% of the days so far. Run the backtest again "
                                            "(tomorrow if the free quota ran out) and it continues where it stopped."]) +
                      ["Past news comes from one publisher (Benzinga), so '2 sources' = 2 separate articles.",
                       "No past X/Reddit posts exist to replay.",
                       f"At most {per_day} headlines a day are read (company news first) to fit the free Gemini quota.",
                       "The halal list is today's list (companies that changed or delisted aren't in it).",
                       "Fills are simulated at the next bar's open; a bar touching both stop and target counts as a stop.",
                       "The -3% day halt and -10% kill switch use closed-trade P&L only (open trades aren't marked to market).",
                       f"TradingAgents was only re-checked on the top {ta_sample} trades (free-tier limit)."
                       + ("" if complete else " Not run yet: it waits until the whole period is read."),
                       "Past results don't promise future results. Treat this as evidence, not proof."]
                      + ([f"{fstats['truncated']} news slice(s) hit Alpaca's page limit, so some headlines were left out."]
                         if fstats["truncated"] else [])}
    write_json(DATA / "backtest.json", out)
    s2 = out["summary"]
    log(f"Backtest {'done' if complete else 'PARTIAL (' + str(pct_read) + '% read)'}: {s2.get('trades', 0)} trades, "
        f"win rate {s2.get('winRate', 0)}%, total {s2.get('totalPct', 0):+}%"
        + (f" vs SPY {spy_pct:+}%" if spy_pct is not None else ""), "Backtester")
    if tri["stopped"]:
        log(f"Backtest paused: {tri['stopped']}. Run it again to continue.", "Backtester")
    return out


def _arg(args, name, default):
    return int(args[args.index(name) + 1]) if name in args else default


if __name__ == "__main__":
    args = sys.argv[1:]
    days = int(args[0]) if args and args[0].isdigit() else 30
    out = run(days, ta_sample=_arg(args, "--ta", 10), max_calls=_arg(args, "--max-calls", 150),
              per_day=_arg(args, "--per-day", None))
    print(json.dumps({k: out[k] for k in ("complete", "triagedPct", "stoppedBecause")} | {"summary": out["summary"]}, indent=1))
    from . import publish
    publish.push("Trading bot: backtest results" + ("" if out["complete"] else " (partial)"))
