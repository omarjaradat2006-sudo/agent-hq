"""Settles every open pick automatically: The Odds API scores first, then a sourced Gemini search
for anything the scores feed doesn't cover (UFC results, late games). Nothing is guessed:
a result without a score or a source stays open and is retried the next day."""
import datetime, os, sys
import config as C
import oddsmath as M
import odds as O
import store as S
from picks import same_fighter, SYSTEM

sys.path.insert(0, os.path.join(C.ROOT, "agents", "gemini"))
import gemini as G  # noqa: E402

SETTLE_AFTER_H = 4      # hours after the start before trying to settle
GIVE_UP_DAYS = 8        # then mark "unresolved" (kept out of the record) and say so


def _t(iso):
    return datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))


def _age_h(iso):
    return (datetime.datetime.now(datetime.timezone.utc) - _t(iso)).total_seconds() / 3600


def leg_result(leg, home, away, winner=None):
    """win / loss / push for one selection. home/away are final scores (NBA) or None (UFC with winner)."""
    mk, side, pt = leg["market"], leg["side"], leg.get("point")
    if winner is not None:  # fight result
        w = str(winner).lower()
        if w in ("draw", "no contest", "nc", "majority draw", "split draw"):
            return "push"
        return "win" if same_fighter(winner, side) else "loss"
    if mk == "h2h":
        mine, theirs = (home, away) if side == leg["home"] else (away, home)
        return "win" if mine > theirs else "loss" if mine < theirs else "push"
    if mk == "spreads":
        mine, theirs = (home, away) if side == leg["home"] else (away, home)
        diff = mine + float(pt) - theirs
        return "win" if diff > 0 else "loss" if diff < 0 else "push"
    total = home + away
    if side == "Over":
        return "win" if total > float(pt) else "loss" if total < float(pt) else "push"
    return "win" if total < float(pt) else "loss" if total > float(pt) else "push"


def search_result(sport, leg):
    """Sourced result lookup. Returns ('finished', home, away, winner) / ('cancelled',...) / None."""
    day = str(leg["commence"])[:10]
    if sport == "ufc":
        q = (f"Search for the official result of the UFC fight {leg['away']} vs {leg['home']} (around {day}). "
             'Reply JSON only: {"status":"finished|cancelled|not_yet|unknown","winner":"exact fighter name, or draw, or no contest","method":"KO/TKO, submission, decision..."}')
    else:
        q = (f"Search for the final score of the NBA game {leg['away']} at {leg['home']} on or around {day}. "
             'Reply JSON only: {"status":"finished|postponed|not_yet|unknown","homeScore":0,"awayScore":0}')
    try:
        text, src = G.generate(q, SYSTEM, search=True, temperature=0)
        r = G.parse_json(text)
    except Exception as e:
        print("result search failed:", e, flush=True)
        return None
    if not src:  # no source, no result
        return None
    status = str(r.get("status", "")).lower()
    url = src[0][1]
    if status in ("cancelled", "postponed"):
        return ("cancelled", None, None, None, url)
    if status != "finished":
        return None
    if sport == "ufc":
        w = r.get("winner")
        if not w or not (same_fighter(w, leg["home"]) or same_fighter(w, leg["away"]) or str(w).lower() in ("draw", "no contest", "nc")):
            return None
        return ("finished", None, None, w, url)
    try:
        return ("finished", int(r["homeScore"]), int(r["awayScore"]), None, url)
    except (KeyError, TypeError, ValueError):
        return None


def run():
    st, lg = S.state(), S.ledger()
    open_picks = [p for p in lg["picks"] if p.get("status") == "open"]
    legs_by_sport = {}
    for p in open_picks:
        for leg in (p.get("legs") or [p]):
            if leg.get("status", "open") == "open" and _age_h(leg["commence"]) >= SETTLE_AFTER_H:
                legs_by_sport.setdefault(p["sport"], []).append(leg)
    if not legs_by_sport:
        S.agent(st, "grader", "ok", f"Nothing to settle yet ({len(open_picks)} open pick(s) still to play)")
        return _done(st, lg, 0)
    scores = {}
    for sport in legs_by_sport:
        try:
            for e in O.fetch_scores(sport, 3) or []:
                if e.get("completed") and e.get("scores"):
                    sc = {x["name"]: int(float(x["score"])) for x in e["scores"] if x.get("score") not in (None, "")}
                    if e.get("home_team") in sc and e.get("away_team") in sc:
                        scores[e["id"]] = (sc[e["home_team"]], sc[e["away_team"]])
        except (O.LowCredits, O.NoKey) as e:
            S.log(st, "Results Grader", str(e))
    settled = 0
    for sport, legs in legs_by_sport.items():
        for leg in legs:
            res = None
            if leg.get("eventId") in scores:
                h, a = scores[leg["eventId"]]
                res = leg_result(leg, h, a)
                leg["finalScore"] = f"{leg['away']} {a} - {h} {leg['home']}"
                leg["gradedBy"] = "The Odds API scores"
            elif sport == "ufc" or _age_h(leg["commence"]) > 30:
                r = search_result(sport, leg)
                if r and r[0] == "cancelled":
                    res = "void"; leg["gradedBy"] = "search: cancelled/postponed"; leg["resultSource"] = r[4]
                elif r:
                    res = leg_result(leg, r[1], r[2], r[3])
                    leg["finalScore"] = f"{r[3]} won" if r[3] else f"{leg['away']} {r[2]} - {r[1]} {leg['home']}"
                    leg["gradedBy"] = "search with source"; leg["resultSource"] = r[4]
            if res:
                leg["status"] = {"win": "won", "loss": "lost"}.get(res, res)
                settled += 1
            elif _age_h(leg["commence"]) > GIVE_UP_DAYS * 24:
                leg["status"] = "unresolved"
    for p in open_picks:
        _settle_pick(p)
    msg = f"Settled {settled} result(s)" if settled else "Results not final yet; will retry tomorrow"
    S.agent(st, "grader", "ok", msg)
    S.log(st, "Results Grader", msg)
    return _done(st, lg, settled)


def _settle_pick(p):
    legs = p.get("legs")
    if not legs:  # single: its own status was set above
        if p["status"] in ("won", "lost", "push", "void"):
            p["result"] = p["status"]
            p["profit"] = M.profit_per_100({"won": "win", "lost": "loss"}.get(p["status"], "push"), p["dec"])
            p["settledAt"] = S.now_iso()
        return
    sts = [l.get("status", "open") for l in legs]
    if "lost" in sts:
        p.update(status="lost", result="lost", profit=-100.0, settledAt=S.now_iso())
    elif "unresolved" in sts:
        p.update(status="unresolved")
    elif all(s in ("won", "push", "void") for s in sts):
        won = [l["dec"] for l in legs if l["status"] == "won"]
        if not won:
            p.update(status="push", result="push", profit=0.0, settledAt=S.now_iso())
        else:
            d = M.parlay_decimal(won)
            p.update(status="won", result="won", settledDec=round(d, 3), profit=M.profit_per_100("win", d), settledAt=S.now_iso())


def _done(st, lg, settled):
    import report
    S.save(S.LEDGER, lg)
    report.refresh(st, lg)
    print(f"grade: settled {settled}")
