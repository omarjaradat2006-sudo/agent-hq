"""TikTok team on Gemini (replaces the Claude scheduled task). Run by .github/workflows/team-tiktok.yml.

Writes out/tiktok_patch.json; apply_patch.py merges it into data/tiktok/state.json on the latest commit,
so Omar's button presses (idea statuses) are never overwritten.
"""
import json, os, re, sys, datetime
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(__file__))
import gemini as G

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE = os.path.join(ROOT, "data", "tiktok", "state.json")
METRICS = os.path.join(ROOT, "data", "tiktok", "metrics.json")
FORMAT = os.path.join(ROOT, "agents", "formats", "tiktok-scripts.md")
OUT = os.path.join(ROOT, "out", "tiktok_patch.json")
TZ = ZoneInfo("America/Toronto")
NOW = datetime.datetime.now(datetime.timezone.utc)
ISO = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
TODAY = NOW.astimezone(TZ).date()
RESEARCH_DAY = TODAY.weekday() in (0, 2, 4) or os.environ.get("FORCE_RESEARCH") == "1"
TAGS = "#fyppppppppppppppppppppppp #viral #fyp"
FAITH = re.compile(r"\b(allah|quran|qur'an|salah|salat|prayer|pray|islam|muslim|hadith|deen|dua|prophet|sunnah|ayah|jannah|iman)\b", re.I)
LETTERS = "ABC"

SYSTEM = """You are the TikTok team (Performance Reviewer, Analyst, Strategist, Copywriter) for Omar Jaradat, a university student in Mississauga who makes sit-down talking-head TikToks: self-improvement for young guys (discipline, mindset, stoicism and philosophy, psychology, habits, money/career mindset, masculinity and relationships, living life right). He is Muslim and faith is one pillar, but most videos are NOT about Islam. He talks as a regular guy still figuring it out, never a guru, never rich.
Never invent stats, studies, quotes, stories, creators, links or numbers. If a line needs Omar's own story, write [fill in: ...]. Quote philosophers accurately and name them. Any hadith/ayah: real reference plus [verify source]."""


def load(p, default=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


def review_step(state, metrics):
    kpis = json.dumps(metrics.get("kpis", {}))[:2000]
    top = json.dumps(metrics.get("topVideos", [])[:25])[:9000]
    done = [{"title": i["title"], "hook": i.get("hook"), "doneAt": i.get("doneAt")} for i in state["ideas"] if i.get("status") == "done"][-15:]
    prompt = f"""Today is {TODAY}. Review how Omar's recent TikToks performed. Only judge posts older than 48 hours as final.
KPIs: {kpis}
Videos (newest/top, with views etc.): {top}
Scripts he filmed from this site: {json.dumps(done)[:3000]}
Previous review headline: {(state.get('review') or {}).get('headline','')}

Return JSON: {{"date":"{TODAY}","createdAt":"{ISO}","headline":"<12 words","summary":"2-3 plain sentences to 'you' with real numbers",
"winners":[{{"title":"","url":"","views":0,"why":""}}] (top 3-5 real ones from the data),
"doMore":["2-4 concrete things"],"stopDoing":["1-3 things"],"skillSuggestions":[]}}"""
    t, _ = G.generate(prompt, SYSTEM, json_out=True, temperature=0.4)
    return G.parse_json(t)


def research_step(state, metrics):
    trending = json.dumps(metrics.get("trending", [])[:15])[:5000]
    prompt = f"""Today is {TODAY}. Search the web for what's doing unusually well RIGHT NOW (last 2 weeks) on TikTok/Reels/Shorts for young men in: stoicism/philosophy, psychology explainers, discipline/habits/dopamine, money and career mindset for 18-25s, masculinity/relationships advice, 'hard truths' talking-head videos, plus Muslim self-improvement. Pay attention to the exact first lines (hooks).
Trending outliers our own tracker found: {trending}
Then give exactly 5 findings (at least 3 non-religious) as a JSON array inside a ```json block:
[{{"title":"","creator":"","url":"real url you found or empty","metric":"only if you saw a real number, else empty","whyItWorks":"1-2 sentences for Omar"}}]"""
    t, sources = G.generate(prompt, SYSTEM, search=True, temperature=0.5)
    items = G.parse_json(t)
    if isinstance(items, dict):
        items = items.get("items", [])
    real = {u for _, u in sources}
    for it in items:   # keep only links that actually came from the search, never invented ones
        if it.get("url") and it["url"] not in real and not it["url"].startswith(("https://www.tiktok.com", "https://www.youtube.com", "https://youtube.com")):
            it["url"] = ""
    return {"date": str(TODAY), "createdAt": ISO, "items": items[:5]}


def write_step(state, fmt):
    rev = state.get("review") or {}
    res = (state.get("research") or [{}])[0]
    recent = [{"title": i["title"], "hookFamily": i.get("hookFamily"), "status": i.get("status")} for i in state["ideas"][-24:]]
    prompt = f"""Today is {TODAY} ({TODAY:%A}). Write 3 NEW ready-to-film TikTok scripts for Omar.

TOPIC MIX: at most 1 faith-centred idea (Islam, Allah, salah, Quran). At least 2 non-religious (philosophy, stoicism, psychology, discipline, habits, money mindset, masculinity, relationships, real life lesson). A non-religious script must not mention religion or end on a religious line. Rotate away from the themes in recent ideas.
The 3 ideas must use 3 DIFFERENT hook families and structures.

Latest review: headline: {rev.get('headline','')}; doMore: {rev.get('doMore')}; stopDoing: {rev.get('stopDoing')}
Latest research: {json.dumps(res.get('items', []))[:3500]}
Recent ideas (don't repeat; lean toward what he approved/did, avoid what he skipped): {json.dumps(recent)}

His format rules (follow exactly):
{fmt}

Write like a real 20-year-old talking: vary sentence length hard, contractions, plain words, no AI tells (no "Here's the thing", "game-changer", "unlock", "journey", em-dashes, "It's not X, it's Y", tidy summaries).

Return JSON only: {{"strategy":"one line on why these 3 angles","ideas":[
 {{"title":"","why":"1-2 sentences tied to the review or research","hookFamily":"","length":30,"onScreen":"",
   "scenes":[{{"label":"Hook","time":"0-3s","line":"","delivery":""}}, ...4-7 scenes],
   "hooksToTest":["line (family)","line (family)","line (family)"],
   "captionLine":"one specific line, no hashtags","tags":["#tag1","#tag2"],
   "whyThisOne":"one sentence on the mechanism","score":7,
   "sources":[{{"title":"","url":""}}]}} x3 ]}}"""
    t, _ = G.generate(prompt, SYSTEM, json_out=True, temperature=0.9)
    return G.parse_json(t)


def formatted(letter, idea):
    out = [f"**VERSION {letter} - {idea['hookFamily']} (~{idea['length']}s)**",
           f"- **Why this one:** {idea.get('whyThisOne','')}",
           f"- **On-screen text (first 3-5s):** {idea['onScreen']}", ""]
    for n, s in enumerate(idea["scenes"], 1):
        out += [f"**Scene {n} - {s['label']} ({s['time']})**", f"> {s['line']}", "", f"*Delivery:* {s['delivery']}", "", "[pause]", ""]
    out += [f"**Last line:** \"{idea['scenes'][-1]['line']}\"", "", "- **Hooks to test:**"]
    out += [f"  - {h}" for h in idea["hooksToTest"][:3]]
    out += [f"- **Caption:** {idea['caption']}"]
    return "\n".join(out)


def build_ideas(raw, state):
    used = {i["id"] for i in state["ideas"]}
    n = 1
    ideas = []
    for k, r in enumerate(raw["ideas"][:3]):
        scenes = [s for s in r.get("scenes", []) if s.get("line")]
        if not 4 <= len(scenes) <= 7:
            raise ValueError(f"idea {k+1} has {len(scenes)} scenes")
        tags = [t if t.startswith("#") else "#" + t for t in (r.get("tags") or [])][:2]
        while f"tiktok-{TODAY}-{n}" in used:
            n += 1
        iid = f"tiktok-{TODAY}-{n}"; used.add(iid)
        idea = {"id": iid, "title": r["title"], "hook": scenes[0]["line"], "why": r.get("why", ""),
                "format": f"Talking head {r.get('length', 30)}s", "hookFamily": r.get("hookFamily", ""),
                "length": int(r.get("length", 30)), "onScreen": r.get("onScreen", ""), "scenes": scenes,
                "hooksToTest": (r.get("hooksToTest") or [])[:3],
                "caption": f"{re.sub(r'#\\S+', '', r.get('captionLine','')).strip()} {TAGS} {' '.join(tags)}".strip(),
                "script": "\n[pause]\n".join(s["line"] for s in scenes),
                "whyThisOne": r.get("whyThisOne", ""), "score": int(r.get("score", 6)),
                "sources": [s for s in (r.get("sources") or []) if s.get("url")], "status": "pending",
                "createdAt": ISO, "madeBy": "gemini"}
        idea["formatted"] = formatted(LETTERS[k], idea)
        idea.pop("whyThisOne")
        ideas.append(idea)
    faith = sum(1 for i in ideas if FAITH.search(i["script"] + " " + i["title"]))
    fams = {i["hookFamily"].lower() for i in ideas}
    if len(ideas) != 3 or faith > 1 or len(fams) < 3:
        raise ValueError(f"rule check failed: {len(ideas)} ideas, {faith} faith, {len(fams)} hook families")
    return ideas


def brief(state, ideas):
    approved = [i for i in state["ideas"] if i.get("status") == "approved"]
    pending = sum(1 for i in state["ideas"] if i.get("status") == "pending") + len(ideas)
    rev = state.get("review") or {}
    best = max(ideas, key=lambda i: i["score"])
    return {"date": str(TODAY), "createdAt": ISO,
            "headline": (rev.get("headline") or f"3 new scripts for {TODAY:%A}")[:90],
            "summary": f"{rev.get('summary','')} Today's best new idea: {best['title']}.".strip(),
            "filmToday": [f"{i['title']} — {i['hook']}" for i in approved[:2]] + [f"{best['title']} — {best['hook']}"],
            "approvals": [f"{pending} scripts waiting for your review"] + [f"Waiting on Omar: {i['title']}" for i in approved[:5]],
            "notes": ["Written by the Gemini team (free tier), not Claude."]}


def main():
    state, metrics = load(STATE), load(METRICS, {})
    fmt = open(FORMAT, encoding="utf-8").read()
    patch = {"team": "tiktok", "at": ISO, "log": [], "agents": {}}
    nxt = (NOW + datetime.timedelta(days=1)).strftime("%Y-%m-%dT14:41:00Z")
    if RESEARCH_DAY:
        patch["review"] = review_step(state, metrics)
        state["review"] = patch["review"]
        patch["log"].append({"t": ISO, "agent": "Performance Reviewer", "msg": patch["review"].get("headline", "Review done")})
        patch["research"] = research_step(state, metrics)
        state.setdefault("research", []).insert(0, patch["research"])
        patch["log"].append({"t": ISO, "agent": "Analyst", "msg": f"Found {len(patch['research']['items'])} things working right now"})
        rd = f"Research day: reviewed and researched {TODAY}"
    else:
        rd = f"Writing day: using {(state.get('review') or {}).get('date','last')} review and research"
    last_err = None
    for _ in range(3):
        try:
            raw = write_step(state, fmt)
            ideas = build_ideas(raw, state)
            break
        except Exception as e:
            last_err = e; print("retrying write:", e, flush=True)
    else:
        raise RuntimeError(f"Copywriter failed 3 times: {last_err}")
    patch["ideas"] = ideas
    patch["brief"] = brief(state, ideas)
    patch["log"] += [{"t": ISO, "agent": "Strategist", "msg": raw.get("strategy", "Picked 3 angles")[:200]},
                     {"t": ISO, "agent": "Copywriter", "msg": "Wrote 3 scripts: " + "; ".join(i["title"] for i in ideas)}]
    for aid, doing in [("reviewer", rd), ("analyst", rd), ("strategist", raw.get("strategy", "")[:120]),
                       ("copywriter", "Wrote 3 scripts (Gemini)")]:
        patch["agents"][aid] = {"status": "ok", "doing": doing, "lastRun": ISO, "nextRun": nxt}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(patch, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("Wrote", OUT, "-", ", ".join(i["title"] for i in ideas))


if __name__ == "__main__":
    main()
