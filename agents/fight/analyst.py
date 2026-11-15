"""Gemini research and probability estimates (free tier, Google Search grounding). No Claude."""
import os, re, sys
import config as C
import oddsmath as M
import wording as W

# Own key (a separate free Google AI Studio project) so the video and trading jobs can't use up its quota.
# Uses GEMINI_API_KEY_FIGHT if set, otherwise falls back to the shared GEMINI_API_KEY.
_own = (os.environ.get("GEMINI_API_KEY_FIGHT") or os.environ.get("FIGHT_GEMINI_API_KEY") or "").strip()
if _own:
    os.environ["GEMINI_API_KEY"] = _own
KEY_SOURCE = "own key (GEMINI_API_KEY_FIGHT)" if _own else "shared key (GEMINI_API_KEY)"
sys.path.insert(0, os.path.join(C.ROOT, "agents", "gemini"))
import gemini as G  # noqa: E402

SYSTEM = """You are a sports research analyst on "Fight & Court Intelligence", a research tool used by one adult in Ontario, Canada who makes his own decisions with his own money.
You research NBA games and UFC fights and estimate honest probabilities.
Rules:
- Research and analysis only. Never suggest stake sizes, budgets, bankroll plans or deposits.
- Never call anything a lock, guaranteed, basically guaranteed, a sure thing, safe or free money. Every outcome is uncertain.
- Never mention, use or compare Bet365.
- Use only facts from your research. Never invent injuries, stats, quotes, results or news. If unsure, say so.
- Having no view is fine: leave a line out instead of guessing.
- Plain English, short sentences."""


SEARCH_OK = True   # turns False for the rest of the run once Google Search is out of free quota


def gen(prompt, search=False, json_out=False, temperature=0.2, fallback=""):
    """One retry round only, so a bad quota day can't burn the whole daily allowance.
    If Google Search is out of quota, answer without search, using `fallback` (e.g. ESPN's injury report) as the facts."""
    global SEARCH_OK
    if search and SEARCH_OK:
        try:
            return G.generate(prompt, SYSTEM, search=True, json_out=False, temperature=temperature, retries=1)
        except RuntimeError as e:
            if "429" not in str(e):
                raise
            SEARCH_OK = False
            print("Google Search grounding is out of free quota; continuing without search", flush=True)
    if search:
        prompt = (f"{prompt}\n\nNOTE: live web search is unavailable right now. Use ONLY these facts for current news and say so:\n"
                  f"{fallback or '(no live data available; give general matchup analysis only and do not state any injury as current)'}")
    return G.generate(prompt, SYSTEM, search=False, json_out=json_out, temperature=temperature, retries=1)


def parse(text):
    try:
        return G.parse_json(text)
    except Exception:
        return None


def json_call(prompt, tries=2):
    for _ in range(tries):
        try:
            text, _ = gen(prompt, json_out=True)
            out = parse(text)
            if isinstance(out, dict):
                return out
        except Exception as e:
            print("gemini retry:", e, flush=True)
    return {}


# ---------- lines shown to the model ----------

def lines(cands):
    """Group the two sides of each line; returns (text, {line_id: {side: candidate}})."""
    groups = {}
    for c in cands:
        who = c.get("player") or c.get("team") or ""
        pt = abs(c["point"]) if (c["market"] in ("spreads", "alternate_spreads") and c["point"] is not None) else c["point"]
        groups.setdefault((c["eventId"], c["market"], who, pt), []).append(c)
    rows, idx = [], {}
    for n, ((eid, mk, who, pt), cs) in enumerate(sorted(groups.items(), key=lambda kv: (kv[1][0]["commence"] or "", str(kv[0]))), 1):
        lid = f"L{n}"
        idx[lid] = {c["side"]: c for c in cs}
        parts = []
        for c in cs:
            pr = " ".join(f"{C.BOOKS[b][:2]} {W.american(d)}" for b, d in c["prices"].items())
            parts.append(f"{c['side']}{'' if c['point'] is None or mk == 'totals' or mk.startswith('player') or mk == 'team_totals' else ' ' + format(c['point'], '+g')} [{pr}] fair {c['fair']*100:.0f}%")
        label = {"h2h": "Winner", "spreads": "Spread", "alternate_spreads": "Alternate spread (big cushion)", "totals": "Game total" if cs[0]["sport"] == "nba" else "Total rounds",
                 "team_totals": f"{who} team total", "player_points": f"{who} points", "player_rebounds": f"{who} rebounds",
                 "player_assists": f"{who} assists", "player_threes": f"{who} threes",
                 "player_points_alternate": f"{who} points milestone (Over {pt} = {int((pt or 0) + 0.5)}+ points)"}.get(mk, mk)
        line_pt = "" if pt is None or mk in ("h2h", "spreads", "alternate_spreads") else f" {pt:g}"
        rows.append(f"{lid} | {W.game(cs[0])} | {label}{line_pt} | " + " | ".join(parts))
    return "\n".join(rows), idx


def apply_estimates(est, idx):
    """Attach model chance + reason to candidates. One side's chance implies the other's."""
    n = 0
    for e in (est or {}).get("picks", []):
        if not isinstance(e, dict):
            continue
        grp = idx.get(str(e.get("id")))
        try:
            p = float(e.get("prob"))
        except (TypeError, ValueError):
            continue
        if not grp or not 0.02 < p < 0.98:
            continue
        side = str(e.get("side", ""))
        hit = next((s for s in grp if s.lower() == side.lower()), None) or next((s for s in grp if W.short(s).lower() == side.lower() or s.lower() in side.lower()), None)
        if not hit:
            continue
        grp[hit]["model"], grp[hit]["why"] = p, str(e.get("why", ""))[:220]
        others = [s for s in grp if s != hit]
        if len(others) == 1 and grp[others[0]].get("model") is None:
            grp[others[0]]["model"], grp[others[0]]["why"] = 1 - p, f"Other side of: {e.get('why', '')}"[:220]
            grp[others[0]]["derived"] = True   # never put on a slip: the research didn't choose this side
        n += 1
    return n


# ---------- NBA ----------

def espn_injuries():
    """ESPN's free public NBA injury report (no key). Used when Google Search is unavailable."""
    import json as _j, urllib.request as _u
    try:
        with _u.urlopen(_u.Request("https://site.api.espn.com/apis/site/v2/sports/basketball/nba/injuries",
                                   headers={"User-Agent": "Mozilla/5.0 agent-hq"}), timeout=30) as r:
            data = _j.loads(r.read().decode())
    except Exception as e:
        print("ESPN injuries unavailable:", e, flush=True)
        return ""
    rows = []
    for team in data.get("injuries", []):
        tname = team.get("displayName") or (team.get("team") or {}).get("displayName", "")
        for i in team.get("injuries", []):
            ath = (i.get("athlete") or {}).get("displayName", "")
            st = i.get("status") or (i.get("type") or {}).get("description", "")
            note = (i.get("shortComment") or i.get("longComment") or "")[:140]
            if ath:
                rows.append(f"{tname}: {ath} - {st}. {note}")
    return "ESPN NBA injury report (official, current):\n" + "\n".join(rows[:150]) if rows else ""


def nba_research(today, games):
    q = (f"Today is {today}. Research tonight's NBA games below for betting analysis: official injury report (out / questionable / probable), "
         "rest and back-to-backs, travel, recent form (last 10 games), pace, offensive and defensive ratings, matchup edges, "
         "and line-moving news from the last 24 hours. Also note which players' roles change because of injuries.\n"
         + "\n".join(games) +
         "\nEnd with one line exactly like: PROP_GAMES: <game>; <game>; ... listing the games with the most player-prop angles first.")
    text, src = gen(q, search=True, temperature=0.3, fallback=espn_injuries())
    m = re.search(r"PROP_GAMES:\s*(.+)", text or "")
    ranked = [g.strip() for g in m.group(1).split(";")] if m else []
    return text, src, ranked


def nba_props_research(today, players_by_game):
    q = (f"Today is {today}. For these NBA players with prop lines tonight, find each one's last 5-10 games (points, rebounds, assists, made threes, minutes), "
         "season averages, tonight's role (starting? minutes limit? teammates out?) and the opponent's defense against their position. Be specific.\n"
         + "\n".join(f"{g}: {', '.join(ps[:10])}" for g, ps in players_by_game.items()))
    return gen(q, search=True, temperature=0.3, fallback=espn_injuries())


def estimate(sport, lines_text, notes, sources, today, extra=""):
    src = "\n".join(f"- {t}: {u}" for t, u in sources[:30])
    p = f"""Today is {today}. Below is every {sport.upper()} line currently listed on FanDuel (Fa) and DraftKings (Dr), with the market's fair (no-vig) chance.

{lines_text[:30000]}

Research notes:
{notes[:16000]}
{extra[:8000]}

Sources:
{src}

{"These lines will be combined into SAME-GAME parlays (2-5 legs from one game), so prefer legs that fit one believable game script and avoid legs that contradict each other. There are NO moneylines or regular spreads (Omar's rule); alternate spreads shown are only big-cushion ones." if sport == "nba" else ""}
Pick up to 45 lines where the research gives you a concrete, specific reason to disagree with or confirm the market, and estimate the TRUE chance of the side you'd choose.
- Start from the fair chance and move only for specific reasons (injury, role change, rest, matchup, recent form, weigh-in, style).
- Moves above 10 points need a strong specific reason.
- "why" must be one short plain sentence a casual fan understands, with the specific reason (e.g. "Davis is out, so Lakers lose their best rebounder").
Return JSON only: {{"picks":[{{"id":"L12","side":"exact side name as shown (team, fighter, Over or Under)","prob":0.58,"why":"..."}}]}}"""
    return json_call(p)


# ---------- UFC ----------

def espn_ufc_cards(days=4):
    """Official UFC schedule from ESPN's free API (UFC only; PFL/Bellator/ONE are separate leagues there).
    Returns list of {"name","date","bouts":[[a,b],...]} or None if ESPN couldn't be reached."""
    import datetime as _d, json as _j, urllib.request as _u
    t = _d.date.today()
    rng = f"{t:%Y%m%d}-{t + _d.timedelta(days=days):%Y%m%d}"
    try:
        with _u.urlopen(_u.Request(f"https://site.api.espn.com/apis/site/v2/sports/mma/ufc/scoreboard?dates={rng}",
                                   headers={"User-Agent": "Mozilla/5.0 agent-hq"}), timeout=30) as r:
            data = _j.loads(r.read().decode())
    except Exception as e:
        print("ESPN UFC schedule unavailable:", e, flush=True)
        return None
    cards = []
    for ev in data.get("events", []):
        bouts = []
        for comp in ev.get("competitions", []):
            names = [(c.get("athlete") or {}).get("displayName") or c.get("displayName") for c in comp.get("competitors", [])]
            if len(names) == 2 and all(names):
                bouts.append(names)
        if bouts:
            cards.append({"name": ev.get("name") or ev.get("shortName") or "UFC", "date": str(ev.get("date", ""))[:10], "bouts": bouts})
    return cards


def ufc_event(today):
    """Returns (status, event, sources). status: "ok" | "none" (checked: no UFC event) | "unchecked" (lookup failed).
    Only UFC (incl. Dana White's Contender Series). Never PFL, Bellator, ONE or others."""
    cards = espn_ufc_cards()
    if cards:
        ev = max(cards, key=lambda c: len(c["bouts"]))
        return "ok", ev, [("ESPN UFC schedule", "https://www.espn.com/mma/schedule/_/league/ufc")]
    q = (f"Today is {today}. Using UFC.com or ESPN's UFC schedule, is there a UFC event (including Dana White's Contender Series) "
         "between today and 3 days from now? UFC only: never PFL, Bellator, ONE or other promotions. "
         'Reply JSON only: {"event":{"name":"...","date":"YYYY-MM-DD","bouts":[["Fighter A","Fighter B"], ...]}} with every bout, '
         'or {"event":null} if the official schedule shows none.')
    try:
        text, src = G.generate(q, SYSTEM, search=True, temperature=0.1, retries=1)
    except Exception as e:
        print("UFC card search failed:", e, flush=True)
        return ("none" if cards == [] else "unchecked"), None, []
    official = [s for s in src if any(d in s[1] for d in ("ufc.com", "espn.com"))]
    out = parse(text) or {}
    if not official or "event" not in out:
        return ("none" if cards == [] else "unchecked"), None, src
    ev = out.get("event")
    if not ev or not ev.get("bouts"):
        return "none", None, official
    return "ok", ev, official


def ufc_research(today, event_name, bouts):
    q = (f"Today is {today}. Full fight-week breakdown for {event_name}. For EVERY fighter in the bouts below cover: stance and style "
         "(striker / wrestler / grappler), the matchup (striker vs wrestler, reach and height, cardio, chin and durability), recent form and activity "
         "(layoffs, ring rust), finishing record and how they have been finished, weigh-in results (missed weight, looked drained, short notice), "
         "camp or coaching changes, injuries or bad news, press conference and media, and fight-week line movement. Be specific and factual.\n"
         + "\n".join(f"- {a} vs {b}" for a, b in bouts))
    return gen(q, search=True, temperature=0.3)


def ufc_underdogs(today, dogs_text, notes, sources):
    src = "\n".join(f"- {t}: {u}" for t, u in sources[:30])
    p = f"""Today is {today}. These are ALL the underdogs on this UFC card, with their best FanDuel/DraftKings price and the market's fair chance:
{dogs_text}

Research notes:
{notes[:18000]}

Sources:
{src}

Analyze every underdog. Then return ONLY the 1 to 3 whose line looks genuinely WRONG (mispriced) given style matchup, recent form,
weigh-in, camp, injuries and activity. A big plus number alone is not a reason. If none are mispriced, return an empty list.
For each: your honest win probability, the realistic winning path, and one line on why the odds are off.
Return JSON only:
{{"underdogs":[{{"fighter":"exact name","prob":0.38,"path":"KO/TKO|submission|decision",
  "whyOff":"one plain sentence: why the odds are wrong",
  "breakdown":{{"style":"...","matchup":"...","form":"...","weighIn":"...","camp":"...","news":"...","lineMove":"..."}}}}]}}"""
    return json_call(p)


def key_fights(today, bouts, notes, sources):
    """Main event (and co-main if it's a big fight): individual picks with odds where a source shows them."""
    src = "\n".join(f"- {t}: {u}" for t, u in sources[:20])
    q = (f"Today is {today}. Official UFC card bouts:\n" + "\n".join(f"- {a} vs {b}" for a, b in bouts) +
         f"\n\nResearch notes:\n{notes[:14000]}\n\nIdentify the MAIN EVENT and the CO-MAIN. Include the co-main only if it's a big fight "
         "(title fight or two ranked top-15 fighters). For each fight give individual picks: winner, method (KO/TKO, submission or decision), "
         "significant strikes, takedowns and rounds. Word each bet the way FanDuel/DraftKings show it. Give the American odds for each pick "
         "ONLY if you found them on FanDuel or DraftKings in a source (else null). One plain line on why. Never call anything guaranteed or a lock.\n"
         'Reply JSON only: {"fights":[{"fight":"A vs B","role":"Main event|Co-main","picks":[{"type":"winner|method|strikes|takedowns|rounds",'
         '"bet":"...","odds":"+150 or null","book":"FanDuel|DraftKings|null","why":"..."}]}]}')
    text, src2 = gen(q, search=True, temperature=0.2)
    out = parse(text) or {}
    return [f for f in (out.get("fights") or []) if isinstance(f, dict) and f.get("picks")][:2], src2


def main_event_legs(today, bout, notes, sources):
    """Strike / takedown / method / round legs for the main event. The odds feed doesn't carry these, so no prices:
    ranked by how strongly the research backs them; Omar checks the price in the app."""
    src = "\n".join(f"- {t}: {u}" for t, u in sources[:20])
    out = json_call(f"""Today is {today}. Main event: {bout[0]} vs {bout[1]}.
Research notes:
{notes[:16000]}
Sources:
{src}

Suggest up to 5 legs for a main-event same-game parlay that FanDuel or DraftKings usually offer for a UFC main event:
significant strikes (e.g. "X 60+ Significant Strikes"), takedowns (e.g. "X 2+ Takedowns"), method of victory ("X by KO/TKO", "X by Submission", "X by Decision"),
"Fight Goes the Distance" / "Fight Doesn't Go the Distance", round totals. Word each exactly the way the app shows it.
Only include legs the research specifically supports. Rank each: "Strongest", "Strong" or "Lean". Never call anything guaranteed or a lock.
Return JSON only: {{"legs":[{{"bet":"...","rating":"Strongest|Strong|Lean","why":"one plain sentence"}}]}}""")
    order = {"Strongest": 0, "Strong": 1, "Lean": 2}
    legs = [l for l in (out.get("legs") or []) if isinstance(l, dict) and l.get("bet")]
    return sorted(legs, key=lambda l: order.get(l.get("rating"), 3))[:5]


def why_lines(parlays):
    if not parlays:
        return
    body = "\n".join(f"P{i}: " + " + ".join(f"{l['text']} ({l['why']})" for l in p["legs"]) for i, p in enumerate(parlays))
    out = json_call("For each parlay write ONE short plain sentence (max 22 words) on why it was built, no jargon, no numbers, never 'lock' or 'guaranteed'. "
                    "Only use facts in the leg reasons below; don't say which team a player plays for unless a reason says so.\n"
                    + body + '\nReturn JSON only: {"why":{"P0":"...","P1":"..."}}')
    for i, p in enumerate(parlays):
        p["why"] = str((out.get("why") or {}).get(f"P{i}") or p["legs"][0]["why"])[:200]
