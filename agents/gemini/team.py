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
    job="""YouTube team for Bounce Theory and Ambient Escape. Review both channels from the metrics (Shorts and longs separately; compare Ambient explainer Shorts vs the rest once they are 2+ days old), find what's winning on other channels now, write at most 1 new concept per channel (only with real evidence), today's footage list (Ambient only, 4-8 clips) and the FULL day's lineup exactly as youtube-lineup.md says: Bounce Theory 24 Shorts (S01-S24) + 2 longs, Ambient Escape 24 Shorts + 2 longs (Ambient: exactly 12 animated explainer Shorts with full specs in the note + 12 proven Shorts). NEVER reuse a title from the ALREADY UPLOADED lists or repeat a recent Bounce template+settings combo: every slot is a fresh variation (new colours, counts, shapes, hook). Every Bounce Theory item MUST have a `settings` object built only from the Bounce template menu (template + knob params; L2 uses settings.clips), as youtube-lineup.md says: the server renders Bounce Theory from those settings with no Claude. Channel separation is absolute. IDEAS FIRST: fill slots from the APPROVED BOARD IDEAS list before inventing anything (oldest first, both channels, only ideas that fit an existing template/format; never the ones marked needsBuild). Every slot made from a board idea MUST carry "ideaId": "<that idea's id>" (one idea per slot, never two slots for one idea). Remaining slots: mostly remixes of Omar's own winners; at most 2 tests per channel. New ideas: never add one that repeats or rewords an idea already on the board. Then a brief whose approvals start with "Today's lineup is ready: 52 videos." """,
    research="what YouTube Shorts and long videos are winning right now in: satisfying physics simulation Shorts, marble races, battle royale sims, quiz Shorts; long sleep / rain / ambient / noise videos (titles, lengths); Islamic reminder and quiz Shorts; animated Islamic explainer Shorts (POV and 'N ways' lists). Real channels, titles and view numbers."),
  "linkedai": dict(state="linkedai", prefix="linkedai", search=True, formats=["competitor-intel.md"],
    keys=["competitors", "research", "ideas", "brief"], agents=["watch", "lead"], hour="Mon 15:17",
    job="""LinkedAI team. Study competitors (LinkedIn / job-search AI extensions: Teal, Simplify, Careerflow, Kickresume, Jobscan, AIApply, Taplio - verify each), their content, ads and Chrome Web Store complaints. Promo VIDEO scripts are NOT your job any more: the Promo Studio writes them Mon/Wed/Fri from its own research (it reads your competitor list). Write 3 ideas that get installs and paid conversions: store listing fixes, onboarding / first-use, reviews, referral, pricing page, UGC brief, ad angle, or a feature that is NOT in SYSTEM_MAP.md's LinkedAI list, each from a competitor gap. At least one uses a competitor lesson (say which in why). Then a brief.""",
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
    job="""R&D Lab: upgrades the WHOLE SYSTEM. Follow rnd-lab.md and SYSTEM_MAP.md exactly. (1) 1-2 SYSTEM upgrades (business "System"): make the machine more efficient, reliable, cheaper and less manual, using the evidence in "All teams" (errors, empty outputs, stale runs, batch issues). (2) Up to 3 BUSINESS upgrades, max 1 each, business exactly one of TikTok / Bounce Theory / Ambient Escape / WANTED LEVEL / LinkedAI, only 8+/10 with evidence, never something SYSTEM_MAP.md says exists and never a reword of an EXISTING UPGRADE TITLE. Growth Architect is PAUSED: nothing about it anywhere. Also formatLeads for the YouTube team and teamLeads (tiktok, linkedai, opps, youtube only). Never depend on upgrades that aren't done. Then a brief listing approved-but-not-done upgrades as 'Waiting on Omar'.""",
    research="ways to run an always-on AI agent + video automation system more efficiently on a free tier: Gemini API free-tier quota tips and new models, reliable cron/job monitoring and phone alerts (ntfy), faster video rendering on ARM CPUs, plus new short-form and YouTube formats winning right now (faceless, simulation, ambient, Islamic content) and LinkedIn job-search tool trends."),
  "repos": dict(state="repos", prefix="repo", search=True, formats=["github-scout.md"], keys=["research", "ideas", "brief", "requestAnswers"],
    agents=["scout", "tester", "lead"], hour="Sun 20:37",
    job="""GitHub Scout. Answer the ONE request named in the research notes (one request per run): the notes hold REAL live GitHub search results for it (stars, licence, last push, README). For each request compare the 3-5 best of those candidates and pick the best one, saying what it does, why it beats the others, licence, whether it runs on his laptop CPU or needs a GPU, and the first setup step. Key requestAnswers by the exact [key] shown for that request. Only answer "Nothing good enough yet" if the candidate list is empty or none of them does the job (say which ones you rejected and why). Then find 1-3 free, open-source GitHub repos that make his work easier or cheaper, checked properly (alive, licence, safety, runs on his laptop CPU or needs a GPU), in the exact github-scout.md format with a buildPrompt. Only real repos, real stars, real licences. Then a brief.""",
    research="useful free open-source GitHub repos released or popular recently for: AI voice/TTS that runs on CPU, video automation and rendering, YouTube/TikTok automation, Python simulation, MCP servers, AI agent frameworks."),
  "chief": dict(state="hq", prefix="hq", search=False, extra=["briefs", "metrics:youtube", "metrics:tiktok"], formats=[],
    keys=["brief"], agents=["chief"], hour="Mon 16:42",
    job="""Chief of Staff. Read every team's brief and status plus the stats, and write ONE short brief for Omar: headline (<12 words), summary (2-3 plain sentences: the most important thing across all teams, with any stat that moved), filmToday (1-3 '<team>: <title> - <hook>'), approvals (how many ideas wait + top 2-3 titles + oldest 'Waiting on Omar' items), notes (1-3 heads-ups, e.g. any agent in error)."""),
}


PAUSED = {"growth": "Growth Architect is under construction", "upgrades": "Growth Architect is under construction"}
PAUSED_STATES = {"growth"}
BUSINESSES = {"System", "TikTok", "Bounce Theory", "Ambient Escape", "WANTED LEVEL", "LinkedAI"}


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
    if cfg["state"] == "youtube":
        board = [{"id": i.get("id"), "channel": channel_of(i), "needsBuild": needs_build(i), "title": i.get("title"), "format": i.get("format"),
                  "hook": i.get("hook"), "notes": str(i.get("script") or i.get("description") or "")[:400]}
                 for i in sorted(approved_ideas(state), key=lambda i: str(i.get("createdAt", "")))]
        parts.append("APPROVED BOARD IDEAS (use these FIRST in today's lineup, oldest first; set ideaId on the slot; skip needsBuild ones):\n"
                     + json.dumps(board, ensure_ascii=False)[:20000])
        parts.append("ALL IDEA TITLES ON THE BOARD (never add a new idea that repeats or rewords one of these):\n"
                     + "\n".join(str(i.get("title", "")) for i in state.get("ideas", []))[:8000])
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
                if t in PAUSED_STATES:
                    continue
                s = load(os.path.join(ROOT, "data", t, "state.json"), {})
                b[t] = {"brief": s.get("brief"), "agents": [(a.get("name"), a.get("status"), a.get("lastRun")) for a in s.get("agents", [])],
                        "waiting": [i["title"] for i in s.get("ideas", []) if i.get("status") == "approved"][:6],
                        "pending": sum(1 for i in s.get("ideas", []) if i.get("status") == "pending")}
            parts.append("All teams: " + json.dumps(b, ensure_ascii=False)[:25000])
    if cfg["state"] == "lab":
        parts.append("EXISTING UPGRADE TITLES (pending, approved, done or skipped; never pitch these again or reword them):\n"
                     + "\n".join(f"- [{i.get('status')}] {i.get('business', '')}: {i.get('title', '')}" for i in state.get("ideas", []))[:12000])
    return "\n\n".join(parts)


def needs_build(i):
    return bool(re.search(r"needs build|new (sim )?build|new template", f"{i.get('title', '')} {i.get('format', '')}", re.I))


def channel_of(i):
    t = f"{i.get('channel') or ''} {i.get('format', '')} {i.get('title', '')}".lower()
    return "Ambient Escape" if "ambient" in t else "Bounce Theory"


def approved_ideas(state):
    return [i for i in state.get("ideas", []) if i.get("status") == "approved"]


def _idea_key(t):
    t = re.sub(r"(?i)bounce theory:|ambient escape:|needs build:|vol\.? ?\d+|#\S+", " ", str(t or ""))
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def drop_repeat_ideas(patch, state):
    """No new idea that repeats or rewords one already on the board (any status) or another new one."""
    import difflib
    seen = [_idea_key(i.get("title")) for i in state.get("ideas", [])]
    keep, dropped = [], 0
    for i in patch.get("ideas", []) or []:
        k = _idea_key(i.get("title"))
        if not k or any(k == o or difflib.SequenceMatcher(None, k, o).ratio() >= 0.8 for o in seen if o):
            dropped += 1; continue
        seen.append(k); keep.append(i)
    patch["ideas"] = keep
    print(f"new ideas kept {len(keep)}, dropped as repeats {dropped}", flush=True)


def check_idea_slots(patch, state):
    """Keep ideaId only on slots that use a real, approved, buildable idea of the same channel, once each."""
    L = patch.get("lineup")
    if not isinstance(L, dict):
        return
    chans = L.get("channels") if isinstance(L.get("channels"), dict) else L
    ok = {i["id"]: i for i in approved_ideas(state) if i.get("id") and not needs_build(i)}
    used, n = set(), 0
    for ch, slots in chans.items():
        for sl in slots if isinstance(slots, list) else []:
            if not isinstance(sl, dict) or not sl.get("ideaId"):
                continue
            iid = str(sl["ideaId"]); idea = ok.get(iid)
            if not idea or iid in used or channel_of(idea) != ch:
                sl.pop("ideaId", None); continue
            used.add(iid); n += 1
    print(f"lineup slots from board ideas: {n} (approved buildable on the board: {len(ok)})", flush=True)


def _norm_title(t):
    t = re.sub(r"#\S+", "", str(t or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def uploaded_titles():
    logs = os.environ.get("BOUNCE_LOGS") or os.path.expanduser("~/bounce-data/logs")
    out = {}
    for ch, f in (("Bounce Theory", "BounceTheory"), ("Ambient Escape", "AmbientEscape")):
        ups = load(os.path.join(logs, f + "_uploaded_log.json"), []) or []
        out[ch] = {_norm_title(x.get("title")) for x in ups if x.get("title")}
    return out


def fix_repeats(patch, system):
    """Gemini often ignores 'never reuse a title'. Find lineup slots whose title is already uploaded and ask once
    for fresh replacements (same channel, same kind/format); the servers skip any slot that still repeats."""
    L = patch.get("lineup")
    if not isinstance(L, dict):
        return
    chans = L.get("channels") if isinstance(L.get("channels"), dict) else L
    seen = uploaded_titles()
    dupes = []
    for ch, slots in chans.items():
        if not isinstance(slots, list) or ch not in seen:
            continue
        used = set(seen[ch])
        for i, sl in enumerate(slots):
            if not isinstance(sl, dict):
                continue
            n = _norm_title(sl.get("title"))
            if n and n in used:
                dupes.append((ch, i, sl))
            used.add(n)
    print(f"lineup repeats of uploaded titles: {len(dupes)}", flush=True)
    if not dupes:
        return
    ask = [{"channel": ch, "index": i, "slot": sl} for ch, i, sl in dupes]
    avoid = {ch: sorted(t for t in seen[ch])[:400] for ch in seen}
    prompt = ("These lineup slots repeat titles that are ALREADY UPLOADED. Rewrite each one as a genuinely new video for the same "
              "channel and the same kind/format: new title (not in the avoid list, not a reworded copy), new hook, and for Bounce Theory "
              "a new `settings` from the same template with different colours/counts/knobs. Keep every other field the slot has.\n"
              "Return JSON {\"slots\": [{\"channel\":..., \"index\":..., \"slot\": {...full slot...}}]}.\n\n"
              f"Slots to rewrite:\n{json.dumps(ask, ensure_ascii=False)[:30000]}\n\nAvoid these (normalized) titles:\n"
              f"{json.dumps(avoid, ensure_ascii=False)[:30000]}")
    try:
        text, _ = G.generate(prompt, system, json_out=True, temperature=0.9)
        fixed = (G.parse_json(text) or {}).get("slots") or []
    except Exception as e:
        print("repeat fix failed:", str(e)[:200], flush=True)
        return
    done = 0
    for f in fixed:
        try:
            ch, i, new = f["channel"], int(f["index"]), f["slot"]
            old = chans[ch][i]
            if isinstance(new, dict) and _norm_title(new.get("title")) not in seen.get(ch, set()):
                new["slot"] = old.get("slot", new.get("slot"))
                chans[ch][i] = new; done += 1
        except Exception:
            continue
    print(f"lineup repeats fixed: {done}/{len(dupes)}", flush=True)


_STOP = {"linkedai", "tiktok", "bounce", "theory", "ambient", "escape", "the", "a", "and", "for", "with", "to", "of", "in", "your"}


def fix_lab(patch, state):
    """R&D Lab: keep only allowed businesses, drop paused ones and repeats of existing upgrades, cap the counts."""
    seen = [set(_idea_key(i.get("title", "")).split()) - _STOP for i in state.get("ideas", [])]
    keep, per = [], {}
    for i in patch.get("ideas", []) or []:
        b = str(i.get("business", "")).strip()
        if b in ("Agent HQ", "Site", "Server"):
            b = i["business"] = "System"
        if b not in BUSINESSES or "growth architect" in (str(i.get("title", "")) + " " + str(i.get("hook", ""))).lower():
            print("lab: dropped (business not allowed / paused):", i.get("title"), flush=True); continue
        w = set(_idea_key(i.get("title", "")).split()) - _STOP
        if any(w and o and len(w & o) >= max(2, 0.6 * min(len(w), len(o))) for o in seen):
            print("lab: dropped repeat:", i.get("title"), flush=True); continue
        biz = sum(v for x, v in per.items() if x != "System")
        if per.get(b, 0) >= (2 if b == "System" else 1) or (b != "System" and biz >= 3):
            continue
        per[b] = per.get(b, 0) + 1; seen.append(w); keep.append(i)
    patch["ideas"] = keep
    if isinstance(patch.get("teamLeads"), dict):
        patch["teamLeads"].pop("growth", None)


def _gh(url):
    import urllib.request
    h = {"Accept": "application/vnd.github+json", "User-Agent": "agent-hq-scout"}
    if os.environ.get("GITHUB_TOKEN"):
        h["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=20))


_STOPQ = set("a an and the i im i'm am is are to for of on in my me that this with it can need want looking please search those them repo repos github so just like who what which also use uses using be all and or but from proper perfectly absolutely free open source".split())


def _kw(text, n=4):
    words = [w for w in re.findall(r"[a-z0-9+#.]+", text.lower()) if w not in _STOPQ and len(w) > 2]
    return " ".join(list(dict.fromkeys(words))[:n])


def scout_target(state):
    """The ONE request this run works on: the oldest open request (one per run keeps Gemini and GitHub quota tiny)."""
    reqs = [r for r in state.get("requests", []) if r.get("status") != "answered"]
    return reqs[0] if reqs else None


def github_research(state, system):
    """GitHub Scout: search GitHub itself (free, no Gemini search quota) for ONE open request.
    Returns (notes, sources, found) where found[key] = number of real candidates for that request."""
    import time, urllib.parse
    r = scout_target(state)
    a = {"key": r["text"][:40], "text": r["text"]} if r else {"key": "general", "text": "free open-source tools for AI video automation, CPU text to speech, YouTube TikTok automation, MCP servers"}
    qs = []
    try:
        text, _ = G.generate("Write 4 short GitHub repository search queries (2-3 plain keywords each, no quotes, no 'github', no qualifiers) "
                             "that would find real open-source repos doing this job. Return JSON {\"queries\": [\"q1\",\"q2\",\"q3\",\"q4\"]}.\nJob: " + a["text"],
                             system, json_out=True, temperature=0.2)
        qs = (G.parse_json(text) or {}).get("queries") or []
    except Exception as e:
        print("query writing failed (using keywords instead):", e, flush=True)
    qs = [q for q in qs if isinstance(q, str) and q.strip()][:4] + [_kw(a["text"], 4), _kw(a["text"], 2)]
    cutoff = (NOW - datetime.timedelta(days=720)).strftime("%Y-%m-%d")
    seen, errors = {}, []
    for q in dict.fromkeys(qs):
        # strict first, then looser if GitHub returns nothing
        for qual in (f" stars:>20 pushed:>{cutoff}", " stars:>5", ""):
            try:
                res = _gh("https://api.github.com/search/repositories?" + urllib.parse.urlencode({"q": q + qual, "sort": "stars", "order": "desc", "per_page": 8}))
                items = res.get("items", [])
            except Exception as e:
                errors.append(f"{q}: {e}"); items = []
            time.sleep(7)   # unauthenticated search limit: 10 a minute
            for it in items:
                seen.setdefault(it["full_name"], it)
            if items:
                break
        if len(seen) >= 12:
            break
    print(f"scout: request [{a['key']}] queries={list(dict.fromkeys(qs))} candidates={len(seen)} errors={errors[:3]}", flush=True)
    top = sorted(seen.values(), key=lambda x: -x["stargazers_count"])[:10]
    lines, sources = [], []
    for n, it in enumerate(top):
        readme = ""
        if n < 5:
            try:
                import base64
                rd = _gh(f"https://api.github.com/repos/{it['full_name']}/readme")
                readme = base64.b64decode(rd.get("content", "")).decode("utf-8", "ignore")
                readme = re.sub(r"<[^>]+>|!\[[^\]]*\]\([^)]*\)|\s+", " ", readme)[:900]
            except Exception:
                pass
        lines.append(f"- {it['full_name']} | {it['stargazers_count']} stars | licence: {(it.get('license') or {}).get('spdx_id') or 'none'} | "
                     f"last push {it['pushed_at'][:10]} | {it.get('language') or ''} | {it['html_url']}\n  {it.get('description') or ''}\n  README: {readme}")
        sources.append((it["full_name"], it["html_url"]))
    note = (f"### THIS RUN'S REQUEST [{a['key']}]: {a['text']}\nReal GitHub search results (live from the GitHub API today, {len(top)} candidates):\n"
            + ("\n".join(lines) or "(GitHub returned nothing" + (": " + "; ".join(errors[:3]) if errors else "") + ")")
            + "\n\nAnswer ONLY this one request this run. Other open requests wait for later runs.")
    return note, sources, {a["key"]: len(top)}, errors

def main(job):
    if job in PAUSED:
        print(f"{job}: paused ({PAUSED[job]}). Not running.")
        return
    cfg = TEAMS[job]
    state = load(os.path.join(ROOT, "data", cfg["state"], "state.json"), {})
    fmts = "\n\n".join(f"### {f}\n" + open(os.path.join(ROOT, "agents", "formats", f), encoding="utf-8").read()[:14000] for f in cfg["formats"])
    runbook = open(os.path.join(ROOT, "agents", "RUNBOOK.md"), encoding="utf-8").read()[:5000]
    sysmap = open(os.path.join(ROOT, "agents", "SYSTEM_MAP.md"), encoding="utf-8").read()[:14000]
    system = f"You are an Agent HQ team working for Omar.\n{OMAR}\n\n{RULES}"
    notes, sources = "", []
    found = {}
    if job == "repos":
        notes, sources, found, gh_errors = github_research(state, system)
    elif cfg.get("search"):
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

What Omar's system is and does TODAY (never pitch anything listed here as new; Growth Architect is paused):\n{sysmap}

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
    if job == "youtube":
        fix_repeats(patch, system)
        check_idea_slots(patch, state)
    if job == "youtube" and patch.get("ideas"):
        drop_repeat_ideas(patch, state)
    if job == "lab":
        fix_lab(patch, state)
    if job == "repos" and isinstance(patch.get("requestAnswers"), list):
        lst = [x for x in patch["requestAnswers"] if x]
        a0 = lst[0] if lst else None
        tgt0 = scout_target(state)
        patch["requestAnswers"] = {tgt0["text"][:40]: (a0.get("answer") or a0.get("text") or json.dumps(a0)) if isinstance(a0, dict) else str(a0)} if (a0 and tgt0) else {}
    if job == "repos" and isinstance(patch.get("requestAnswers"), dict):
        # One request per run. "Nothing good" only closes a request after 3 real tries; otherwise it stays open
        # with a note, and the next run searches again with fresh queries.
        tgt = scout_target(state)
        for k in list(patch["requestAnswers"]):
            ans = str(patch["requestAnswers"][k])
            if not tgt or str(k)[:40] != tgt["text"][:40]:
                patch["requestAnswers"].pop(k); continue
            if ans.lower().startswith("nothing good"):
                tgt["tries"] = int(tgt.get("tries", 0)) + 1
                if tgt["tries"] < 3:
                    print(f"kept request open (try {tgt['tries']}/3):", k, flush=True)
                    patch.setdefault("requestNotes", {})[tgt["text"][:40]] = f"Try {tgt['tries']} of 3: {ans[:300]}"
                    patch["requestAnswers"].pop(k)
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    json.dump(patch, open(os.path.join(ROOT, "out", f"{job}_patch.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{job}: wrote patch with keys {sorted(patch)} and {len(ideas)} ideas")


if __name__ == "__main__":
    main(sys.argv[1])
