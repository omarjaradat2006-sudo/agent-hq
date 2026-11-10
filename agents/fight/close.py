"""Closing-line check: shortly before tip-off / the fights, re-price each open single at the same book.
Beating the closing price is the earliest honest sign the picks are any good (win rate needs hundreds of picks).
Optional: skipped automatically when Odds API credits run low."""
import datetime
import config as C
import oddsmath as M
import odds as O
import store as S


def run(sport):
    st, lg = S.state(), S.ledger()
    now = datetime.datetime.now(datetime.timezone.utc)
    soon = [p for p in lg["picks"] if p.get("sport") == sport and p.get("status") == "open" and not p.get("legs") and "close" not in p
            and 0 < (datetime.datetime.fromisoformat(p["commence"].replace("Z", "+00:00")) - now).total_seconds() < 6 * 3600]
    if not soon:
        print("close: nothing starting soon")
        return
    try:
        raw = O.fetch_odds(sport, 7, min_left=C.CLOSE_MIN_CREDITS)
    except O.LowCredits as e:
        S.log(st, "Odds Scout", str(e)); S.save(S.STATE, st); print(e); return
    ev = {e["id"]: e for e in raw}
    n = 0
    for p in soon:
        e = ev.get(p["eventId"])
        if not e:
            continue
        for b in O.clean_books(e):
            if b["key"] != p["book"]:
                continue
            for m in b.get("markets", []):
                if m["key"] != p["market"]:
                    continue
                for o in m.get("outcomes", []):
                    if o["name"] == p["side"] and (p["market"] == "h2h" or o.get("point") == p["point"]):
                        cd = float(o["price"])
                        p["close"] = {"dec": round(cd, 3), "american": M.fmt_american(cd), "at": S.now_iso(),
                                      "clvPct": round((p["dec"] / cd - 1) * 100, 2)}
                        n += 1
    msg = f"{C.SPORTS[sport]['name']}: closing prices for {n} of {len(soon)} pick(s)"
    S.agent(st, "odds", "ok", msg)
    S.log(st, "Odds Scout", msg)
    import report
    S.save(S.LEDGER, lg)
    report.refresh(st, lg)
    print(msg)
