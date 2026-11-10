"""Builds the 3 parlays (+100 / +500 / +1000). Rules that keep every slip placeable:
- every leg is on ONE book (FanDuel or DraftKings) and came from that book's live odds feed
- at most ONE leg per game/fight -> a standard parlay; no same-game combos the app could block or reprice
- total odds = the legs' odds multiplied (how both apps price a standard parlay)"""
import itertools
import config as C
import oddsmath as M
import wording as W


def chance(c):
    return M.blend(c["fair"], c.get("model"), C.MODEL_WEIGHT)


def strength(ch, ev, all_analyzed):
    if ev >= 0.08 and all_analyzed and ch >= 0.12:
        return "Strong"
    if ev >= 0:
        return "Medium"
    return "Long shot"


def _pool(legs, book):
    analyzed = [c for c in legs if book in c["prices"] and c.get("model") is not None]
    for c in analyzed:
        c["_edge"] = chance(c) - M.implied(c["prices"][book])
    ok = [c for c in analyzed if c["_edge"] > -0.02]
    pool = sorted(ok, key=lambda c: -c["_edge"])[:12]                     # best value
    pool += [c for c in sorted(ok, key=lambda c: -chance(c)) if c not in pool][:8]   # most likely (needed for the +100 slip)
    if len({c["eventId"] for c in pool}) < 4:  # thin slate: fill with the market's own favourites, clearly un-analyzed
        extra = sorted([c for c in legs if book in c["prices"] and c.get("model") is None and c["market"] in ("h2h", "spreads", "totals")],
                       key=lambda c: -c["fair"])[:8]
        for c in extra:
            c["_edge"] = c["fair"] - M.implied(c["prices"][book])
        pool += extra
    return pool


def _best(pools, lo, hi, avoid):
    best = None
    for book, pool in pools.items():
        for n in range(2, C.MAX_LEGS + 1):  # 2+ legs: it has to be a real parlay
            for combo in itertools.combinations(pool, n):
                if len({c["eventId"] for c in combo}) < n:
                    continue
                dec = M.parlay_decimal([c["prices"][book] for c in combo])
                if not lo <= dec <= hi:
                    continue
                ch = M.parlay_prob([chance(c) for c in combo])
                ev = M.ev(ch, dec)
                reuse = sum(c["id"] in avoid for c in combo)
                score = ev - 0.04 * reuse + 0.01 * sum(c.get("model") is not None for c in combo)
                if best is None or score > best[0]:
                    best = (score, book, combo, dec, ch, ev)
    return best


def build(legs, sport, card_id, today):
    pools = {b: _pool(legs, b) for b in C.BOOKS}
    out, used = [], set()
    for tier, lo, hi in C.TARGETS:
        found = _best(pools, lo, hi, used) or _best(pools, lo * 0.85, hi * 1.25, used)
        if not found:
            continue
        _, book, combo, dec, ch, ev = found
        used |= {c["id"] for c in combo}
        analyzed = all(c.get("model") is not None for c in combo)
        out.append({
            "id": f"{card_id}-{tier.strip('+')}", "cardId": card_id, "date": today, "sport": sport, "kind": f"{sport}_parlay", "tier": tier,
            "book": book, "bookName": C.BOOKS[book], "dec": round(dec, 3), "american": W.american(dec),
            "chancePct": round(ch * 100, 1), "impliedPct": round(100 / dec, 1), "evPer100": round(ev * 100, 2),
            "strength": strength(ch, ev, analyzed), "why": "", "status": "open",
            "commence": min(c["commence"] for c in combo),
            "legs": [leg_row(c, book) for c in sorted(combo, key=lambda c: c["commence"])],
        })
    return out


def leg_row(c, book):
    d = c["prices"][book]
    return {"text": W.leg_text(c, book), "american": W.american(d), "dec": round(d, 3), "where": W.where(c, book),
            "why": c.get("why") or "No research edge; included as the market favourite to reach the target odds.",
            "analyzed": c.get("model") is not None, "chancePct": round(chance(c) * 100, 1), "impliedPct": round(100 / d, 1),
            "fairPct": round(c["fair"] * 100, 1), "eventId": c["eventId"], "market": c["market"], "side": c["side"],
            "point": c.get("point"), "player": c.get("player"), "team": c.get("team"), "home": c["home"], "away": c["away"],
            "commence": c["commence"], "status": "open"}
