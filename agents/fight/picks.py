"""Daily card for one sport: Ontario odds -> Gemini research -> probability estimates ->
value check in code -> singles, parlays, underdog review, or "no bet".
Research and recommendations only. Nothing here can place a bet."""
import itertools, json, os, re, sys, unicodedata
import config as C
import oddsmath as M
import odds as O
import store as S

sys.path.insert(0, os.path.join(C.ROOT, "agents", "gemini"))
import gemini as G  # noqa: E402

SYSTEM = """You are a sports research analyst on "Fight & Court Intelligence", a research tool used by one adult in Ontario, Canada who makes his own decisions.
You research NBA games and UFC fights and estimate honest win probabilities.
Rules:
- Research and analysis only. Never tell him to bet, never suggest stake sizes, budgets, bankroll plans or deposits.
- Never call anything a lock, guaranteed, a sure thing or free money. Every outcome is uncertain.
- Never mention, use or compare Bet365 in any way.
- Use only facts from the research. Never invent injuries, stats, quotes, results or news. If you're unsure, say so.
- Having no view on a game is fine: return null for the probability instead of guessing.
- Plain English, short sentences."""


def norm(name):
    n = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z ]", " ", n).split()


def same_fighter(a, b):
    """'Islam Makhachev' vs 'Makhachev, Islam' or 'I. Makhachev': last names must match."""
    na, nb = norm(a), norm(b)
    return bool(na and nb) and (na[-1] == nb[-1] or na[-1] in nb or nb[-1] in na)


def label(ev, sport):
    return f"{ev['away']} vs {ev['home']}" if sport == "ufc" else f"{ev['away']} @ {ev['home']}"


def sel_label(mk, name, point):
    if mk == "h2h":
        return f"{name} to win"
    if mk == "spreads":
        return f"{name} {point:+g}"
    return f"{name} {point:g}"


# ---------------- research ----------------

def ufc_card(today):
    """Which bouts in the MMA feed are UFC this week (the feed mixes promotions)."""
    q = (f"Today is {today}. Search for the UFC event(s) taking place in the next 8 days (UFC only, not PFL or other promotions). "
         'Reply with JSON only: {"events":[{"name":"UFC ...","date":"YYYY-MM-DD","bouts":[["Fighter A","Fighter B"], ...]}]}. '
         'Include every bout on the main card and prelims. If there is no UFC event in that window reply {"events":[]}.')
    text, src = G.generate(q, SYSTEM, search=True, temperature=0.1)
    try:
        return G.parse_json(text).get("events", []), src
    except Exception:
        return [], src


def research(sport, slate, today):
    if sport == "nba":
        q = (f"Today is {today}. For each NBA game below, search for: official injury report and who is out or questionable, "
             "rest (back-to-backs, travel), recent form over the last 10 games, offensive/defensive ratings, pace, notable matchup edges, "
             "and any line-moving news from the last 24 hours. Be specific and name your sources.\n" + "\n".join(slate))
    else:
        q = (f"Today is {today}. For each UFC bout below, search for: weigh-in results (missed weight?), short-notice replacements, "
             "injuries or camp changes, records and recent form, age, reach and height, striking and grappling style matchup, "
             "finishing rates, and any line-moving news. Be specific and name your sources.\n" + "\n".join(slate))
    return G.generate(q, SYSTEM, search=True, temperature=0.3)


def board_text(board, sport):
    rows = []
    for n, ev in enumerate(board, 1):
        rows.append(f"E{n} | {label(ev, sport)} | starts {ev['commence']}")
        for ln in ev["lines"]:
            parts = []
            for o in ln["outcomes"]:
                b, d = o["best"]
                parts.append(f"{sel_label(ln['market'], o['name'], o['point'])}: best {M.fmt_american(d)} ({C.BOOKS[b]['name']}), market fair {o['fair']*100:.1f}%")
            rows.append(f"   {ln['market']}: " + " | ".join(parts))
    return "\n".join(rows)


def estimate(sport, board, notes, sources, today):
    src = "\n".join(f"- {t}: {u}" for t, u in sources[:30])
    p = f"""Today is {today}. Below is the {C.SPORTS[sport]['name']} slate with the best Ontario sportsbook price for every side and the market's fair (no-vig) probability.

{board_text(board, sport)}

Research notes from today's web search:
{notes[:14000]}

Sources found:
{src}

For every event, estimate the TRUE probability of the outcomes you have a real, research-based view on.
- Use the market fair probability as your starting point and move away from it only for concrete reasons in the research (injuries, rest, weight miss, style matchup, form).
- Small moves are normal. Moves above 8 points need a strong, specific reason.
- For spreads and totals use the exact point shown. If you have no view, use null.
Return JSON only:
{{"events":[{{"e":"E1","summary":"one or two plain sentences on the matchup","estimates":[{{"market":"h2h|spreads|totals","side":"exact side name as shown (team/fighter, Over or Under)","point":null,"prob":0.55,"reason":"specific reason from the research"}}],"keyFactors":["short factor", "..."]}}],
 "slateNotes":"one sentence on the whole slate"}}"""
    for _ in range(3):
        try:
            text, _ = G.generate(p, SYSTEM, json_out=True, temperature=0.2)
            out = G.parse_json(text)
            if isinstance(out, dict):
                return out
        except Exception as e:
            print("estimate retry:", e, flush=True)
    raise RuntimeError("Gemini didn't return usable estimates")


# ---------------- value ----------------

def find_est(ests, mk, name, point):
    for e in ests or []:
        if e.get("market") != mk or e.get("prob") is None:
            continue
        side = str(e.get("side", ""))
        if not (side.lower() == name.lower() or (mk != "totals" and same_fighter(side, name))):
            continue
        if mk != "h2h":
            try:
                if abs(float(e.get("point")) - float(point)) > 0.01:
                    continue
            except (TypeError, ValueError):
                continue
        try:
            return float(e["prob"]), str(e.get("reason", ""))
        except (TypeError, ValueError):
            return None
    return None


def evaluate(ln, ests):
    """Every outcome of a line with implied, fair, research and blended probability, edge and EV at the best price."""
    outs = ln["outcomes"]
    found = [find_est(ests, ln["market"], o["name"], o["point"]) for o in outs]
    if len(outs) == 2:  # one side's estimate implies the other's
        for i in (0, 1):
            if found[i] is None and found[1 - i] is not None:
                found[i] = (1 - found[1 - i][0], found[1 - i][1])
    res = []
    for o, f in zip(outs, found):
        b, d = o["best"]
        model = f[0] if f else None
        p = M.blend(o["fair"], model, C.MODEL_WEIGHT)
        e = M.ev(p, d)
        edge = p - o["fair"]
        value = model is not None and edge >= C.MIN_EDGE and e >= C.MIN_EV
        res.append({**o, "market": ln["market"], "book": b, "dec": d, "implied": M.implied(d), "model": model,
                    "blended": p, "edge": edge, "ev": e, "value": value, "reason": f[1] if f else ""})
    return res


def pick_row(sport, ev, ev_info, o, kind, card_id, today):
    return {
        "cardId": card_id, "date": today, "sport": sport, "type": kind, "createdAt": S.now_iso(),
        "event": label(ev, sport), "eventId": ev["id"], "commence": ev["commence"], "home": ev["home"], "away": ev["away"],
        "market": o["market"], "selection": sel_label(o["market"], o["name"], o["point"]), "side": o["name"], "point": o["point"],
        "book": o["book"], "bookName": C.BOOKS[o["book"]]["name"], "feed": C.BOOKS[o["book"]]["feed"],
        "dec": round(o["dec"], 3), "american": M.fmt_american(o["dec"]),
        "impliedPct": round(o["implied"] * 100, 1), "fairPct": round(o["fair"] * 100, 1), "fairSource": o.get("fairSource"),
        "researchPct": None if o["model"] is None else round(o["model"] * 100, 1), "ourPct": round(o["blended"] * 100, 1),
        "edgePct": round(o["edge"] * 100, 1), "evPer100": round(o["ev"] * 100, 2), "value": bool(o["value"]),
        "reasoning": S.sanitize(o["reason"] or ""), "summary": S.sanitize(ev_info.get("summary", "")),
        "keyFactors": S.clean(ev_info.get("keyFactors", [])[:5]),
        "allPrices": {C.BOOKS[b]["name"]: M.fmt_american(d) for b, d in sorted(o["prices"].items(), key=lambda x: -x[1])},
        "status": "open",
    }


def build_parlays(sport, legs_pool, card_id, today):
    """2-3 value legs from different events, priced at the one book that has every leg at the best combined price."""
    pool = sorted(legs_pool, key=lambda x: -x[1]["ev"])[:6]
    found = []
    for n in range(C.PARLAY_LEGS[0], C.PARLAY_LEGS[1] + 1):
        for combo in itertools.combinations(pool, n):
            if len({ev["id"] for ev, _, _ in combo}) < n:
                continue
            books = set.intersection(*[set(o["prices"]) for _, o, _ in combo])
            if not books:
                continue
            best = max(books, key=lambda b: M.parlay_decimal([o["prices"][b] for _, o, _ in combo]))
            dec = M.parlay_decimal([o["prices"][best] for _, o, _ in combo])
            prob = M.parlay_prob([o["blended"] for _, o, _ in combo])
            fair = M.parlay_prob([o["fair"] for _, o, _ in combo])
            e = M.ev(prob, dec)
            if e < 0.05:
                continue
            found.append((e, best, dec, prob, fair, combo))
    found.sort(key=lambda x: -x[0])
    out, used = [], set()
    for e, best, dec, prob, fair, combo in found:
        sig = frozenset((ev["id"], o["name"]) for ev, o, _ in combo)
        if sig in used:
            continue
        used.add(sig)
        legs = []
        for ev, o, info in combo:
            legs.append({"event": label(ev, sport), "eventId": ev["id"], "commence": ev["commence"], "home": ev["home"], "away": ev["away"],
                         "market": o["market"], "side": o["name"], "point": o["point"], "selection": sel_label(o["market"], o["name"], o["point"]),
                         "dec": round(o["prices"][best], 3), "american": M.fmt_american(o["prices"][best]),
                         "ourPct": round(o["blended"] * 100, 1), "fairPct": round(o["fair"] * 100, 1), "reasoning": S.sanitize(o["reason"]), "status": "open"})
        out.append({
            "id": f"{card_id}-p{len(out) + 1}", "cardId": card_id, "date": today, "sport": sport, "type": "parlay", "createdAt": S.now_iso(),
            "event": " + ".join(l["selection"] for l in legs), "commence": min(l["commence"] for l in legs),
            "selection": f"{len(legs)}-leg parlay", "book": best, "bookName": C.BOOKS[best]["name"], "feed": C.BOOKS[best]["feed"],
            "dec": round(dec, 3), "american": M.fmt_american(dec), "impliedPct": round(100 / dec, 1), "fairPct": round(fair * 100, 1),
            "ourPct": round(prob * 100, 1), "edgePct": round((prob - fair) * 100, 1), "evPer100": round(e * 100, 2), "value": True,
            "reasoning": "Every leg has value on its own, and the legs are from different games, so they don't depend on each other. "
                         "A parlay multiplies the edge but also the risk: all legs must win.",
            "legs": legs, "status": "open"})
        if len(out) >= C.MAX_PARLAYS:
            break
    return out


# ---------------- the run ----------------

def run(sport, force=False):
    today = S.today()
    card_id = f"{sport}-{today}"
    st, lg = S.state(), S.ledger()
    agent_id = "court" if sport == "nba" else "fight"
    name = C.SPORTS[sport]["name"]
    if not force and any(c.get("id") == card_id for c in lg["cards"]):
        print(f"{card_id} already made today; use --force to redo")
        return
    hours = 30 if sport == "nba" else 40
    events = O.fetch_events(sport, hours)  # free
    card = {"id": card_id, "date": today, "sport": sport, "createdAt": S.now_iso(), "games": 0, "picks": [], "parlays": [], "underdogs": [], "noBet": None, "sources": []}
    if not events:
        card["noBet"] = f"No {name} {'games' if sport == 'nba' else 'UFC card'} in the next {hours} hours."
        card["noGames"] = True
        return finish(st, lg, card, agent_id, f"No {name} events today, no odds credits spent")
    ufc_info = None
    if sport == "ufc":
        cards, src = ufc_card(today)
        bouts = [b for c in cards for b in c.get("bouts", []) if isinstance(b, list) and len(b) == 2]
        events = [e for e in events if any(same_fighter(e["home_team"], a) and same_fighter(e["away_team"], b)
                                           or same_fighter(e["home_team"], b) and same_fighter(e["away_team"], a) for a, b in bouts)]
        ufc_info = ", ".join(f"{c.get('name')} ({c.get('date')})" for c in cards)
        card["event"] = ufc_info
        if not events:
            card["noBet"] = "No UFC card in the next 40 hours (other MMA promotions are ignored)."
            card["noGames"] = True
            return finish(st, lg, card, agent_id, "No UFC bouts in the window, no odds credits spent")
    ids = {e["id"] for e in events}
    raw = [e for e in O.fetch_odds(sport, hours) if e["id"] in ids]
    board = O.board(raw)
    card["games"] = len(board)
    if not board:
        card["noBet"] = f"No Ontario prices posted yet for today's {name} events."
        return finish(st, lg, card, agent_id, "Ontario books haven't posted prices yet")
    S.agent(st, "odds", "ok", f"{name}: {len(board)} events priced at {len(O.active_books())} Ontario books (Bet365 excluded)")
    slate = [f"- {label(ev, sport)} ({ev['commence']})" for ev in board]
    notes, sources = research(sport, slate, today)
    card["sources"] = [{"title": t, "url": u} for t, u in sources[:20]]
    est = estimate(sport, board, notes, sources, today)
    by_e = {str(e.get("e")): e for e in est.get("events", []) if isinstance(e, dict)}
    card["slateNotes"] = S.sanitize(est.get("slateNotes", ""))

    singles, pool, dogs, near = [], [], [], []
    for n, ev in enumerate(board, 1):
        info = by_e.get(f"E{n}", {})
        best_here = None
        for ln in ev["lines"]:
            for o in evaluate(ln, info.get("estimates")):
                near.append((o["ev"], ev, o))
                if o["value"] and (best_here is None or o["ev"] > best_here["ev"]):
                    best_here = o
                if ln["market"] == "h2h" and o["fair"] < 0.5:
                    dogs.append({"event": label(ev, sport), "commence": ev["commence"], "side": o["name"], "american": M.fmt_american(o["dec"]),
                                 "bookName": C.BOOKS[o["book"]]["name"], "impliedPct": round(o["implied"] * 100, 1), "fairPct": round(o["fair"] * 100, 1),
                                 "ourPct": round(o["blended"] * 100, 1), "evPer100": round(o["ev"] * 100, 2), "value": o["value"],
                                 "reasoning": S.sanitize(o["reason"]) or "No research angle strong enough to move off the market price.",
                                 "verdict": "Value" if o["value"] else ("No value: the price is fair or short" if o["model"] is not None else "No value: no research edge")})
        if best_here:
            kind = "underdog" if best_here["market"] == "h2h" and best_here["fair"] < 0.5 and best_here["dec"] >= 2 else "single"
            singles.append(pick_row(sport, ev, info, best_here, kind, card_id, today))
            pool.append((ev, best_here, info))
    singles.sort(key=lambda p: -p["evPer100"])
    card["picks"] = singles[:C.MAX_SINGLES]
    for i, p in enumerate(card["picks"], 1):
        p["id"] = f"{card_id}-{i}"
    keep = {p["eventId"] + p["side"] for p in card["picks"]}
    card["parlays"] = build_parlays(sport, [x for x in pool if x[0]["id"] + x[1]["name"] in keep], card_id, today)
    card["underdogs"] = sorted(dogs, key=lambda d: -d["evPer100"])
    card["analysis"] = [{"event": label(ev, sport), "summary": S.sanitize(by_e.get(f"E{n}", {}).get("summary", "")),
                         "keyFactors": S.clean(by_e.get(f"E{n}", {}).get("keyFactors", [])[:5])} for n, ev in enumerate(board, 1)]
    if not card["picks"] and not card["parlays"]:
        best = max(near, key=lambda x: x[0]) if near else None
        card["noBet"] = ("No bet: nothing on this slate has value at the best Ontario price." +
                         (f" Closest was {sel_label(best[2]['market'], best[2]['name'], best[2]['point'])} ({label(best[1], sport)}) at "
                          f"{M.fmt_american(best[2]['dec'])}, expected value {best[0]*100:+.1f} per $100." if best else ""))
    msg = (f"{name}: {len(card['picks'])} value pick(s), {len(card['parlays'])} parlay(s) from {card['games']} events"
           if not card["noBet"] else f"{name}: no bet today ({card['games']} events checked)")
    return finish(st, lg, card, agent_id, msg)


def finish(st, lg, card, agent_id, msg):
    import report
    card = S.clean(card)
    lg["cards"] = [c for c in lg["cards"] if c.get("id") != card["id"]] + [{k: card[k] for k in ("id", "date", "sport", "games", "noBet") if k in card} | {"picks": len(card["picks"]), "parlays": len(card["parlays"])}]
    lg["picks"] = [p for p in lg["picks"] if p.get("cardId") != card["id"] or p.get("status") != "open"] + card["picks"] + card["parlays"]
    st.setdefault("cards", {})[card["sport"]] = card
    S.agent(st, agent_id, "ok", msg)
    S.agent(st, "value", "ok", f"Checked every side against the no-vig price: {len(card['picks']) + len(card['parlays'])} with value, {sum(1 for d in card['underdogs'] if d['value'])} value underdog(s)")
    S.log(st, "Court Analyst" if agent_id == "court" else "Fight Analyst", msg)
    S.save(S.LEDGER, lg)
    report.refresh(st, lg)
    print(msg)
