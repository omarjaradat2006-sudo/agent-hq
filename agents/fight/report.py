"""Builds data/fight/state.json for Agent HQ. Every record number comes from ledger.json (flat $100 per bet)."""
import config as C
import odds as O
import store as S

AGENTS = [
    {"id": "lead", "name": "Desk Lead", "role": "Posts the slips and the plain-words record"},
    {"id": "odds", "name": "Odds Scout", "role": "FanDuel + DraftKings live lines only"},
    {"id": "court", "name": "Court Analyst", "role": "NBA: injuries, rest, matchups, form, player props"},
    {"id": "fight", "name": "Fight Analyst", "role": "UFC: full fighter breakdowns, weigh-ins, line moves"},
    {"id": "value", "name": "Parlay Builder", "role": "3 placeable parlays, one leg per game, one book"},
    {"id": "grader", "name": "Results Grader", "role": "Grades every parlay and underdog pick"},
]
KINDS = {"nba_parlay": "NBA parlays", "ufc_parlay": "UFC parlays", "ufc_dog": "UFC underdog picks"}


def stats(bets):
    s = [b for b in bets if b.get("status") in ("won", "lost", "push")]
    w, l = sum(b["status"] == "won" for b in s), sum(b["status"] == "lost" for b in s)
    profit = round(sum(b.get("profit", 0) for b in s), 2)
    return {"bets": len(s), "won": w, "lost": l, "push": len(s) - w - l, "profit": profit,
            "per100": round(profit / len(s), 2) if s else None, "open": sum(b.get("status") == "open" for b in bets)}


def line(name, s):
    if not s["bets"]:
        return f"{name}: no results yet" + (f" ({s['open']} waiting)" if s["open"] else "")
    word = "up" if s["per100"] >= 0 else "down"
    push = f", {s['push']} void" if s["push"] else ""
    return f"{name}: {s['won']} won, {s['lost']} lost{push}, {word} ${abs(s['per100']):.2f} per $100"


def record(lg):
    bets = lg.get("bets", [])
    by = {k: stats([b for b in bets if b.get("kind") == k]) for k in KINDS}
    tl = []
    for sp in ("nba", "ufc"):
        for t, _, _ in C.TARGETS:
            tl.append(line(f"{sp.upper()} {t} parlays", stats([b for b in bets if b.get("kind") == f"{sp}_parlay" and b.get("tier") == t])))
    return {"all": stats(bets), "byKind": by, "lines": [line(KINDS[k], by[k]) for k in KINDS], "tierLines": tl, "updatedAt": S.now_iso()}


def refresh(st, lg):
    have = {a.get("id"): a for a in st.get("agents", [])}
    st["agents"] = [{**a, **{k: v for k, v in have.get(a["id"], {}).items() if k in ("status", "doing", "lastRun")}} for a in AGENTS]
    for a in st["agents"]:
        a.setdefault("status", "idle")
    st.update(team="fight", hired=True, updatedAt=S.now_iso())
    for k in ("recent", "openPicks"):
        st.pop(k, None)
    rec = record(lg)
    st["record"] = rec
    st["history"] = sorted([b for b in lg.get("bets", []) if b.get("status") != "open"], key=lambda b: b.get("commence") or "", reverse=True)[:60]
    st["credits"] = {**O.credits(), "planCredits": C.PLAN_CREDITS,
                     "plan": "Free (500 credits a month)" if C.PLAN_CREDITS <= 500 else f"Paid ({C.PLAN_CREDITS:,} credits a month)"}
    st["costInfo"] = [
        "Now: free plan, $0. Covers NBA winner, spread and game total for every game, plus player points/rebounds/assists/threes and team totals for about 2 games a day (that's what 500 credits a month allows).",
        "Upgrade option (not done): The Odds API 20K plan, $30 USD a month (about $42 CAD). Gives player props and team totals for every NBA game every day (about 1,300 credits a month used).",
        "UFC: the feed carries fight winner and, at some books, total rounds. It does NOT carry method of victory, significant strikes or takedowns on any plan, so UFC underdog picks are tracked as straight wins.",
        "Grading costs no odds credits: NBA results and box scores come from ESPN's free public data; UFC results from a sourced Google search.",
        "Credits left are checked before every call; it stops spending 25 credits before the limit and posts fewer prop games instead.",
    ]
    st["books"] = {"active": list(C.BOOKS.values()), "excluded": "Bet365 is excluded everywhere. No other book is read or shown."}
    st["rules"] = ["Research and recommendations only. It never places bets and never logs into a sportsbook.",
                   "FanDuel and DraftKings only. Every leg came from that app's live odds when it was posted.",
                   "One leg per game, all legs on one app: a normal parlay the app accepts, total odds = the legs multiplied.",
                   "Most analyzed, not safest. Nothing is ever called a lock or guaranteed.",
                   "No budget, stake or deposit advice. You decide your own money.",
                   "Every parlay and underdog pick is graded automatically at a flat $100 so the record shows if it profits."]
    head = []
    for sp in ("nba", "ufc"):
        c = st.get("cards", {}).get(sp)
        if c and c.get("date") == S.today():
            head.append(f"{sp.upper()}: " + (f"{len(c['parlays'])} parlays" if c.get("parlays") else (c.get("message") or "no slips")))
    st["brief"] = {"date": S.today(), "createdAt": S.now_iso(), "headline": " · ".join(head) or "Next NBA slips at 1:27 PM",
                   "summary": " · ".join(rec["lines"]), "filmToday": [], "approvals": [], "notes": []}
    S.agent(st, "lead", "ok", st["brief"]["headline"])
    S.save(S.STATE, {k: (v if k in ("rules", "books", "brief", "agents") else S.clean(v)) for k, v in st.items()})
