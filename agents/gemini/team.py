"""Generic Agent HQ team on Gemini. Usage: python agents/gemini/team.py <job>
Jobs: youtube, linkedai, growth, upgrades, opps, lab, repos, chief.
Each job = (optional) Google-search research call + one structured writing call, following the team's own
agents/formats/*.md rules. Output goes to out/<job>_patch.json; apply_patch.py merges it safely.
"""
import json, os, re, sys, datetime
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(__file__))
import gemini as G

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TZ = ZoneInfo("America/Toronto")
NOW = datetime.datetime.now(datetime.timezone.utc)
ISO = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
TODAY = NOW.astimezone(TZ).date()

OMAR = """Omar Jaradat: university student in Mississauga, Ontario (Canada), Muslim (nothing haram: no interest-based lending, gambling etc.), limited money and hours. Runs: a TikTok self-improvement page (talking head), two faceless YouTube channels (Bounce Theory: Python physics-sim Shorts; Ambient Escape: 3-hour sleep/ambience videos from free stock footage + Islamic reminder and animated explainer Shorts), the LinkedAI Chrome extension (LinkedIn job/outreach AI, freemium), Growth Architect (Base44 web app being rebranded into an 'office of AI agents' for small e-com stores, $9.99/$19.99/$39.99), a Shopify Quran-cover brand (SATR) and NFC review tags. His AI agents now run on Gemini (free tier) instead of Claude."""

RULES = """Hard rules:
- Never invent anything: products, prices, people, channels, links, view counts, numbers, quotes, hadith or ayat. Use only facts from the research notes or the data given. If unsure, leave the field empty or write [verify].
- Religious content must be accurate (ayah with surah:ayah, only authentic hadith with collection and number). Add [verify source].
- New ideas start with status "pending" (YouTube video ideas start "approved"). Never output statuses for existing ideas.
- Write plainly, like a person, no hype words. English only."""

TEAMS = {
  "youtube": dict(state="youtube", prefix="youtube", search=True, extra=["metrics:youtube", "lab:formatLeads", "bounce:templates"],
    formats=["youtube-lineup.md", "performance-review.md"], keys=["review", "research", "ideas", "footage", "lineup", "brief"],
    agents=["reviewer", "analyst", "strategist", "producer", "lead"], hour="15:13",
    job="""YouTube team for Bounce Theory and Ambient Escape. Review both channels from the metrics (Shorts and longs separately; compare Ambient explainer Shorts vs the rest once they are 2+ days old), find what's winning on other channels now, write at most 1 new concept per channel (only with real evidence), today's footage list (Ambient only, 4-8 clips) and the FULL day's lineup exactly as youtube-lineup.md says: Bounce Theory 24 Shorts (S01-S24) + 2 longs, Ambient Escape 15 Shorts + 2 longs (Ambient: exactly 8 explainer Shorts with full specs in the note + 7 proven Shorts). NEVER reuse a title from the ALREADY UPLOADED lists or repeat a recent Bounce template+settings combo: every slot is a fresh variation (new colours, counts, shapes, hook). Every Bounce Theory item MUST have a `settings` object built only from the Bounce template menu (template + knob params; L2 uses settings.clips), as youtube-lineup.md says: the server renders Bounce Theory from those settings with no Claude. Channel separation is absolute. Mostly remixes of Omar's own winners; at most 2 tests per channel. Then a brief whose approvals start with "Today's lineup is ready: 43 videos." """,
    research="what YouTube Shorts and long videos are winning right now in: satisfying physics simulation Shorts, marble races, battle royale sims, quiz Shorts; long sleep / rain / ambient / noise videos (titles, lengths); Islamic reminder and quiz Shorts; animated Islamic explainer Shorts (POV and 'N ways' lists). Real channels, titles and view numbers."),
  "linkedai": dict(state="linkedai", prefix="linkedai", search=True, formats=["competitor-intel.md", "promo-scripts.md", "tiktok-scripts.md"],
    keys=["competitors", "research", "ideas", "brief"], agents=["watch", "copywriter", "lead"], hour="Mon 15:17",
    job="""LinkedAI team. Study competitors (LinkedIn / job-search AI extensions: Teal, Simplify, Careerflow, Kickresume, Jobscan, AIApply, Taplio - verify each), their content, ads and Chrome Web Store complaints. Write 3 ideas: at least 2 short-form promo scripts (a creator who found a useful tool, never the builder) in Omar's exact script format with a full 'formatted' field, plus 1 UGC brief / store listing fix / ad angle / feature idea from a competitor gap. At least one uses a competitor lesson (say which in why). Then a brief.""",
    research="LinkedIn and job-search AI tools (Teal, Simplify, Careerflow, Kickresume, Jobscan, AIApply, Taplio) right now: pricing, new features, complaints, and short-form videos about job hunting, LinkedIn tips and AI resumes doing unusually well."),
  "growth": dict(state="growth", prefix="growth", search=True, formats=["competitor-intel.md", "promo-scripts.md", "tiktok-scripts.md"],
    keys=["competitors", "research", "ideas", "brief"], agents=["watch", "copywriter", "lead"], hour="Tue 15:19",
    job="""Growth Architect team. Study competitors (AI marketing assistants and AI agent apps for small Shopify stores, e.g. Shopify Sidekick, YepAI, Gorgias AI, Klaviyo AI - verify each): what they post, how they advertise, complaints. Positioning: an office of AI agents for e-com stores doing ~$2k-30k/month, read-only access, nothing sends without approval. Write 3 ideas: at least 2 promo scripts (a store owner who used it, never the builder) in Omar's exact script format with a full 'formatted' field, plus 1 UGC brief / landing page fix / ad angle / positioning idea. One must use a competitor lesson. Then a brief.""",
    research="AI agent apps and AI marketing assistants for small Shopify / e-commerce stores right now (Shopify Sidekick, YepAI, Gorgias AI, Klaviyo AI and others): features, pricing, complaints, and short-form videos about small-store marketing and 'how I got my first customers' doing well."),
  "upgrades": dict(state="growth", prefix="growth-u", search=True, formats=["growth-upgrades.md", "swarm-test.md"],
    keys=["ideas", "swarms", "upgradeBrief"], agents=["upgrades"], hour="Mon,Thu 18:41",
    job="""Growth Architect Upgrade Lab. Research what Growth Architect should build next, then write 1-2 product upgrades exactly as growth-upgrades.md describes, each with a complete self-contained buildPrompt. Run a simulated 100-person reaction test (as swarm-test.md describes, clearly labelled as a simulation) on the best one and attach it as "swarm"; add it to swarms. Then upgradeBrief.""",
    research="what AI agent / marketing apps for small online stores shipped recently, what users complain about, and gaps a small 'office of AI agents with an approval queue' could fill."),
  "opps": dict(state="opps", prefix="opps", search=True, formats=["opps-build.md", "swarm-test.md"],
    keys=["research", "ideas", "swarms", "brief"], agents=["scout", "planner", "swarm", "lead"], hour="Wed 15:23",
    job="""AI Opportunities team. Find real current ways to make money with AI that fit Omar (Canada, student hours, small budget, halal). Write 3 opportunities exactly as opps-build.md describes (with a rule check against the platform's real policy, honest earnings, and a complete buildPrompt). Run a simulated 100-person test on the best one (label it a simulation), then a brief.""",
    research="ways people are actually making money with AI in the last 60 days: creator reward programs, marketplaces for AI-built products, local-business AI services, faceless content niches with proof of revenue. Include platform policy pages and real earnings reports."),
  "lab": dict(state="lab", prefix="lab", search=True, extra=["briefs"], formats=["rnd-lab.md", "youtube-lineup.md"],
    keys=["research", "formatLeads", "teamLeads", "ideas", "brief"], agents=["hunter", "scout", "engineer", "lead"], hour="every 3 days 11:23",
    job="""R&D Lab. Explore improvements to Omar's whole ecosystem. Write formatLeads for the YouTube team (new formats winning now, with real examples and view numbers), teamLeads per team, and 4-5 upgrades in the exact rnd-lab.md format (business, type, impact, effort, cost, score, step-by-step script, complete buildPrompt), each for a different business. Never depend on upgrades that aren't done. Then a brief listing approved-but-not-done upgrades as 'Waiting on Omar'.""",
    research="new short-form and YouTube formats winning right now (faceless, AI-generated, simulation, ambient, Islamic content), new free AI tools for video, voice and automation, and new ways small creators make money."),
  "repos": dict(state="repos", prefix="repo", search=True, formats=["github-scout.md"], keys=["research", "ideas", "brief", "requestAnswers"],
    agents=["scout", "tester", "lead"], hour="Sun 20:37",
    job="""GitHub Scout. Answer Omar's open requests first (compare 3-5 repos, pick the best). Then find 1-3 free, open-source GitHub repos that make his work easier or cheaper, checked properly (alive, licence, safety, runs on his laptop CPU or needs a GPU), in the exact github-scout.md format with a buildPrompt. Only real repos, real stars, real licences. Then a brief.""",
    research="useful free open-source GitHub repos released or popular recently for: AI voice/TTS that runs on CPU, video automation and rendering, YouTube/TikTok automation, Python simulation, MCP servers, AI agent frameworks."),
  "chief": dict(state="hq", prefix="hq", search=False, extra=["briefs", "metrics:youtube", "metrics:tiktok"], formats=[],
    keys=["brief"], agents=["chief"], hour="Mon 16:42",
    job="""Chief of Staff. Read every team's brief and status plus the stats, and write ONE short brief for Omar: headline (<12 words), summary (2-3 plain sentences: the most important thing across all teams, with any stat that moved), filmToday (1-3 '<team>: <title> - <hook>'), approvals (how many ideas wait + top 2-3 titles + oldest 'Waiting on Omar' items), notes (1-3 heads-ups, e.g. any agent in error)."""),
}


def load(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def context(cfg, state):
    keep = {k: state.get(k) for k in ("brief", "review", "competitors", "formatLeads", "teamLeads", "upgradeBrief", "requests") if state.get(k)}
    keep["recentIdeas"] = [{k: i.get(k) for k in ("id", "title", "status", "format", "score")} for i in state.get("ideas", [])[-30:]]
    keep["lastResearch"] = (state.get("research") or [None])[0]
    if cfg["state"] == "youtube":
        keep["lastLineup"] = state.get("lineup")
        keep["footage"] = state.get("footage")
    parts = [json.dumps(keep, ensure_ascii=False)[:30000]]
    for e in cfg.get("extra", []):
        if e.startswith("metrics:"):
            m = load(os.path.join(ROOT, "data", e[8:], "metrics.json"), {})
            parts.append(f"{e}: " + json.dumps(m, ensure_ascii=False)[:25000])
        elif e == "lab:formatLeads":
            parts.append("R&D formatLeads: " + json.dumps(load(os.path.join(ROOT, "data/lab/state.json"), {}).get("formatLeads"), ensure_ascii=False)[:6000])
        elif e == "bounce:templates":
            m = load(os.path.join(ROOT, "data/youtube/bounce_templates.json"), {})
            lines = [f"colors: {', '.join(m.get('colors', []))}", f"tunes: {', '.join(m.get('choices', {}).get('tune', []))}"]
            for n, t in (m.get("templates") or {}).items():
                ks = ", ".join(f"{k}={json.dumps(v.get('default'))}" for k, v in t.get("knobs", {}).items())
                lines.append(f"{n} [{t.get('kind')}{', ~' + str(t['secs']) + ' s' if t.get('secs') else ''}]: {ks}")
            rep = load(os.path.join(ROOT, "data/youtube/bounce_report.json"), {})
            # What's already on the channels: no lineup slot may reuse an uploaded title or a recent template+settings combo.
            logs = os.environ.get("BOUNCE_LOGS") or os.path.expanduser("~/bounce-data/logs")
            for ch, f in (("Bounce Theory", "BounceTheory"), ("Ambient Escape", "AmbientEscape")):
                ups = load(os.path.join(logs, f + "_uploaded_log.json"), []) or []
                titles = list(dict.fromkeys(x.get("title", "") for x in reversed(ups) if x.get("title")))[:250]
                parts.append(f"ALREADY UPLOADED on {ch} (newest first; NEVER reuse one of these titles, not even with a new emoji):\n"
                             + "\n".join(titles)[:14000])
            bh = load(os.path.join(ROOT, "data/youtube/bounce_history.json"), {}) or {}
            combos = [f"{d.get('date')} {s.get('template')} {json.dumps(s.get('params') or {}, sort_keys=True)} colors={s.get('colors')}"
                      for d in (bh.get("days") or [])[:14] for s in d.get("slots", []) if s.get("template")]
            parts.append("Bounce template+settings already rendered in the last 14 days (every new slot must differ in colours, "
                         "counts, shapes or other knobs, and in its hook):\n" + "\n".join(combos)[:12000])
            parts.append("Bounce template menu (template [kind]: knob=default, ...):\n" + "\n".join(lines)[:22000]
                         + "\n\nYesterday's Bounce batch report: " + json.dumps({k: rep.get(k) for k in ("date", "issues", "notMade")}, ensure_ascii=False)[:3000])
        elif e == "briefs":
            b = {}
            for t in sorted(os.listdir(os.path.join(ROOT, "data"))):
                s = load(os.path.join(ROOT, "data", t, "state.json"), {})
                b[t] = {"brief": s.get("brief"), "agents": [(a.get("name"), a.get("status"), a.get("lastRun")) for a in s.get("agents", [])],
                        "waiting": [i["title"] for i in s.get("ideas", []) if i.get("status") == "approved"][:6],
                        "pending": sum(1 for i in s.get("ideas", []) if i.get("status") == "pending")}
            parts.append("All teams: " + json.dumps(b, ensure_ascii=False)[:25000])
    return "\n\n".join(parts)


def main(job):
    cfg = TEAMS[job]
    state = load(os.path.join(ROOT, "data", cfg["state"], "state.json"), {})
    fmts = "\n\n".join(f"### {f}\n" + open(os.path.join(ROOT, "agents", "formats", f), encoding="utf-8").read()[:14000] for f in cfg["formats"])
    runbook = open(os.path.join(ROOT, "agents", "RUNBOOK.md"), encoding="utf-8").read()[:5000]
    system = f"You are an Agent HQ team working for Omar.\n{OMAR}\n\n{RULES}"
    notes, sources = "", []
    if cfg.get("search"):
        # Web-search calls have a much smaller free quota than normal calls. If search is out of quota or busy,
        # the team still does its job from the metrics and earlier research instead of failing the whole day.
        try:
            notes, sources = G.generate(f"Today is {TODAY}. Search the web and report the real findings (with names, links and numbers you actually saw) about: {cfg['research']}\nContext: {cfg['job'][:600]}", system, search=True, temperature=0.4, retries=1)
        except Exception as e:
            print(f"web search unavailable today ({str(e)[:160]}); continuing without it", flush=True)
            notes = ("(No web search today: Gemini search was out of quota or busy. Work from the metrics, the performance data and "
                     "earlier research in the state; don't claim new outside trends or add links that aren't already in the data.)")
    src = "\n".join(f"- {t}: {u}" for t, u in sources[:40])
    prompt = f"""Today is {TODAY} ({TODAY:%A}). Your job:\n{cfg['job']}

Rules for Omar's decisions (from RUNBOOK):\n{runbook}

Format files you must follow exactly:\n{fmts}

Current state and data:\n{context(cfg, state)}

Research notes from today's web search:\n{notes[:15000]}
Links found by the search (only use these, or links already in the data):\n{src}

Return ONE JSON object with only these keys: {cfg['keys']} plus "log" (list of 2-4 short plain lines on what you did) and "doing" (one short line).
- "ideas": list of NEW ideas only, every field the format file asks for (no "id", I add it).
- "research": ONE entry {{"date":"{TODAY}","createdAt":"{ISO}","items":[...]}}.
- "brief": {{"date":"{TODAY}","createdAt":"{ISO}","headline":"","summary":"","filmToday":[],"approvals":[],"notes":[]}}.
Include every key listed above."""
    raw = None
    for attempt in range(3):
        try:
            text, _ = G.generate(prompt, system, json_out=True, temperature=0.7)
            raw = G.parse_json(text)
            if isinstance(raw, dict):
                break
        except Exception as e:
            print("retrying:", e, flush=True)
    if not isinstance(raw, dict):
        raise RuntimeError("Gemini didn't return usable JSON 3 times")
    patch = {"team": cfg["state"], "at": ISO, "log": [], "agents": {}}
    for k in cfg["keys"]:
        if k in raw and raw[k] not in (None, "", []):
            patch[k] = raw[k]
    # ids, statuses, provenance for new ideas
    used = {i.get("id") for i in state.get("ideas", [])}
    n, ideas = 1, []
    for i in patch.get("ideas", []) or []:
        if not isinstance(i, dict) or not i.get("title"):
            continue
        while f"{cfg['prefix']}-{TODAY}-{n}" in used:
            n += 1
        i["id"] = f"{cfg['prefix']}-{TODAY}-{n}"; used.add(i["id"])
        i["status"] = "approved" if job == "youtube" else "pending"
        i["createdAt"] = ISO; i["madeBy"] = "gemini"
        for k in ("decidedAt", "doneAt"):
            i.pop(k, None)
        ideas.append(i)
    if ideas:
        patch["ideas"] = ideas
    name = {"reviewer": "Performance Reviewer", "lead": "Lead", "chief": "Chief of Staff", "upgrades": "Upgrade Lab"}
    for line in (raw.get("log") or [])[:4]:
        patch["log"].append({"t": ISO, "agent": "Gemini team", "msg": str(line)[:240]})
    for a in cfg["agents"]:
        patch["agents"][a] = {"status": "ok", "doing": str(raw.get("doing", "Done (Gemini)"))[:140], "lastRun": ISO}
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    json.dump(patch, open(os.path.join(ROOT, "out", f"{job}_patch.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{job}: wrote patch with keys {sorted(patch)} and {len(ideas)} ideas")


if __name__ == "__main__":
    main(sys.argv[1])
