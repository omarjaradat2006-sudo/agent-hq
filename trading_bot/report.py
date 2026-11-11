"""Writes data/trading/state.json: what the Trading tab in Agent HQ shows."""
from datetime import timedelta
from . import config as C
from .util import read_json, write_json, iso, now_utc, now_et, parse_time, drain_log, DATA

AGENTS = [
    ("scout", "News Scout", "Reads X, Reddit and news feeds"),
    ("analyst", "News Analyst", "Gemini: is it real, what moves, which way"),
    ("confirm", "Confirmation Checker", "2 sources + volume + price check"),
    ("deep", "Deep Analyst", "TradingAgents debate, max 5 a day"),
    ("risk", "Risk Officer", "Hard limits, stop-losses, kill switch"),
    ("trader", "Trader", "Places paper orders on Alpaca"),
    ("coins", "Coin Watcher", "Meme coins: watch only, never trades"),
    ("screener", "Halal Screener", "Weekly Shariah screen"),
]
AGENT_OF = {"News Scout": "scout", "News Analyst": "analyst", "Analyst": "confirm", "Deep Analyst": "deep",
            "Risk Officer": "risk", "Trader": "trader", "Coin Watcher": "coins", "Halal Screener": "screener"}


def write(bot):
    old = read_json(DATA / "state.json", {}) or {}
    led, s = bot.ledger, bot.s
    new_log = [{"t": l["t"], "agent": l["agent"], "msg": l["msg"]} for l in reversed(drain_log())]
    log = (new_log + (old.get("log") or []))[:150]
    acct = bot.a.account()
    eq, last = float(acct["equity"]), float(acct.get("last_equity") or acct["equity"])
    start = led.get("startEquity") or eq
    spy_now = (led["equity"][-1].get("spy") if led.get("equity") else None) or led.get("spyStart")
    spy_pct = ((spy_now - led["spyStart"]) / led["spyStart"] * 100) if led.get("spyStart") and spy_now else None
    total_pct = (eq - start) / start * 100
    open_t = [t for t in led["trades"] if t["status"] in ("open", "pending")]
    closed = [t for t in led["trades"] if t["status"] == "closed"]
    today = now_et().date().isoformat()
    closed_today = [t for t in closed if parse_time(t["closedAt"]).astimezone(now_et().tzinfo).date().isoformat() == today]
    from .watch import summary as wsum
    watch = s.get("watch") or []
    counters = s.get("counters") or {}
    deep_used = counters.get("deep", 0) if counters.get("day") == today else 0

    last_by_agent = {}
    for l in log:
        last_by_agent.setdefault(AGENT_OF.get(l["agent"], ""), l)
    agents = []
    for aid, name, role in AGENTS:
        l = last_by_agent.get(aid)
        recent = l and now_utc() - parse_time(l["t"]) < timedelta(minutes=20)
        agents.append({"id": aid, "name": name, "role": role, "status": "working" if recent else ("ok" if l else "idle"),
                       "doing": l["msg"] if l else "", "lastRun": l["t"] if l else None})

    day_pnl = eq - last
    head = (f"Paper account {'+' if day_pnl >= 0 else '-'}${abs(day_pnl):,.0f} today ({day_pnl / last * 100:+.2f}%), "
            f"{total_pct:+.2f}% total" + (f" vs SPY {spy_pct:+.2f}%" if spy_pct is not None else "")
            + f" · {len(open_t)} open")
    notes = []
    if led.get("killed"):
        notes.append("KILL SWITCH ON: down 10% from the start, everything sold. Review, then run 'unlock'.")
    if s.get("haltedDate") == today:
        notes.append("Down 3% today: no new trades until tomorrow.")
    soc = s.get("socialStatus") or {}
    if soc.get("problems"):
        notes.append("X/Reddit reader: " + soc["problems"][0][:140])
    events = sorted(s.get("events", {}).values(), key=lambda e: e.get("lastSeen", ""), reverse=True)[:12]

    plain = plain_words(bot, acct, eq, start, spy_pct, today, counters if counters.get("day") == today else {})

    state = {
        "team": "trading", "plain": plain, "hired": True, "updatedAt": iso(), "mode": "PAPER", "agents": agents, "log": log,
        "brief": {"date": f"{now_et():%a %b} {now_et().day}", "createdAt": iso(),
                  "headline": head,
                  "summary": f"{len(closed_today)} trade(s) closed today, {sum(1 for t in closed if t['pnl'] > 0)}/{len(closed)} winners overall. "
                             f"TradingAgents checks used today: {deep_used}/{C.DEEP['max_per_day']}.",
                  "notes": notes},
        "account": {"equity": round(eq, 2), "cash": round(float(acct.get("cash") or 0), 2), "startEquity": round(start, 2),
                    "startedAt": led.get("startedAt"), "dayPnl": round(day_pnl, 2), "dayPct": round(day_pnl / last * 100, 2),
                    "totalPnl": round(eq - start, 2), "totalPct": round(total_pct, 2),
                    "spyPct": round(spy_pct, 2) if spy_pct is not None else None,
                    "vsSpyPct": round(total_pct - spy_pct, 2) if spy_pct is not None else None},
        "status": {"killed": bool(led.get("killed")), "haltedToday": s.get("haltedDate") == today,
                   "deepUsed": deep_used, "deepMax": C.DEEP["max_per_day"], "social": soc,
                   "universe": {"stocks": len((bot.universe or {}).get("stocks") or {}),
                                "crypto": len((bot.universe or {}).get("crypto") or {})},
                   "alert": s.get("alert")},
        "positions": open_t,
        "trades": led["trades"][:120],
        "decisions": led.get("decisions", [])[:60],
        "equity": led.get("equity", [])[-400:],
        "watch": watch[-60:], "watchSummary": wsum(watch),
        "events": [{"summary": e["summary"], "category": e.get("category"), "firstSeen": e.get("firstSeen"),
                    "publishers": sorted({x["publisher"] for x in e["items"]}),
                    "assets": e.get("assets"), "sources": e["items"][:5]} for e in events],
        "rules": {"risk": dict(C.RISK), "confirm": C.confirm_rules(), "rulesMode": C.rules_mode(), "halal": dict(C.HALAL)},
    }
    write_json(DATA / "state.json", state)
    return state


def _n(k, word):
    return f"{k} {word}" + ("" if k == 1 else "s")


def _money(x):
    return f"${abs(x):,.2f}"


def plain_words(bot, acct, eq, start, spy_pct, today, counters):
    """The 3 lines at the top of the Trading tab, in plain words."""
    from .util import read_events
    from .alpaca import to_pos_symbol
    led, uni = bot.ledger, bot.universe or {}
    diff = eq - start
    if abs(diff) < 0.005:
        top = f"Even since start (still {_money(eq)})"
    else:
        top = f"{'Up' if diff > 0 else 'Down'} {_money(diff)} since start ({diff / start * 100:+.2f}%)"
    if spy_pct is not None:
        top += f" · just holding SPY would be {spy_pct:+.2f}%"

    holding = []
    try:
        pos = {p["symbol"]: p for p in bot.a.positions()}
    except Exception:  # noqa: BLE001
        pos = {}
    for t in [t for t in led["trades"] if t["status"] in ("open", "pending")]:
        if t["status"] == "pending":
            holding.append(f"{t['symbol']}: buy order sent, waiting to fill")
            continue
        p = pos.get(to_pos_symbol(t["symbol"])) or {}
        val = float(p.get("market_value") or 0) or (t.get("lastPrice") or t["entryPrice"]) * (t.get("qty") or 0)
        pl = float(p.get("unrealized_pl") or 0)
        q = t.get("qty") or 0
        qty = f"{q:g} shares" if t.get("asset") != "crypto" else f"{q:.6g} coins"
        holding.append(f"{t['symbol']}: {qty} worth {_money(val)}, {'up' if pl >= 0 else 'down'} {_money(pl)} "
                       f"(sells at {_money(t.get('target') or 0)} or stops at {_money(t.get('stop') or 0)})")

    did = []
    in_today = lambda ts: ts and parse_time(ts).astimezone(now_et().tzinfo).date().isoformat() == today
    bought = [t for t in led["trades"] if in_today(t.get("openedAt")) and t["status"] != "cancelled"]
    sold = [t for t in led["trades"] if t["status"] == "closed" and in_today(t.get("closedAt"))]
    for t in bought:
        did.append(f"Bought {t['symbol']} after the news: {((t.get('news') or {}).get('summary') or 'see Trades').rstrip('.')}.")
    for t in sold:
        did.append(f"Sold {t['symbol']} ({t.get('exitReason', 'closed')}): {'made' if t['pnl'] > 0 else 'lost'} {_money(t['pnl'])}.")
    scans, heads, stories = counters.get("scans", 0), counters.get("headlines", 0), counters.get("stories", 0)
    if scans:
        did.append(f"Scanned the news {_n(scans, 'time')} today: read {_n(heads, 'headline')}, found {stories} that could move a "
                   f"stock or coin it's allowed to trade." + ("" if bought else " None passed every check, so no trade (that's normal)."))
    ds = [d for d in led.get("decisions", []) if in_today(d.get("t")) and d["outcome"] != "bought"]
    why = {}
    for d in ds:
        why.setdefault(d["why"], []).append(d["symbol"])
    for w, syms in sorted(why.items(), key=lambda x: -len(x[1]))[:4]:
        did.append(f"Passed on {', '.join(sorted(set(syms))[:5])}: {w}.")
    ev = [e for e in read_events() if in_today(e.get("t")) and e["kind"] in ("risk", "limit")]
    if ev:
        rules = {}
        for e in ev:
            rules[e["rule"].replace("_", " ")] = rules.get(e["rule"].replace("_", " "), 0) + 1
        did.append("Safety rules that stepped in: " + ", ".join(f"{k} (x{v})" for k, v in rules.items()) + ".")
    if not did:
        did.append("Hasn't scanned yet today.")

    n_st = len([s for s in uni.get("stocks") or {} if s not in C.SHARIAH_ETFS])
    n_etf = len([s for s in uni.get("stocks") or {} if s in C.SHARIAH_ETFS])
    n_c = len(uni.get("crypto") or {})
    watch = f"Allowed to trade: {_n(n_st, 'halal stock')}, {_n(n_etf, 'Shariah ETF')}, {_n(n_c, 'coin')}."
    if uni.get("partial"):
        watch += f" Halal stock screen not finished ({uni.get('problem', 'SEC data missing')}); retrying hourly."
    if not (n_st or n_etf or n_c):
        watch = "Allowed to trade: NOTHING yet. The halal list is empty, so every story is skipped."
    n_tr = len([t for t in led["trades"] if t["status"] != "cancelled"])
    held = [t["symbol"] for t in led["trades"] if t["status"] in ("open", "pending")]
    line = (("Even" if abs(diff) < 0.005 else ("Up " if diff > 0 else "Down ") + _money(diff)) + " since start · "
            + _n(n_tr, "trade") + " · holding: " + (", ".join(held) if held else "nothing (all cash)"))
    return {"line": line, "rulesMode": C.rules_mode(), "top": top, "up": diff >= 0, "holding": holding or ["Nothing right now (all cash)."], "today": did,
            "watchlist": watch, "lastScan": counters.get("lastScan")}
