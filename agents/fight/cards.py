"""The daily NBA card and the Friday UFC card. Research and recommendations only; nothing here can place a bet."""
import config as C
import oddsmath as M
import odds as O
import store as S
import analyst as A
import builder as B
import wording as W
from grade import same_fighter


def _finish(card, agent_id, msg, bets=()):
    import report
    st, lg = S.state(), S.ledger()
    card = S.clean(card)
    bets = S.clean(list(bets))
    lg["cards"] = [c for c in lg["cards"] if c.get("id") != card["id"]] + [{"id": card["id"], "date": card["date"], "sport": card["sport"], "bets": len(bets), "message": card.get("message")}]
    lg["bets"] = [b for b in lg["bets"] if b.get("cardId") != card["id"]] + bets
    st.setdefault("cards", {})[card["sport"]] = card
    S.agent(st, agent_id, "ok", msg)
    S.log(st, {"court": "Court Analyst", "fight": "Fight Analyst"}[agent_id], msg)
    S.save(S.LEDGER, lg)
    report.refresh(st, lg)
    print(msg)


def _exists(card_id):
    return any(c.get("id") == card_id for c in S.ledger()["cards"])


# ---------------- NBA ----------------

def run_nba(force=False):
    today = S.today()
    cid = f"nba-{today}"
    if _exists(cid) and not force:
        print(f"{cid} already posted; use --force to redo"); return
    card = {"id": cid, "date": today, "sport": "nba", "createdAt": S.now_iso(), "parlays": [], "message": None, "sources": []}
    print("Gemini:", A.KEY_SOURCE, flush=True)
    events = O.fetch_events(C.NBA_KEY, 20)
    if not events:
        card["message"] = "No NBA games today."
        return _finish(card, "court", "No NBA games today (no credits spent)")
    raw = O.fetch_odds(C.NBA_KEY, C.NBA_MAIN, 20)
    cands = [c for e in raw for c in O.candidates(e, "nba")]
    games = [f"{e['away_team']} @ {e['home_team']}" for e in raw]
    notes, src, ranked = A.nba_research(today, games)
    # props for as many games as the credit budget allows, most promising games first
    budget = min(O.daily_prop_budget(), len(raw))
    order = sorted(raw, key=lambda e: next((i for i, g in enumerate(ranked) if W.short(e["home_team"]).lower() in g.lower()), 99))
    prop_games, players, prop_ids, prop_names = 0, {}, [], []
    for e in order[:budget]:
        try:
            eo = O.fetch_event_odds(C.NBA_KEY, e["id"], C.NBA_PROPS)
        except O.LowCredits:
            break
        pc = O.candidates(eo, "nba") if eo else []
        cands += pc
        if pc:
            prop_games += 1; prop_ids.append(e["id"]); prop_names.append(f"{W.short(e['away_team'])} vs {W.short(e['home_team'])}")
        ps = sorted({c["player"] for c in pc if c.get("player")})
        if ps:
            players[f"{e['away_team']} @ {e['home_team']}"] = ps
    extra, src2 = ("", [])
    if players:
        extra, src2 = A.nba_props_research(today, players)
    # same-game parlays are built only from the prop games; keep milestones between -400 and +400 so the list stays sane
    sgp_ids = [e for e in prop_ids]
    cands = [c for c in cands if not (c["market"].endswith("_alternate") and not any(1.25 <= d <= 5.0 for d in c["prices"].values()))]
    text, idx = A.lines([c for c in cands if c["eventId"] in sgp_ids])
    est = A.estimate("nba", text, notes, src + src2, today, extra=extra)
    analyzed = A.apply_estimates(est, idx)
    parlays = B.build_sgp(cands, cid, today, sgp_ids)
    A.why_lines(parlays)
    card.update(games=len(raw), propGames=prop_games, propGameNames=prop_names, analyzedLines=analyzed, totalLines=len(idx), parlays=parlays,
                propBudget=budget, sources=[{"title": t, "url": u} for t, u in (src + src2)[:20]])
    if not prop_ids:
        card["message"] = "No same-game parlays today: no player props were available (odds credits or books hadn't posted props yet)."
    elif len(parlays) < 3:
        card["message"] = f"Only {len(parlays)} slip(s) today: the {prop_games} game(s) with props didn't have enough allowed legs to reach every target."
    msg = f"NBA: {len(parlays)} same-game parlay(s); props for {prop_games} of {len(raw)} games ({', '.join(prop_names)}); {analyzed} lines analyzed"
    return _finish(card, "court", msg, parlays)


# ---------------- UFC ----------------

def run_ufc(force=False):
    today = S.today()
    cid = f"ufc-{today}"
    if _exists(cid) and not force:
        print(f"{cid} already posted; use --force to redo"); return
    card = {"id": cid, "date": today, "sport": "ufc", "createdAt": S.now_iso(), "parlays": [], "underdogs": [], "message": None, "dogMessage": None, "sources": []}
    ev, src = A.ufc_event(today)
    bouts = [b for b in ((ev or {}).get("bouts") or []) if isinstance(b, list) and len(b) == 2]
    if not bouts:
        card["message"] = "No UFC event this week"
        card["noEvent"] = True
        return _finish(card, "fight", "No UFC event this week (no odds credits spent)")
    card["event"] = f"{ev.get('name', 'UFC')} ({ev.get('date', '')})"
    events = O.fetch_events(C.UFC_KEY, 80)
    match = lambda e: any((same_fighter(e["home_team"], a) and same_fighter(e["away_team"], b)) or (same_fighter(e["home_team"], b) and same_fighter(e["away_team"], a)) for a, b in bouts)
    ids = {e["id"] for e in events if match(e)}
    if not ids:
        card["message"] = f"{card['event']}: FanDuel and DraftKings haven't posted odds for this card yet."
        return _finish(card, "fight", card["message"])
    raw = [e for e in O.fetch_odds(C.UFC_KEY, C.UFC_MAIN, 80) if e["id"] in ids]
    cands = [c for e in raw for c in O.candidates(e, "ufc")]
    notes, src2 = A.ufc_research(today, card["event"], bouts)
    sources = src + src2
    text, idx = A.lines(cands)
    est = A.estimate("ufc", text, notes, sources, today)
    A.apply_estimates(est, idx)
    parlays = B.build(cands, "ufc", cid, today)
    A.why_lines(parlays)
    dogs = underdogs(cands, notes, sources, cid, today)
    card.update(fights=len(raw), parlays=parlays, underdogs=dogs, sources=[{"title": t, "url": u} for t, u in sources[:20]])
    if not dogs:
        card["dogMessage"] = "No underdog worth it this week."
    if len(parlays) < 3:
        card["message"] = f"Only {len(parlays)} parlay(s): not enough separate fights with listed odds to reach every target." if parlays else "No parlay: not enough fights with listed odds."
    msg = f"UFC {card['event']}: {len(parlays)} parlay(s), {len(dogs)} underdog pick(s)"
    return _finish(card, "fight", msg, parlays + dogs)


def underdogs(cands, notes, sources, cid, today):
    dogs = [c for c in cands if c["market"] == "h2h" and c["fair"] < 0.5]
    if not dogs:
        return []
    for c in dogs:
        c["_book"] = max(c["prices"], key=c["prices"].get)
    text = "\n".join(f"- {c['side']} (vs {c['home'] if c['side'] == c['away'] else c['away']}): {W.american(c['prices'][c['_book']])} on {C.BOOKS[c['_book']]}, fair chance {c['fair']*100:.0f}%" for c in dogs)
    out = A.ufc_underdogs(today, text, notes, sources)
    res = []
    for d in out.get("underdogs", []) or []:
        if not isinstance(d, dict) or not d.get("genuine"):
            continue
        c = next((x for x in dogs if same_fighter(x["side"], str(d.get("fighter", "")))), None)
        if not c:
            continue
        try:
            c["model"] = float(d.get("prob"))
        except (TypeError, ValueError):
            c["model"] = None
        c["why"] = str(d.get("oneLine", ""))[:200]
        ch = B.chance(c)
        if ch < C.DOG_MIN_CHANCE:
            continue
        book = c["_book"]
        dec = c["prices"][book]
        path = str(d.get("path") or "straight win").strip()
        straight = path.lower() in ("straight win", "decision", "")
        leg = B.leg_row(c, book)
        res.append({
            "id": f"{cid}-dog-{len(res) + 1}", "cardId": cid, "date": today, "sport": "ufc", "kind": "ufc_dog", "risk": "High risk",
            "book": book, "bookName": C.BOOKS[book], "dec": round(dec, 3), "american": W.american(dec), "path": path,
            "betText": leg["text"], "why": c["why"], "chancePct": round(ch * 100, 1), "impliedPct": round(100 / dec, 1),
            "evPer100": round(M.ev(ch, dec) * 100, 2), "breakdown": d.get("breakdown") or {}, "commence": c["commence"],
            "pathNote": None if straight else (f"Their path is {path}. FanDuel/DraftKings method-of-victory odds aren't in our odds feed, so the "
                                               f"tracked bet is the straight win. The \"{c['side']} by {path}\" version pays more but wasn't checked here."),
            "legs": [leg], "status": "open"})
    return res
