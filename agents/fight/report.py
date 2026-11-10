"""Builds data/fight/state.json for Agent HQ: record (win rate, profit per $100 staked, by bet type),
today's cards, brief, credits and books. Every number comes from ledger.json."""
import datetime
import config as C
import odds as O
import store as S

AGENTS = [
    {"id": "lead", "name": "Desk Lead", "role": "Today's card and the honest record"},
    {"id": "odds", "name": "Odds Scout", "role": "Ontario-licensed prices only, Bet365 excluded"},
    {"id": "court", "name": "Court Analyst", "role": "NBA: injuries, rest, form, matchups"},
    {"id": "fight", "name": "Fight Analyst", "role": "UFC: weigh-ins, styles, form, late news"},
    {"id": "value", "name": "Value & Underdog Checker", "role": "Implied vs fair probability; no value = no bet"},
    {"id": "grader", "name": "Results Grader", "role": "Settles every pick automatically"},
]
SETTLED = ("won", "lost", "push")


def stats(picks):
    s = [p for p in picks if p.get("status") in SETTLED]
    w = sum(p["status"] == "won" for p in s)
    l = sum(p["status"] == "lost" for p in s)
    pu = sum(p["status"] == "push" for p in s)
    profit = round(sum(p.get("profit", 0) for p in s), 2)
    staked = 100 * len(s)
    clv = [p["close"]["clvPct"] for p in picks if isinstance(p.get("close"), dict)]
    return {"picks": len(s), "won": w, "lost": l, "push": pu,
            "winRate": round(100 * w / (w + l), 1) if w + l else None,
            "staked": staked, "profit": profit,
            "profitPer100": round(100 * profit / staked, 2) if staked else None,
            "clvAvg": round(sum(clv) / len(clv), 2) if clv else None,
            "beatClose": round(100 * sum(c > 0 for c in clv) / len(clv)) if clv else None, "clvCount": len(clv)}


def record(lg):
    picks = lg.get("picks", [])
    cut = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    by_type = {k: stats([p for p in picks if p.get("type") == k]) for k in ("single", "underdog", "parlay")}
    by_sport = {k: stats([p for p in picks if p.get("sport") == k]) for k in C.SPORTS}
    series, run = [], 0.0
    for p in sorted([p for p in picks if p.get("status") in SETTLED], key=lambda p: (p.get("commence") or "", p.get("id"))):
        run += p.get("profit", 0)
        series.append({"t": p.get("commence"), "profit": round(run, 2)})
    cards = lg.get("cards", [])
    return {"all": stats(picks), "last30": stats([p for p in picks if (p.get("date") or "") >= cut]),
            "byType": by_type, "bySport": by_sport, "series": series[-400:],
            "open": sum(p.get("status") == "open" for p in picks), "unresolved": sum(p.get("status") == "unresolved" for p in picks),
            "void": sum(p.get("status") == "void" for p in picks),
            "cards": sum(1 for c in cards if c.get("games")),
            "noBetDays": sum(1 for c in cards if str(c.get("noBet") or "").startswith("No bet")),
            "updatedAt": S.now_iso()}


def brief(st, rec):
    cards = st.get("cards", {})
    today = S.today()
    head, film = [], []
    for sp in ("nba", "ufc"):
        c = cards.get(sp)
        if not c or c.get("date") != today:
            continue
        n = len(c.get("picks", [])) + len(c.get("parlays", []))
        if c.get("noGames"):
            continue
        head.append(f"{C.SPORTS[sp]['name']}: {n} value pick{'s' if n != 1 else ''}" if n else f"{C.SPORTS[sp]['name']}: no bet")
        for p in (c.get("picks", []) + c.get("parlays", []))[:3]:
            film.append(f"{p['selection']} ({p['event']}) {p['american']} at {p['bookName']} · EV {p['evPer100']:+.2f} per $100")
    a = rec["all"]
    summary = (f"Record: {a['won']}-{a['lost']}" + (f"-{a['push']}" if a["push"] else "") +
               (f", {a['winRate']}% wins, {a['profitPer100']:+.2f} per $100 staked over {a['picks']} settled picks." if a["picks"] else ". No settled picks yet.") +
               (f" Beat the closing price on {a['beatClose']}% of {a['clvCount']} picks." if a["clvCount"] else ""))
    if a["picks"] and a["picks"] < 100:
        summary += " Under 100 picks is too few to judge; watch the closing-price number first."
    cr = O.credits()
    notes = ["Prices come from each book's feed; confirm the price in the Ontario app before deciding.",
             "Bet365 is excluded from every price, comparison and calculation."]
    if cr.get("remaining") is not None:
        notes.insert(0, f"Odds API credits left this month: {cr['remaining']} of 500 (free plan).")
    return {"date": today, "createdAt": S.now_iso(), "headline": " · ".join(head) or "No NBA or UFC card today",
            "summary": summary, "filmToday": film, "approvals": [], "notes": notes}


def refresh(st, lg):
    have = {a.get("id"): a for a in st.get("agents", [])}
    st["agents"] = [{**a, **{k: v for k, v in have.get(a["id"], {}).items() if k in ("status", "doing", "lastRun", "nextRun")}} for a in AGENTS]
    for a in st["agents"]:
        a.setdefault("status", "idle")
    st.update(team="fight", hired=True, updatedAt=S.now_iso())
    rec = record(lg)
    st["record"] = rec
    st["recent"] = sorted([p for p in lg.get("picks", []) if p.get("status") != "open"], key=lambda p: p.get("commence") or "", reverse=True)[:80]
    st["openPicks"] = [p for p in lg.get("picks", []) if p.get("status") == "open"]
    st["credits"] = {**O.credits(), "plan": "Free (500 credits/month, no card)", "estimatePerMonth": 270, "cost": "$0"}
    books = S.load(f"{C.DATA}/books.json", {})
    st["books"] = {"active": [{"key": k, "name": b["name"], "feed": b["feed"], "mine": k in C.MY_BOOKS} for k, b in O.active_books().items()],
                   "excluded": "Bet365 (excluded everywhere)", "checkedAt": books.get("checkedAt"), "results": books.get("results")}
    st["rules"] = ["Research and recommendations only. It never places bets and never logs into a sportsbook.",
                   "Best odds are picked only from your books: FanDuel, DraftKings, BetMGM and BetRivers. The other Ontario books only help work out the fair price.",
                   "Ontario-licensed sportsbooks only. Bet365 is excluded from odds, comparisons and calculations.",
                   f"A pick needs our blended probability at least {C.MIN_EDGE*100:g} points above the no-vig market and +{C.MIN_EV*100:g}% expected value at the best price. Otherwise: no bet.",
                   "Blended probability = market fair price moved halfway toward the research estimate (AI estimates run overconfident).",
                   "Nothing is ever called a lock. No staking, budget or deposit advice.",
                   "Every pick is tracked at a flat $100 so the record shows whether this actually works."]
    st["brief"] = brief(st, rec)
    S.agent(st, "lead", "ok", st["brief"]["headline"])
    # our own fixed text (rules, books, brief notes) names Bet365 and "lock" on purpose; everything else is scrubbed
    S.save(S.STATE, {k: (v if k in ("rules", "books", "brief", "agents") else S.clean(v)) for k, v in st.items()})
