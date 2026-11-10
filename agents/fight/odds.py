"""The Odds API client (stdlib only), FanDuel + DraftKings only. Read-only: odds and events.
Every leg we post comes from this feed for that exact book, so it was a real, listed market at posting time."""
import calendar, datetime, json, os, time, urllib.parse, urllib.request, urllib.error
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


def credits():
    try:
        with open(CREDITS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_credits(h, label):
    c = credits()
    if h.get("x-requests-remaining") is not None:
        c["remaining"] = int(float(h["x-requests-remaining"]))
    if h.get("x-requests-used") is not None:
        c["used"] = int(float(h["x-requests-used"]))
    c["last"] = {"call": label, "cost": h.get("x-requests-last"), "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    os.makedirs(C.DATA, exist_ok=True)
    with open(CREDITS_FILE, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=1)


def _get(path, params, cost, label):
    have = credits().get("remaining")
    if cost and have is not None and have - cost < C.CREDIT_RESERVE:
        raise LowCredits(f"Only {have} Odds API credits left this month; skipped {label}")
    url = f"{C.ODDS_BASE}/{path}?{urllib.parse.urlencode(dict(params, apiKey=key()))}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "agent-hq-fight/2"}), timeout=40) as r:
                body = json.loads(r.read().decode())
                _save_credits({k.lower(): v for k, v in r.headers.items()}, label)
                return body
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:200]
            if e.code in (401, 403):
                raise NoKey(f"The Odds API refused the key ({e.code}): {msg}")
            if e.code == 404:
                return []
            if e.code == 422:
                raise RuntimeError(f"Odds API rejected the request: {msg}")
            if attempt == 2:
                raise
            time.sleep(5)
        except urllib.error.URLError:
            if attempt == 2:
                raise
            time.sleep(5)


def _window(hours):
    now = time.time()
    f = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))
    return {"commenceTimeFrom": f(now - 1800), "commenceTimeTo": f(now + hours * 3600)}


def books_param():
    return ",".join(k for k in C.BOOKS if not C.BANNED.search(k))


def fetch_sports():
    return _get("sports", {}, 0, "sports list (free)")


def fetch_events(sport_key, hours):
    """Free: /events costs no credits."""
    return _get(f"sports/{sport_key}/events", _window(hours), 0, "events (free)") or []


def fetch_odds(sport_key, markets, hours):
    return _get(f"sports/{sport_key}/odds", dict(_window(hours), bookmakers=books_param(), markets=",".join(markets), oddsFormat="decimal"),
                len(markets), f"{sport_key} {','.join(markets)} ({len(markets)} credits)") or []


def fetch_event_odds(sport_key, event_id, markets):
    """Player props / team totals for one game. Costs [markets returned] credits."""
    return _get(f"sports/{sport_key}/events/{event_id}/odds", {"bookmakers": books_param(), "markets": ",".join(markets), "oddsFormat": "decimal"},
                len(markets), f"props for one game (up to {len(markets)} credits)") or {}


def daily_prop_budget(main_cost=3, per_game=len(C.NBA_PROPS)):
    """How many games can get props today without running out before the month resets."""
    have = credits().get("remaining")
    if have is None:
        return 99
    now = datetime.datetime.now(datetime.timezone.utc)
    days_left = calendar.monthrange(now.year, now.month)[1] - now.day + 1
    per_day = (have - C.CREDIT_RESERVE - 4 * 3) / max(days_left, 1) - main_cost  # 4*3 = UFC Fridays left (roughly)
    return max(0, int(per_day // per_game))


# ---------- normalise into candidate legs ----------

def _short(odds):
    return abs(M.decimal_to_american(odds)) > C.MAX_ABS_ODDS


def candidates(event, sport):
    """All legs for one event, one entry per (market, player/team, side, point), with each book's price
    and the no-vig fair chance. Only FanDuel and DraftKings; anything else (incl. Bet365) is dropped."""
    groups, out = {}, {}
    for b in event.get("bookmakers", []):
        bk = b.get("key")
        if bk not in C.BOOKS or C.BANNED.search(bk or "") or C.BANNED.search(b.get("title", "")):
            continue
        for m in b.get("markets", []):
            mk = m["key"]
            for o in m.get("outcomes", []):
                who = o.get("description")
                pt = o.get("point")
                gkey = (bk, mk, who, abs(pt) if (mk == "spreads" and pt is not None) else pt)
                groups.setdefault(gkey, []).append(o)
    for (bk, mk, who, _), outs in groups.items():
        fair = M.no_vig([o["price"] for o in outs]) if len(outs) == 2 else [None] * len(outs)
        for o, f in zip(outs, fair):
            side, pt = o["name"], o.get("point")
            cid = "|".join(str(x) for x in (event["id"], mk, who or "", side, "" if pt is None else pt))
            c = out.setdefault(cid, {"id": cid, "sport": sport, "eventId": event["id"], "home": event["home_team"], "away": event["away_team"],
                                     "commence": event.get("commence_time"), "market": mk, "player": who if mk.startswith("player_") else None,
                                     "team": who if mk == "team_totals" else None, "side": side, "point": pt, "prices": {}, "fairs": {}})
            if not _short(o["price"]):
                c["prices"][bk] = float(o["price"])
                if f is not None:
                    c["fairs"][bk] = f
    res = []
    for c in out.values():
        if not c["prices"]:
            continue
        c["fair"] = round(sum(c["fairs"].values()) / len(c["fairs"]), 4) if c["fairs"] else round(min(M.implied(d) for d in c["prices"].values()), 4)
        del c["fairs"]
        res.append(c)
    return res
