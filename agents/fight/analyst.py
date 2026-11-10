"""Gemini research and probability estimates (free tier, Google Search grounding). No Claude."""
import os, re, sys
import config as C
import oddsmath as M
import wording as W

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


def gen(prompt, search=False, json_out=False, temperature=0.2):
    return G.generate(prompt, SYSTEM, search=search, json_out=json_out, temperature=temperature)


def parse(text):
    try:
        return G.parse_json(text)
    except Exception:
        return None


def json_call(prompt, tries=3):
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
        pt = abs(c["point"]) if (c["market"] == "spreads" and c["point"] is not None) else c["point"]
        groups.setdefault((c["eventId"], c["market"], who, pt), []).append(c)
    rows, idx = [], {}
    for n, ((eid, mk, who, pt), cs) in enumerate(sorted(groups.items(), key=lambda kv: (kv[1][0]["commence"] or "", str(kv[0]))), 1):
        lid = f"L{n}"
        idx[lid] = {c["side"]: c for c in cs}
        parts = []
        for c in cs:
            pr = " ".join(f"{C.BOOKS[b][:2]} {W.american(d)}" for b, d in c["prices"].items())
            parts.append(f"{c['side']}{'' if c['point'] is None or mk == 'totals' or mk.startswith('player') or mk == 'team_totals' else ' ' + format(c['point'], '+g')} [{pr}] fair {c['fair']*100:.0f}%")
        label = {"h2h": "Winner", "spreads": "Spread", "totals": "Game total" if cs[0]["sport"] == "nba" else "Total rounds",
                 "team_totals": f"{who} team total", "player_points": f"{who} points", "player_rebounds": f"{who} rebounds",
                 "player_assists": f"{who} assists", "player_threes": f"{who} threes"}.get(mk, mk)
        line_pt = "" if pt is None or mk in ("h2h", "spreads") else f" {pt:g}"
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
        n += 1
    return n


# ---------- NBA ----------

def nba_research(today, games):
    q = (f"Today is {today}. Research tonight's NBA games below for betting analysis: official injury report (out / questionable / probable), "
         "rest and back-to-backs, travel, recent form (last 10 games), pace, offensive and defensive ratings, matchup edges, "
         "and line-moving news from the last 24 hours. Also note which players' roles change because of injuries.\n"
         + "\n".join(games) +
         "\nEnd with one line exactly like: PROP_GAMES: <game>; <game>; ... listing the games with the most player-prop angles first.")
    text, src = gen(q, search=True, temperature=0.3)
    m = re.search(r"PROP_GAMES:\s*(.+)", text or "")
    ranked = [g.strip() for g in m.group(1).split(";")] if m else []
    return text, src, ranked


def nba_props_research(today, players_by_game):
    q = (f"Today is {today}. For these NBA players with prop lines tonight, find each one's last 5-10 games (points, rebounds, assists, made threes, minutes), "
         "season averages, tonight's role (starting? minutes limit? teammates out?) and the opponent's defense against their position. Be specific.\n"
         + "\n".join(f"{g}: {', '.join(ps[:10])}" for g, ps in players_by_game.items()))
    return gen(q, search=True, temperature=0.3)


def estimate(sport, lines_text, notes, sources, today, extra=""):
    src = "\n".join(f"- {t}: {u}" for t, u in sources[:30])
    p = f"""Today is {today}. Below is every {sport.upper()} line currently listed on FanDuel (Fa) and DraftKings (Dr), with the market's fair (no-vig) chance.

{lines_text[:30000]}

Research notes:
{notes[:16000]}
{extra[:8000]}

Sources:
{src}

Pick up to 45 lines where the research gives you a concrete, specific reason to disagree with or confirm the market, and estimate the TRUE chance of the side you'd choose.
- Start from the fair chance and move only for specific reasons (injury, role change, rest, matchup, recent form, weigh-in, style).
- Moves above 10 points need a strong specific reason.
- "why" must be one short plain sentence a casual fan understands, with the specific reason (e.g. "Davis is out, so Lakers lose their best rebounder").
Return JSON only: {{"picks":[{{"id":"L12","side":"exact side name as shown (team, fighter, Over or Under)","prob":0.58,"why":"..."}}]}}"""
    return json_call(p)


# ---------- UFC ----------

def ufc_event(today):
    q = (f"Today is {today} (a Friday). Is there a UFC event this Friday, Saturday or Sunday? UFC only, not PFL, ONE or other promotions. "
         'Reply JSON only: {"event":{"name":"UFC ...","date":"YYYY-MM-DD","bouts":[["Fighter A","Fighter B"], ...]}} with every bout on the main card and prelims, '
         'or {"event":null} if there is no UFC event.')
    text, src = gen(q, search=True, temperature=0.1)
    out = parse(text) or {}
    return out.get("event"), src


def ufc_research(today, event_name, bouts):
    q = (f"Today is {today}. Full fight-week breakdown for {event_name}. For EVERY fighter in the bouts below cover: stance and style "
         "(striker / wrestler / grappler), the matchup (striker vs wrestler, reach and height, cardio, chin and durability), recent form and activity "
         "(layoffs, ring rust), finishing record and how they have been finished, weigh-in results (missed weight, looked drained, short notice), "
         "camp or coaching changes, injuries or bad news, press conference and media, and fight-week line movement. Be specific and factual.\n"
         + "\n".join(f"- {a} vs {b}" for a, b in bouts))
    return gen(q, search=True, temperature=0.3)


def ufc_underdogs(today, dogs_text, notes, sources):
    src = "\n".join(f"- {t}: {u}" for t, u in sources[:30])
    p = f"""Today is {today}. These are the underdogs on this UFC card with their best price on FanDuel/DraftKings and the market's fair chance:
{dogs_text}

Research notes:
{notes[:18000]}

Sources:
{src}

For each underdog decide honestly whether they have a GENUINE path to winning (a real, specific way to win this matchup), or are just a big plus number with no real chance.
Return JSON only:
{{"underdogs":[{{"fighter":"exact name","genuine":true,"prob":0.33,"path":"KO/TKO|submission|finish|decision|straight win",
  "oneLine":"one plain sentence on why they could actually win",
  "breakdown":{{"style":"stance and style","matchup":"striker vs wrestler, reach, cardio, chin","form":"recent form and activity, layoffs","finishing":"finishing record and how they have been finished","weighIn":"weigh-in: missed weight / drained / short notice","camp":"camp or coaching changes","news":"injuries or bad news","media":"press conference and media","lineMove":"fight-week line movement"}}}}]}}"""
    return json_call(p)


def why_lines(parlays):
    if not parlays:
        return
    body = "\n".join(f"P{i}: " + " + ".join(f"{l['text']} ({l['why']})" for l in p["legs"]) for i, p in enumerate(parlays))
    out = json_call("For each parlay write ONE short plain sentence (max 22 words) on why it was built, no jargon, no numbers, never 'lock' or 'guaranteed'.\n"
                    + body + '\nReturn JSON only: {"why":{"P0":"...","P1":"..."}}')
    for i, p in enumerate(parlays):
        p["why"] = str((out.get("why") or {}).get(f"P{i}") or p["legs"][0]["why"])[:200]
