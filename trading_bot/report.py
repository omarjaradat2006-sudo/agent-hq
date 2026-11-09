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

    state = {
        "team": "trading", "hired": True, "updatedAt": iso(), "mode": "PAPER", "agents": agents, "log": log,
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
        "rules": {"risk": dict(C.RISK), "confirm": dict(C.CONFIRM), "halal": dict(C.HALAL)},
    }
    write_json(DATA / "state.json", state)
    return state
