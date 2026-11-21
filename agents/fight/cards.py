"""The daily NBA card and the Friday UFC card. Research and recommendations only; nothing here can place a bet."""
import json
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
    splits, ssrc = A.nba_splits(today, games)
    all_main = list(cands)        # keep spreads here for the tracked fade list (never used on slips)
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
    # Omar's rule: no moneylines, no regular spreads; alternate spreads only with a big cushion (-300 or shorter)
    cands = [c for c in cands if c["market"] not in C.NBA_BLOCKED_MARKETS]
    for c in cands:
        if c["market"] == "alternate_spreads":
            c["prices"] = {b: d for b, d in c["prices"].items() if d <= C.ALT_SPREAD_MAX_DEC}
    cands = [c for c in cands if c["prices"]]
    text, idx = A.lines([c for c in cands if c["eventId"] in sgp_ids])
    split_txt = "" if not splits else "Public betting splits today (% of bets / % of money):\n" + json.dumps(splits)[:3000]
    est = A.estimate("nba", text, notes, src + src2, today, extra=extra + "\n" + split_txt)
    analyzed = A.apply_estimates(est, idx)
    parlays = B.build_sgp(cands, cid, today, sgp_ids)
    A.why_lines(parlays)
    fades = fade_list(splits or [], all_main, cid, today)
    money = money_ranking(splits or [])
    card.update(money=money, splits=splits, splitsSource=(ssrc[0][1] if ssrc else None), fades=fades,
                splitsMessage=None if splits else "Couldn't get today's betting splits.")
    card.update(games=len(raw), propGames=prop_games, propGameNames=prop_names, analyzedLines=analyzed, totalLines=len(idx), parlays=parlays,
                propBudget=budget, sources=[{"title": t, "url": u} for t, u in (src + src2)[:20]])
    if not prop_ids:
        card["message"] = "No same-game parlays today: no player props were available (odds credits or books hadn't posted props yet)."
    elif len(parlays) < 3:
        card["message"] = f"Only {len(parlays)} slip(s) today: the {prop_games} game(s) with props didn't have enough allowed legs to reach every target."
    msg = f"NBA: {len(parlays)} same-game parlay(s); props for {prop_games} of {len(raw)} games ({', '.join(prop_names)}); {analyzed} lines analyzed"
    return _finish(card, "court", msg, parlays + fades)


def money_ranking(splits):
    """Every spread/total side ranked by % of the money: the top line is where the most money is tonight."""
    rows = []
    for g in splits:
        sp, tt = g.get("spread") or {}, g.get("total") or {}
        try:
            if sp.get("fav") is not None and sp.get("favMoney") is not None:
                fm = float(sp["favMoney"]); ln = float(sp.get("line") or 0)
                side = (f"{sp['fav']} {ln:+g}", fm) if fm >= 50 else (f"{sp['fav']} opponent {-ln:+g}", 100 - fm)
                rows.append({"game": g["game"], "line": side[0], "money": round(side[1]), "bets": round(float(sp.get("favBets", 50)) if fm >= 50 else 100 - float(sp.get("favBets", 50)))})
            if tt.get("line") is not None and tt.get("overMoney") is not None:
                om = float(tt["overMoney"])
                rows.append({"game": g["game"], "line": f"{'Over' if om >= 50 else 'Under'} {float(tt['line']):g}", "money": round(om if om >= 50 else 100 - om),
                             "bets": round(float(tt.get("overBets", 50)) if om >= 50 else 100 - float(tt.get("overBets", 50)))})
        except (TypeError, ValueError):
            continue
    return sorted(rows, key=lambda r: -r["money"])


def fade_list(splits, cands, cid, today):
    """Opposite of where the money is (65%+ of the money) on spreads and totals, at the real FD/DK price. Tracked, not a slip."""
    out = []
    def hit(c, g):
        s = str(g.get("game", "")).lower()
        return W.short(c["home"]).lower() in s and W.short(c["away"]).lower() in s
    for g in splits:
        sp, tt = g.get("spread") or {}, g.get("total") or {}
        targets = []
        try:
            if sp.get("fav") and float(sp.get("favMoney", 0)) >= C.FADE_MIN_MONEY:
                targets.append(("spreads", "dog", sp, f"{sp['favMoney']:g}% of the money on {sp['fav']}"))
            elif sp.get("fav") and 100 - float(sp.get("favMoney", 50)) >= C.FADE_MIN_MONEY:
                targets.append(("spreads", "fav", sp, f"{100 - float(sp['favMoney']):g}% of the money on the underdog"))
            if tt and float(tt.get("overMoney", 0)) >= C.FADE_MIN_MONEY:
                targets.append(("totals", "Under", tt, f"{tt['overMoney']:g}% of the money on the Over"))
            elif tt and 100 - float(tt.get("overMoney", 50)) >= C.FADE_MIN_MONEY:
                targets.append(("totals", "Over", tt, f"{100 - float(tt['overMoney']):g}% of the money on the Under"))
        except (TypeError, ValueError):
            continue
        for mk, side, info, why in targets:
            pool = [c for c in cands if c["market"] == mk and hit(c, g)]
            if mk == "spreads":
                fav = str(info.get("fav", "")).lower()
                is_fav = lambda c: W.short(c["side"]).lower() in fav or fav in c["side"].lower()
                pool = [c for c in pool if (is_fav(c) if side == "fav" else not is_fav(c))]
            else:
                pool = [c for c in pool if c["side"] == side]
            if not pool:
                continue
            c = max(pool, key=lambda c: max(c["prices"].values()))
            book = max(c["prices"], key=c["prices"].get)
            leg = B.leg_row(c, book)
            out.append({"id": f"{cid}-fade{len(out) + 1}", "cardId": cid, "date": today, "sport": "nba", "kind": "nba_fade",
                        "book": book, "bookName": C.BOOKS[book], "dec": leg["dec"], "american": leg["american"], "betText": leg["text"],
                        "why": f"Fading the crowd: {why}.", "commence": c["commence"], "legs": [leg], "status": "open"})
    return out


# ---------------- UFC ----------------

def run_ufc(force=False, dwcs=False):
    """Friday 8 PM (and Tuesday --dwcs for Dana White's Contender Series). UFC only, checked against the official card."""
    today = S.today()
    cid = f"ufc-{today}"
    if _exists(cid) and not force:
        print(f"{cid} already posted; use --force to redo"); return
    card = {"id": cid, "date": today, "sport": "ufc", "createdAt": S.now_iso(), "parlays": [], "keyFights": [], "underdogs": [],
            "message": None, "dogMessage": None, "sources": []}
    status, ev, src = A.ufc_event(today)
    if dwcs and not (status == "ok" and "contender" in str(ev.get("name", "")).lower()):
        print("No Contender Series tonight; nothing posted"); return
    if status == "unchecked":
        card["message"] = "Couldn't check the UFC card this week, so no picks were posted."
        return _finish(card, "fight", "Couldn't check the official UFC card; no picks posted (no odds credits spent)")
    bouts = [b for b in ((ev or {}).get("bouts") or []) if isinstance(b, list) and len(b) == 2]
    if status == "none" or not bouts:
        card["message"] = "No UFC event this week"
        card["noEvent"] = True
        return _finish(card, "fight", "Official schedule checked: no UFC event this week (no odds credits spent)")
    card["event"] = f"{ev.get('name', 'UFC')} ({ev.get('date', '')})"
    on_card = lambda e: any((same_fighter(e["home_team"], a) and same_fighter(e["away_team"], b)) or
                            (same_fighter(e["home_team"], b) and same_fighter(e["away_team"], a)) for a, b in bouts)
    ids = {e["id"] for e in O.fetch_events(C.UFC_KEY, 80) if on_card(e)}
    if not ids:
        card["message"] = f"{card['event']}: FanDuel and DraftKings haven't posted odds for this card yet."
        return _finish(card, "fight", card["message"])
    raw = [e for e in O.fetch_odds(C.UFC_KEY, C.UFC_MAIN, 80) if e["id"] in ids and on_card(e)]   # anything not on the official card is dropped
    cands = [c for e in raw for c in O.candidates(e, "ufc")]
    notes, src2 = A.ufc_research(today, card["event"], bouts)
    sources = src + src2
    text, idx = A.lines(cands)
    A.apply_estimates(A.estimate("ufc", text, notes, sources, today), idx)
    parlays = B.build(cands, "ufc", cid, today)
    A.why_lines(parlays)
    fights, src3 = A.key_fights(today, bouts, notes, sources)
    keyf, winners = key_fight_picks(fights, cands, cid, today)
    dogs = underdogs(cands, notes, sources, cid, today)
    card.update(fights=len(raw), parlays=parlays, keyFights=keyf, underdogs=dogs, sources=[{"title": t, "url": u} for t, u in (sources + src3)[:20]])
    if not dogs:
        card["dogMessage"] = "No underdog worth it this week"
    if len(parlays) < 3:
        card["message"] = f"Only {len(parlays)} parlay(s): not enough separate fights with listed odds to reach every target." if parlays else "No parlay: not enough fights with listed odds."
    msg = f"UFC {card['event']}: {len(raw)} official bouts priced, {len(parlays)} parlay(s), {len(keyf)} key fight(s), {len(dogs)} mispriced underdog(s)"
    return _finish(card, "fight", msg, parlays + winners + dogs)


def key_fight_picks(fights, cands, cid, today):
    """Main / co-main individual picks. Winner and rounds use our checked odds feed; method, strikes and takedowns
    show odds only if the research found them on FanDuel/DraftKings (marked 'check in app')."""
    out, tracked = [], []
    for f in fights:
        a, b = (str(f.get("fight", "")).split(" vs ") + [""])[:2]
        picks = []
        for p in f.get("picks", [])[:6]:
            if p.get("type") in ("strikes", "takedowns") and "under" in str(p.get("bet", "")).lower():
                continue   # no Unders on strikes/takedowns: the apps don't allow them in a same-game parlay
            row = {"type": p.get("type"), "bet": S.sanitize(str(p.get("bet", ""))), "why": S.sanitize(str(p.get("why", "")))[:200],
                   "odds": p.get("odds") if p.get("odds") not in (None, "null", "") else None, "book": p.get("book") if p.get("book") in C.BOOKS.values() else None,
                   "checked": False}
            if p.get("type") in ("winner", "rounds"):
                mk = "h2h" if p["type"] == "winner" else "totals"
                for c in cands:
                    if c["market"] != mk or not ((same_fighter(c["home"], a) and same_fighter(c["away"], b)) or (same_fighter(c["home"], b) and same_fighter(c["away"], a))):
                        continue
                    hit = (mk == "h2h" and same_fighter(c["side"], row["bet"].split(" to ")[0].split(" by ")[0])) or \
                          (mk == "totals" and c["side"].lower() in row["bet"].lower() and f"{c['point']:g}" in row["bet"])
                    if hit:
                        book = max(c["prices"], key=c["prices"].get)
                        row.update(odds=W.american(c["prices"][book]), book=C.BOOKS[book], checked=True)
                        if mk == "h2h":
                            leg = B.leg_row(c, book)
                            tracked.append({"id": f"{cid}-key{len(tracked) + 1}", "cardId": cid, "date": today, "sport": "ufc", "kind": "ufc_main",
                                            "book": book, "bookName": C.BOOKS[book], "dec": leg["dec"], "american": leg["american"],
                                            "betText": leg["text"], "why": row["why"], "commence": c["commence"], "legs": [leg], "status": "open"})
                        break
            picks.append(row)
        out.append({"fight": f.get("fight"), "role": f.get("role", ""), "picks": picks})
    return out, tracked


def underdogs(cands, notes, sources, cid, today):
    """Analyze ALL underdogs; list only the 1-3 that look genuinely mispriced (our chance at least 4 points above the price)."""
    dogs = [c for c in cands if c["market"] == "h2h" and c["fair"] < 0.5]
    for c in dogs:
        c["_book"] = max(c["prices"], key=c["prices"].get)
    dogs = [c for c in dogs if c["prices"][c["_book"]] >= C.UFC_DOG_MIN_DEC]   # serious underdogs only (+200 or longer)
    if not dogs:
        return []
    text = "\n".join(f"- {c['side']} (vs {c['home'] if c['side'] == c['away'] else c['away']}): {W.american(c['prices'][c['_book']])} on {C.BOOKS[c['_book']]}, fair chance {c['fair']*100:.0f}%" for c in dogs)
    res = []
    for d in (A.ufc_underdogs(today, text, notes, sources).get("underdogs") or [])[:3]:
        c = next((x for x in dogs if isinstance(d, dict) and same_fighter(x["side"], str(d.get("fighter", "")))), None)
        if not c:
            continue
        try:
            c["model"] = float(d.get("prob"))
        except (TypeError, ValueError):
            continue
        book, ch = c["_book"], B.chance(c)
        dec = c["prices"][book]
        if ch - M.implied(dec) < 0.04:   # not actually mispriced
            continue
        path = str(d.get("path") or "decision").strip()
        leg = B.leg_row(c, book)
        res.append({"id": f"{cid}-dog-{len(res) + 1}", "cardId": cid, "date": today, "sport": "ufc", "kind": "ufc_dog", "risk": "High risk",
                    "book": book, "bookName": C.BOOKS[book], "dec": round(dec, 3), "american": W.american(dec), "path": path,
                    "betText": leg["text"], "methodBet": f"{c['side']} by {path}", "why": S.sanitize(str(d.get("whyOff", "")))[:200],
                    "chancePct": round(ch * 100, 1), "impliedPct": round(100 / dec, 1), "evPer100": round(M.ev(ch, dec) * 100, 2),
                    "breakdown": d.get("breakdown") or {}, "commence": c["commence"],
                    "pathNote": f"Find \"{c['side']} by {path}\" under Method of Victory in the app; the record tracks the straight win and whether the method was right.",
                    "legs": [leg], "status": "open"})
    return res
