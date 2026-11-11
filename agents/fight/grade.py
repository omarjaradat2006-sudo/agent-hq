"""Grades every posted parlay and underdog pick automatically.
NBA: ESPN's free public scoreboard + box score (team scores and player stats). Fallback: sourced Gemini search.
UFC: sourced Gemini search (winner, method, round, time). No result without a score or a source: it stays open and retries."""
import datetime, json, os, re, sys, unicodedata, urllib.request
from zoneinfo import ZoneInfo
import config as C
import oddsmath as M
import store as S

ESPN = "https://site.api.espn.com/apis/site/v2/sports/basketball/nba"
SETTLE_AFTER_H = 4
GIVE_UP_DAYS = 8
STATKEY = {"player_points": "PTS", "player_rebounds": "REB", "player_assists": "AST", "player_threes": "3PT"}


def norm(name):
    n = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode().lower()
    n = re.sub(r"\b(jr|sr|ii|iii|iv)\b", " ", n)
    return re.sub(r"[^a-z ]", " ", n).split()


def same_fighter(a, b):
    na, nb = norm(a), norm(b)
    return bool(na and nb) and (na[-1] == nb[-1] or na[-1] in nb or nb[-1] in na)


def same_player(a, b):
    na, nb = norm(a), norm(b)
    return bool(na and nb) and (na == nb or (na[-1] == nb[-1] and na[0][0] == nb[0][0]))


def _t(iso):
    return datetime.datetime.fromisoformat(str(iso).replace("Z", "+00:00"))


def _age_h(iso):
    return (datetime.datetime.now(datetime.timezone.utc) - _t(iso)).total_seconds() / 3600


def _json(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 agent-hq"}), timeout=30) as r:
        return json.loads(r.read().decode())


# ---------------- ESPN (NBA) ----------------

_board_cache, _box_cache = {}, {}


def espn_game(leg):
    day = _t(leg["commence"]).astimezone(ZoneInfo("America/New_York")).strftime("%Y%m%d")
    if day not in _board_cache:
        _board_cache[day] = _json(f"{ESPN}/scoreboard?dates={day}").get("events", [])
    for e in _board_cache[day]:
        comp = (e.get("competitions") or [{}])[0]
        teams = {c.get("homeAway"): c for c in comp.get("competitors", [])}
        h, a = teams.get("home", {}), teams.get("away", {})
        if h.get("team", {}).get("displayName") == leg["home"] and a.get("team", {}).get("displayName") == leg["away"]:
            done = (e.get("status") or {}).get("type", {}).get("completed")
            st = (e.get("status") or {}).get("type", {}).get("name", "")
            return {"id": e["id"], "completed": bool(done), "postponed": "POSTPONED" in st or "CANCELED" in st,
                    "home": int(float(h.get("score") or 0)), "away": int(float(a.get("score") or 0))}
    return None


def espn_box(gid):
    """{normalized player name tuple: {'PTS':..,'REB':..,'AST':..,'3PT':..,'played':bool}}"""
    if gid in _box_cache:
        return _box_cache[gid]
    out = {}
    for team in _json(f"{ESPN}/summary?event={gid}").get("boxscore", {}).get("players", []):
        for block in team.get("statistics", []):
            labels = block.get("labels") or block.get("names") or []
            for a in block.get("athletes", []):
                name = (a.get("athlete") or {}).get("displayName", "")
                stats = a.get("stats") or []
                if a.get("didNotPlay") or not stats:
                    out[name] = {"played": False}
                    continue
                row = dict(zip(labels, stats))
                try:
                    made3 = int(str(row.get("3PT", "0-0")).split("-")[0])
                    out[name] = {"played": True, "PTS": int(row.get("PTS", 0)), "REB": int(row.get("REB", 0)), "AST": int(row.get("AST", 0)), "3PT": made3}
                except ValueError:
                    out[name] = {"played": False}
    _box_cache[gid] = out
    return out


# ---------------- leg results ----------------

def over_under(val, side, pt):
    if val == pt:
        return "push"
    return "won" if (val > pt) == (side == "Over") else "lost"


def nba_leg(leg, home, away, box=None):
    mk, side, pt = leg["market"], leg["side"], leg.get("point")
    mine, theirs = (home, away) if side == leg["home"] else (away, home)
    if mk == "h2h":
        return "won" if mine > theirs else "lost"
    if mk in ("spreads", "alternate_spreads"):
        d = mine + float(pt) - theirs
        return "push" if d == 0 else "won" if d > 0 else "lost"
    if mk == "totals":
        return over_under(home + away, side, float(pt))
    if mk == "team_totals":
        return over_under(home if leg["team"] == leg["home"] else away, side, float(pt))
    if box is None:
        return None
    rec = next((v for k, v in box.items() if same_player(k, leg["player"])), None)
    if rec is None or not rec.get("played"):
        return "void"  # FanDuel/DraftKings void a prop when the player doesn't play
    return over_under(rec[STATKEY[leg["market"].replace("_alternate", "")]], side, float(pt))


def ufc_leg(leg, r):
    """r: {'winner','method','round','time','rounds'}"""
    w = str(r.get("winner") or "").lower()
    if leg["market"] == "h2h":
        if w in ("draw", "no contest", "nc") or not w:
            return "void"
        return "won" if same_fighter(r["winner"], leg["side"]) else "lost"
    if leg["market"] == "totals":
        try:
            if "decision" in str(r.get("method", "")).lower():
                mins = int(r.get("rounds") or 3) * 5
            else:
                m, s = str(r.get("time", "5:00")).split(":")
                mins = (int(r["round"]) - 1) * 5 + int(m) + int(s) / 60
        except (KeyError, ValueError, TypeError):
            return None
        return over_under(mins, leg["side"], float(leg["point"]) * 5)
    return None


def search(prompt):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import analyst as A
    try:
        text, src = A.gen(prompt, search=True, temperature=0)
    except Exception as e:
        print("result search failed:", e, flush=True)
        return None, None
    return (A.parse(text) or {}), (src[0][1] if src else None)


def ufc_result(leg):
    r, url = search(f"Search for the official result of the UFC fight {leg['away']} vs {leg['home']} around {str(leg['commence'])[:10]}. "
                    'Reply JSON only: {"status":"finished|cancelled|not_yet|unknown","winner":"exact name, or draw, or no contest",'
                    '"method":"KO/TKO|submission|decision|...","round":2,"time":"3:41","rounds":3}  (rounds = scheduled rounds)')
    if not r or not url:
        return None, None
    return r, url


def nba_search(leg):
    stat = f" and {leg['player']}'s {STATKEY.get(leg['market'].replace('_alternate', ''), '')} (made threes for 3PT)" if leg.get("player") else ""
    r, url = search(f"Search the final box score of the NBA game {leg['away']} at {leg['home']} on {str(leg['commence'])[:10]}: final score{stat}. "
                    'Reply JSON only: {"status":"finished|postponed|unknown","homeScore":0,"awayScore":0,"played":true,"stat":0}')
    return (r, url) if r and url else (None, None)


# ---------------- run ----------------

def settle_leg(sport, leg):
    if sport == "nba":
        try:
            g = espn_game(leg)
            if g and g["postponed"]:
                return "void", "ESPN: postponed"
            if g and g["completed"]:
                box = espn_box(g["id"]) if leg.get("player") else None
                leg["final"] = f"{leg['away']} {g['away']} - {g['home']} {leg['home']}"
                return nba_leg(leg, g["home"], g["away"], box), "ESPN box score"
        except Exception as e:
            print("ESPN failed:", e, flush=True)
        if _age_h(leg["commence"]) < 30:
            return None, None
        r, url = nba_search(leg)
        if not r or r.get("status") != "finished":
            return ("void", url) if r and r.get("status") == "postponed" else (None, None)
        try:
            h, a = int(r["homeScore"]), int(r["awayScore"])
        except (KeyError, TypeError, ValueError):
            return None, None
        box = None
        if leg.get("player"):
            box = {leg["player"]: {"played": bool(r.get("played")), STATKEY[leg["market"].replace("_alternate", "")]: r.get("stat")}} if r.get("stat") is not None or not r.get("played") else None
            if box is None:
                return None, None
        return nba_leg(leg, h, a, box), f"search: {url}"
    r, url = ufc_result(leg)
    if not r:
        return None, None
    if r.get("status") == "cancelled":
        return "void", f"search: {url}"
    if r.get("status") != "finished":
        return None, None
    leg["final"] = f"{r.get('winner')} by {r.get('method')}" + (f", round {r.get('round')} {r.get('time')}" if r.get("round") else "")
    leg["method"], leg["winner"] = str(r.get("method") or ""), str(r.get("winner") or "")
    return ufc_leg(leg, r), f"search: {url}"


def settle_bet(b):
    sts = [l.get("status", "open") for l in b["legs"]]
    if "lost" in sts:
        b.update(status="lost", profit=-100.0, settledAt=S.now_iso())
    elif "unresolved" in sts:
        b.update(status="unresolved")
    elif all(s in ("won", "push", "void") for s in sts):
        won = [l["dec"] for l in b["legs"] if l["status"] == "won"]
        if not won:
            b.update(status="push", profit=0.0, settledAt=S.now_iso())
        else:
            d = M.parlay_decimal(won)
            b.update(status="won", settledDec=round(d, 3), profit=M.profit_per_100("win", d), settledAt=S.now_iso())


def run():
    import report
    st, lg = S.state(), S.ledger()
    open_bets = [b for b in lg["bets"] if b.get("status") == "open"]
    n = 0
    for b in open_bets:
        for leg in b["legs"]:
            if leg.get("status", "open") != "open" or _age_h(leg["commence"]) < SETTLE_AFTER_H:
                continue
            res, how = settle_leg(b["sport"], leg)
            if res:
                leg.update(status=res, gradedBy=how); n += 1
            elif _age_h(leg["commence"]) > GIVE_UP_DAYS * 24:
                leg["status"] = "unresolved"
        settle_bet(b)
    still = sum(b.get("status") == "open" for b in lg["bets"])
    msg = f"Graded {n} leg(s); {still} bet(s) still waiting on games" if n else f"Nothing final yet ({still} bet(s) open)"
    S.agent(st, "grader", "ok", msg); S.log(st, "Results Grader", msg)
    S.save(S.LEDGER, lg)
    report.refresh(st, lg)
    print(msg)
