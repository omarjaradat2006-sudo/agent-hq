"""Meme / celebrity coins: WATCH MODE ONLY. Never traded, not even on paper.

When the news desk spots a meme-coin story it logs a pretend entry at the current price and then
follows it with the same rules a real trade would have (-3% stop, +6% target, 48h max) so Omar can
review a week of "what would have happened".
"""
from datetime import timedelta
from . import config as C
from .util import http, HttpError, iso, now_utc, parse_time, log

CG = "https://api.coingecko.com/api/v3"


def _cg_id(ticker, name, cache):
    key = (ticker or name or "").lower()
    if key in cache:
        return cache[key]
    try:
        r = http("GET", f"{CG}/search", {"query": ticker or name}, timeout=20, retries=1) or {}
        coins = r.get("coins") or []
        exact = [c for c in coins if (c.get("symbol") or "").lower() == (ticker or "").lower()]
        pick = (exact or coins or [None])[0]
        cache[key] = pick["id"] if pick else None
    except HttpError:
        cache[key] = None
    return cache[key]


def _prices(ids):
    ids = [i for i in ids if i]
    if not ids:
        return {}
    try:
        r = http("GET", f"{CG}/simple/price", {"ids": ",".join(sorted(set(ids))), "vs_currencies": "usd"}, timeout=20) or {}
        return {k: float(v["usd"]) for k, v in r.items() if "usd" in v}
    except HttpError as e:
        log(f"coin prices unavailable: {e}", "Coin Watcher")
        return {}


def update(state, events):
    w = state.setdefault("watch", [])
    cache = state.setdefault("cgIds", {})
    now = now_utc()
    # new sightings
    for e in events.values():
        for m in e.get("memes") or []:
            if m.get("direction") != "up":
                continue
            tk = (m.get("ticker") or "").upper().replace("$", "")
            dup = any(x for x in w if x["coin"] == (tk or m.get("name")) and x["status"] == "open")
            if dup or m.get("logged"):
                continue
            m["logged"] = True
            cid = _cg_id(tk, m.get("name"), cache)
            if not cid:
                continue
            w.append({"coin": tk or m.get("name"), "name": m.get("name"), "cgId": cid, "event": e["summary"],
                      "eventKey": e["key"], "why": m.get("why", ""), "openedAt": iso(now), "status": "open",
                      "entry": None, "high": None, "low": None})
    # follow open ones
    open_ = [x for x in w if x["status"] == "open"]
    px = _prices([x["cgId"] for x in open_])
    for x in open_:
        p = px.get(x["cgId"])
        if p is None:
            continue
        if x["entry"] is None:
            x["entry"] = x["high"] = x["low"] = p
            log(f"Watching {x['coin']} (would have bought at ${p:.6g}): {x['event'][:90]}", "Coin Watcher")
            continue
        x["high"], x["low"], x["last"] = max(x["high"], p), min(x["low"], p), p
        stop = x["entry"] * (1 - C.RISK["stop_loss_pct"])
        target = x["entry"] * (1 + C.RISK["take_profit_pct"])
        age = now - parse_time(x["openedAt"])
        reason = None
        if x["low"] <= stop:
            reason, exitp = "stop-loss -3%", stop
        elif x["high"] >= target:
            reason, exitp = "target +6%", target
        elif age >= timedelta(hours=C.RISK["crypto_max_hold_hours"]):
            reason, exitp = "48h limit", p
        if reason:
            x.update({"status": "closed", "closedAt": iso(now), "exit": exitp, "exitReason": reason,
                      "pnlPct": round((exitp - x["entry"]) / x["entry"] * 100, 2),
                      "biggestSwingPct": round((x["high"] - x["low"]) / x["entry"] * 100, 1)})
            log(f"Watch result {x['coin']}: {reason} ({x['pnlPct']:+.1f}%)", "Coin Watcher")
    state["watch"] = w[-200:]
    return state["watch"]


def summary(watch):
    closed = [x for x in watch if x["status"] == "closed"]
    wins = [x for x in closed if x["pnlPct"] > 0]
    return {"open": sum(1 for x in watch if x["status"] == "open"), "closed": len(closed), "wins": len(wins),
            "avgPct": round(sum(x["pnlPct"] for x in closed) / len(closed), 2) if closed else None}
