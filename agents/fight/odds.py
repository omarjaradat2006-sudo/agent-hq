"""The Odds API client (stdlib only). Free plan: 500 credits a month, no card.
Only Ontario-licensed books are requested (by name, so 10 books cost 1 region). Bet365 is never
requested and is dropped if it ever shows up. Read-only: odds and scores, nothing else."""
import json, math, os, time, urllib.parse, urllib.request, urllib.error
from collections import Counter
import config as C
import oddsmath as M

CREDITS_FILE = os.path.join(C.DATA, "credits.json")


class NoKey(Exception):
    pass


class LowCredits(Exception):
    pass


def key():
    k = (os.environ.get("ODDS_API_KEY") or "").strip()
    if not k:
        raise NoKey("ODDS_API_KEY is not set on the server")
    return k


def active_books():
    """Ontario-licensed books in use right now (config + the weekly licence check), never Bet365."""
    over = {}
    try:
        over = json.load(open(os.path.join(C.DATA, "books.json"), encoding="utf-8")).get("overrides", {})
    except Exception:
        pass
    out = {}
    for k, b in C.BOOKS.items():
        on = over.get(k, {}).get("on", b["on"])
        if on and not C.BANNED.search(k) and not C.BANNED.search(b["name"]):
            out[k] = b
    return out


def credits():
    try:
        return json.load(open(CREDITS_FILE, encoding="utf-8"))
    except Exception:
        return {}


def _save_credits(h, cost_label):
    c = credits()
    rem, used = h.get("x-requests-remaining"), h.get("x-requests-used")
    if rem is not None:
        c["remaining"] = int(float(rem))
    if used is not None:
        c["used"] = int(float(used))
    c["last"] = {"call": cost_label, "cost": h.get("x-requests-last"), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    os.makedirs(C.DATA, exist_ok=True)
    json.dump(c, open(CREDITS_FILE, "w", encoding="utf-8"), indent=1)
    return c


def _get(path, params, cost, label, min_left=None):
    have = credits().get("remaining")
    floor = C.CREDIT_RESERVE if min_left is None else min_left
    if have is not None and have - cost < floor:
        raise LowCredits(f"Only {have} Odds API credits left this month; skipped {label} (needs {cost}, keeps {floor} in reserve)")
    params = dict(params, apiKey=key())
    url = f"{C.ODDS_BASE}/{path}?{urllib.parse.urlencode(params)}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "agent-hq-fight/1"}), timeout=40) as r:
                body = json.loads(r.read().decode())
                _save_credits({k.lower(): v for k, v in r.headers.items()}, label)
                return body
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:200]
            if e.code in (401, 403):
                raise NoKey(f"The Odds API refused the key ({e.code}): {msg}")
            if e.code == 429 and attempt < 2:
                time.sleep(5); continue
            if e.code == 422:
                raise RuntimeError(f"Odds API rejected the request: {msg}")
            if attempt == 2:
                raise
            time.sleep(5)
        except urllib.error.URLError:
            if attempt == 2:
                raise
            time.sleep(5)


def odds_cost(markets, nbooks):
    return len(markets) * max(1, math.ceil(nbooks / 10))


def fetch_odds(sport, hours_ahead=36, min_left=None):
    """Raw events from /odds for the Ontario books. Costs markets x ceil(books/10) credits."""
    s = C.SPORTS[sport]
    books = active_books()
    cost = odds_cost(s["markets"], len(books))
    now = time.time()
    params = {
        "bookmakers": ",".join(books), "markets": ",".join(s["markets"]), "oddsFormat": "decimal",
        "commenceTimeFrom": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 3600)),
        "commenceTimeTo": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + hours_ahead * 3600)),
    }
    return _get(f"sports/{s['key']}/odds", params, cost, f"{sport} odds ({cost} credits)", min_left)


def fetch_events(sport, hours_ahead=36):
    """Upcoming events. Free: The Odds API doesn't charge credits for /events."""
    s = C.SPORTS[sport]
    now = time.time()
    params = {"commenceTimeFrom": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - 3600)),
              "commenceTimeTo": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now + hours_ahead * 3600))}
    return _get(f"sports/{s['key']}/events", params, 0, f"{sport} events (free)", min_left=0)


def fetch_scores(sport, days_from=3):
    s = C.SPORTS[sport]
    return _get(f"sports/{s['key']}/scores", {"daysFrom": days_from}, 2, f"{sport} scores (2 credits)")


def clean_books(event):
    """Drop Bet365 and any book that isn't on the active Ontario list."""
    allowed = active_books()
    return [b for b in event.get("bookmakers", [])
            if b.get("key") in allowed and not C.BANNED.search(b.get("key", "")) and not C.BANNED.search(b.get("title", ""))]


def _too_long(d):
    return abs(M.decimal_to_american(d)) > C.MAX_ABS_ODDS


def build_lines(event):
    """Turn one raw event into comparable lines.
    Returns list of lines: {market, point, outcomes: [{name, point, prices: {book: dec}, best: (book, dec), fair}]}.
    Spreads and totals use the point offered by the most books, so every price compared is for the same line.
    fair = Pinnacle's no-vig probability when Pinnacle has the line, else the average no-vig across books."""
    books = clean_books(event)
    by_market = {}
    for b in books:
        for m in b.get("markets", []):
            by_market.setdefault(m["key"], []).append((b["key"], m.get("outcomes", [])))
    lines = []
    for mk, rows in by_market.items():
        if mk == "h2h":
            pick_point = None
        else:
            pts = Counter()
            for _, outs in rows:
                for o in outs:
                    if o.get("point") is not None and (mk == "totals" and o["name"] == "Over" or mk == "spreads" and o["name"] == event.get("home_team")):
                        pts[o["point"]] += 1
            if not pts:
                continue
            pick_point = pts.most_common(1)[0][0]
        names, prices, fairs = [], {}, {}
        for bk, outs in rows:
            sel = outs if mk == "h2h" else [o for o in outs if (o["name"] in ("Over", "Under") and o.get("point") == pick_point)
                                                 or (mk == "spreads" and o["name"] == event.get("home_team") and o.get("point") == pick_point)
                                                 or (mk == "spreads" and o["name"] == event.get("away_team") and o.get("point") == -pick_point)]
            if len(sel) != len(outs if mk == "h2h" else [1, 1]) or len(sel) < 2:
                continue  # book doesn't have the full market at this line
            fv = M.no_vig([o["price"] for o in sel])
            for o, f in zip(sel, fv):
                n = o["name"]
                if n not in names:
                    names.append(n)
                prices.setdefault(n, {})[bk] = float(o["price"])
                fairs.setdefault(n, {})[bk] = f
        if len(names) < 2:
            continue
        outcomes = []
        for n in names:
            pr = {b: d for b, d in prices.get(n, {}).items() if not _too_long(d)}
            if not pr:
                continue
            best_book = max(pr, key=pr.get)
            fb = fairs.get(n, {})
            fair = fb["pinnacle"] if "pinnacle" in fb else sum(fb.values()) / len(fb)
            pt = None if mk == "h2h" else (pick_point if (mk == "totals" or n == event.get("home_team")) else -pick_point)
            outcomes.append({"name": n, "point": pt, "prices": pr, "best": [best_book, pr[best_book]], "fair": round(fair, 4),
                             "fairSource": "Pinnacle no-vig" if "pinnacle" in fb else f"average of {len(fb)} books, no-vig"})
        if len(outcomes) >= 2:
            lines.append({"market": mk, "point": pick_point, "outcomes": outcomes})
    return lines


def board(raw_events):
    """Compact, comparable board for the analyst and the site."""
    out = []
    for e in raw_events or []:
        lines = build_lines(e)
        if lines:
            out.append({"id": e["id"], "commence": e.get("commence_time"), "home": e.get("home_team"), "away": e.get("away_team"), "lines": lines})
    return out
