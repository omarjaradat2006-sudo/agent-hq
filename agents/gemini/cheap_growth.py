"""Cheap Growth agent for LinkedAI (Gemini free tier, Oracle server). Finds $0-50 ways to get LinkedAI installs.

Usage:
  python3 agents/gemini/cheap_growth.py chunk      # hourly (Sat+Sun from 3 AM): research ONE topic with 1 Gemini search call,
                                                   # save it to ~/research/cheap-growth/<topic>.json. Skips topics collected
                                                   # in the last FRESH_DAYS days, so most runs make 0 calls.
  python3 agents/gemini/cheap_growth.py assemble   # weekly: 1 Gemini call (no search) turns the saved research + what Omar
                                                   # tried into a ranked plan -> out/cheapgrowth_patch.json
  python3 agents/gemini/cheap_growth.py apply      # merge the patch into data/linkedai/state.json (no Gemini call)
  python3 agents/gemini/cheap_growth.py status     # show which research chunks are saved and how old they are

Nothing here posts, messages, buys or spends anything. It only writes suggestions for Omar.
"""
import json, os, re, sys, time, datetime, urllib.request
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(__file__))
import gemini as G

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = os.path.expanduser(os.environ.get("CHEAP_GROWTH_DIR", "~/research/cheap-growth"))
STATE = os.path.join(ROOT, "data", "linkedai", "state.json")
PATCH = os.path.join(ROOT, "out", "cheapgrowth_patch.json")
TZ = ZoneInfo("America/Toronto")
NOW = datetime.datetime.now(datetime.timezone.utc)
ISO = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
TODAY = NOW.astimezone(TZ).date()
FRESH_DAYS = 5          # a topic researched less than 5 days ago is skipped (no Gemini call)
RETRY_MIN = 50          # a topic that failed is retried by the next hourly run, not the same one
BUDGET = 50             # Omar's starting budget in USD
STORE_URL = "https://chromewebstore.google.com/detail/linkedai-%E2%80%94-smart-linkedin/pjbdjikbmncplbhiljcdipkhoidklngp"

PRODUCT = """LinkedAI: a free Chrome extension (Chrome Web Store, live) by Omar Jaradat, a university student in Ontario, Canada.
It works on LinkedIn: reads a profile and summarizes the person; writes outreach/connection messages that find real
common ground between the user's profile and the other person's (3 tones); reads a LinkedIn job post and writes a
tailored resume + cover letter (9 designs, downloadable, discounted bundle); profile tips; human-sounding writing.
Freemium: free credits, Pro monthly/yearly (yearly 20% off). Google sign-in. Also a free AI resume/LinkedIn audit page
(https://linkedai-audit.web.app). Store page: """ + STORE_URL + """
Audience: job seekers, students and new grads, career changers, people networking on LinkedIn.
Status: public but almost no users yet. Budget: about $50 total to start. Omar's own TikTok already promotes it,
so look for channels BEYOND his TikTok."""

# One topic = one Gemini search call. Order = research order.
TOPICS = [
    ("cws", "Chrome Web Store", "Chrome Web Store listing optimization and search ranking for extensions in 2026 (title, short description, keywords, screenshots, promo tile, category, what the current Chrome Web Store ranking factors are), and LEGITIMATE ways to get the first real reviews (in-extension review prompts, asking real users; note the store's policy against fake or incentivized reviews)."),
    ("reddit", "Reddit and communities", "Which subreddits, Discord servers, Facebook groups and forums job seekers use right now to ask for LinkedIn, resume and job-search help (e.g. r/jobs, r/resumes, r/careerguidance, r/linkedin, r/cscareerquestions, r/csMajors, r/jobsearchhacks, r/forhire, Canadian ones like r/askTO/r/PersonalFinanceCanada career threads), their member counts and CURRENT self-promotion rules, and how indie Chrome extension makers have successfully shared tools there without being banned."),
    ("launch", "Launch sites and directories", "Free or cheap places to launch and list a Chrome extension / AI tool in 2026: Product Hunt (how launches work now, best day, what gets featured), free AI tool directories (There's An AI For That, Futurepedia, Toolify, AI tool lists), extension directories, Hacker News Show HN, BetaList, Uneed, Microlaunch, Peerlist, Indie Hackers. Include current submission costs (free vs paid) and which ones actually send traffic."),
    ("newsletters", "Newsletters", "Job-search, career, student and AI-tools newsletters that feature new tools for free or take cheap sponsorships (under $50) in 2026, how to get featured, and their audience size and price where public."),
    ("students", "Students and campuses", "Free ways to reach university and college students in Canada (Ontario especially, e.g. Ontario Tech, UofT, TMU, York, Waterloo, McMaster) with a job-search tool: career centres, co-op offices, student clubs and societies, campus Discord servers, student ambassador programs, LinkedIn-for-students workshops, student deal sites (e.g. student discount listings), and how student founders got their first users this way."),
    ("linkedin", "LinkedIn itself", "Organic LinkedIn strategies in 2026 for a solo founder to promote a LinkedIn productivity tool: what post formats get reach now (build in public, carousels/document posts, before/after examples), commenting strategy, LinkedIn groups, LinkedIn newsletters, and any LinkedIn rules about promoting third-party extensions."),
    ("creators", "Micro-creators", "Where to hire micro-creators (1k-20k followers) on TikTok, Instagram, LinkedIn and YouTube Shorts to post about an app for about $10-50 per post in 2026: Fiverr/UGC gigs, Collabstr, Whop Content Rewards (pay per view campaigns), TikTok Creator Marketplace/TikTok One, Insense, Billo, career-tok creators who take small deals, and how to brief them. Include real current prices."),
    ("ads", "Small ad tests", "How to run a $10-30 ad test for a free Chrome extension in 2026: Reddit Ads minimum budgets and targeting by subreddit, Google Ads search for extension keywords, TikTok Promote, Meta/Instagram boost, LinkedIn ads minimums, Microsoft Ads, and which give the cheapest install for job-seeker audiences. Include real minimum spends."),
    ("partners", "Affiliates, partners and free listings", "Affiliate and partner deals for a small SaaS/Chrome extension in 2026: free affiliate platforms (e.g. Rewardful/FirstPromoter/Lemon Squeezy/Stripe-based options, revenue-share deals), career coaches and resume writers who might recommend tools, job boards and bootcamps that list free tools, alternativeto.net/SaaSHub/G2/Capterra free listings, 'best LinkedIn tools' listicle bloggers who accept submissions, and student-startup programs with free perks."),
]

STYLE = """Writing rules for every post/message you write for Omar: plain, human, like a real student founder talking.
No emojis. No em dashes. No hype words (revolutionary, game-changer, unlock, supercharge, elevate, seamless).
Short sentences. For Reddit and communities: say honestly he made it, give real value first, follow that
community's self-promo rule. Never suggest fake reviews, fake accounts, buying reviews, vote rings or spam."""


def load(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def age_days(iso):
    try:
        return (NOW - datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)).total_seconds() / 86400
    except Exception:
        return 999


def topic_file(key):
    return os.path.join(RES, f"{key}.json")


def due_topic():
    """First topic with no fresh research, skipping ones that failed less than RETRY_MIN minutes ago."""
    for key, name, q in TOPICS:
        f = load(topic_file(key), {})
        if f.get("methods") and age_days(f.get("at", "")) < FRESH_DAYS:
            continue
        if f.get("failedAt") and age_days(f["failedAt"]) * 1440 < RETRY_MIN:
            continue
        return key, name, q, f
    return None


def chunk():
    os.makedirs(RES, exist_ok=True)
    t = due_topic()
    if not t:
        print(f"{ISO} cheap-growth: all {len(TOPICS)} research chunks are fresh, nothing to do (0 Gemini calls)")
        return
    key, name, q, old = t
    print(f"{ISO} cheap-growth: researching '{name}' (1 Gemini search call)", flush=True)
    system = "You research cheap, real, current marketing channels for a tiny one-person software product. Only report things you actually found in search results. Never invent prices, member counts, rules or links."
    prompt = f"""Today is {TODAY}. Product:\n{PRODUCT}\n\nSearch the web for: {q}

Return ONLY a JSON object (no prose around it):
{{"methods":[{{"name":"short name of the method/place","channel":"{name}","cost":"$0 or real price","costUSD":0,
"timeMinutes":30,"audience":"who is there, with real size if found","expected":"realistic result for a brand-new tool",
"steps":["exact step 1","step 2","..."],"rules":"current rules/limits that matter (self-promo, fees, approval)",
"links":[{{"title":"","url":"real URL you saw"}}],"evidence":"what you found that supports this, with numbers"}}],
"notes":"anything important that changed recently"}}
Give 4 to 7 methods, cheapest and most likely to work first. If a price or number isn't in the results, write "[verify]"."""
    try:
        text, sources = G.generate(prompt, system, search=True, temperature=0.3, retries=1)
        data = G.parse_json(text)
        methods = data.get("methods") if isinstance(data, dict) else data
        if not isinstance(methods, list) or not methods:
            raise RuntimeError("no methods in reply")
    except Exception as e:
        old["failedAt"] = ISO
        old["lastError"] = str(e)[:300]
        json.dump(old, open(topic_file(key), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"!! cheap-growth chunk '{key}' failed: {str(e)[:200]} (next hourly run retries it)")
        sys.exit(1)
    out = {"topic": key, "name": name, "at": ISO, "methods": methods[:8],
           "notes": (data.get("notes") if isinstance(data, dict) else "") or "",
           "sources": [{"title": a, "url": b} for a, b in sources[:15]]}
    json.dump(out, open(topic_file(key), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"saved {len(out['methods'])} methods to {topic_file(key)}")


def store_stats():
    """Free (no Gemini): read LinkedAI's public user count and rating from its Chrome Web Store page."""
    try:
        req = urllib.request.Request(STORE_URL + "?hl=en", headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/130 Safari/537.36", "Accept-Language": "en"})
        html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
        users = re.search(r"([\d,]+)\s+users", html)
        rating = re.search(r"([0-5](?:\.\d)?)\s*out of 5", html) or re.search(r'"ratingValue"\s*:\s*"?([0-5](?:\.\d+)?)', html)
        count = re.search(r"([\d,]+)\s+ratings?", html)
        return {"at": ISO, "users": int(users.group(1).replace(",", "")) if users else None,
                "rating": float(rating.group(1)) if rating else None,
                "ratings": int(count.group(1).replace(",", "")) if count else 0}
    except Exception as e:
        print("store stats unavailable:", str(e)[:150])
        return None


def assemble():
    state = load(STATE, {})
    tried = state.get("cheapGrowthTried", [])
    prev = state.get("cheapGrowth", {}) or {}
    chunks = []
    for key, name, _ in TOPICS:
        f = load(topic_file(key), {})
        if f.get("methods"):
            chunks.append({"topic": key, "channel": name, "daysOld": round(age_days(f.get("at", "")), 1),
                           "methods": f["methods"], "notes": f.get("notes", ""), "sources": f.get("sources", [])[:6]})
    if not chunks:
        raise SystemExit("!! no research saved yet: run the chunk job first")
    missing = [n for k, n, _ in TOPICS if not any(c["topic"] == k for c in chunks)]
    spent = round(sum(float(x.get("spent") or 0) for x in tried), 2)
    store = store_stats()
    hist = (state.get("cheapGrowthStore") or [])
    team = {k: state.get(k) for k in ("brief",) if state.get(k)}
    system = "You are the Cheap Growth agent on Omar's Agent HQ. You turn saved research into a practical weekly plan. Use only facts in the research. Never invent prices, numbers or links."
    prompt = f"""Today is {TODAY}. Product:\n{PRODUCT}\n\n{STYLE}

Budget: ${BUDGET} total. Already spent: ${spent}. Left: ${round(BUDGET - spent, 2)}.
Chrome Web Store now: {json.dumps(store)}; earlier readings: {json.dumps(hist[:6])}
What Omar already tried or skipped (newest first; status tried = he did it, skipped = he doesn't want it):
{json.dumps(tried[:30], ensure_ascii=False)}
Last week's top 3: {json.dumps(prev.get("thisWeek", []))}
LinkedAI team's latest brief: {json.dumps(team, ensure_ascii=False)[:1500]}

Saved research (each chunk was collected by an hourly job; daysOld = how old it is):
{json.dumps(chunks, ensure_ascii=False)[:60000]}

Make this week's plan. Rules:
- Merge duplicates. Rank every method by (expected installs per dollar and per hour, how likely it works for a brand-new tool with no reviews, and fit with job seekers). Free first unless a paid one is clearly better.
- Pick exactly 3 for THIS WEEK that Omar can do in under 2 hours total. At most one paid, and it must fit the budget left. Don't pick skipped methods. Don't repeat a tried method unless its result says it worked; if so, give the next step.
- Each method needs exact steps and a READY-TO-USE post or message he can paste as-is (follow the writing rules; for Reddit include a title).
- Paid ones: needsYes = true and the exact cost. Nothing gets posted or paid automatically.
- Give one followUp line for each tried method in the list above (what the result means, what to do next). Empty list if none.

Return ONE JSON object:
{{"headline":"one line","summary":"2-3 plain sentences","thisWeek":["id","id","id"],
"methods":[{{"id":"short-kebab-id","name":"","channel":"","cost":"$0","costUSD":0,"needsYes":false,"timeMinutes":20,
"expected":"realistic result","score":8,"why":"one line","steps":["..."],
"post":{{"where":"exact place","title":"title if needed or empty","text":"the full ready post/message"}},
"links":[{{"title":"","url":""}}],"rules":"rules to respect"}}],
"followUps":[{{"id":"tried method id","advice":""}}],
"log":["2-3 short lines on what you did"]}}
Give 8 to 14 methods in ranked order (best first)."""
    raw = None
    for attempt in range(2):
        try:
            text, _ = G.generate(prompt, system, json_out=True, temperature=0.6)
            raw = G.parse_json(text)
            if isinstance(raw, dict) and raw.get("methods"):
                break
        except Exception as e:
            print("retrying:", str(e)[:200], flush=True)
            raw = None
    if not isinstance(raw, dict) or not raw.get("methods"):
        raise SystemExit("!! Gemini didn't return a usable plan")
    methods, seen = [], set()
    skipped = {x.get("id") for x in tried if x.get("status") == "skipped"}
    for m in raw["methods"]:
        if not isinstance(m, dict) or not m.get("name"):
            continue
        mid = re.sub(r"[^a-z0-9]+", "-", str(m.get("id") or m["name"]).lower()).strip("-")[:48] or f"m{len(methods)+1}"
        if mid in seen:
            continue
        seen.add(mid); m["id"] = mid
        try:
            m["costUSD"] = float(m.get("costUSD") or 0)
        except (TypeError, ValueError):
            m["costUSD"] = 0.0
        m["needsYes"] = bool(m.get("needsYes")) or m["costUSD"] > 0      # anything that costs money needs Omar's yes
        m["links"] = [l for l in (m.get("links") or []) if isinstance(l, dict) and str(l.get("url", "")).startswith("http")][:4]
        for k in ("post",):
            if not isinstance(m.get(k), dict):
                m[k] = {"where": "", "title": "", "text": str(m.get(k) or "")}
            m[k]["text"] = re.sub(r"\s*[—–]\s*", ", ", str(m[k].get("text", "")))   # no em/en dashes
        methods.append(m)
    # top 3: Gemini's picks if valid, else best-ranked; never skipped; at most one paid, within budget
    left = BUDGET - spent
    ids = [re.sub(r"[^a-z0-9]+", "-", str(x).lower()).strip("-")[:48] for x in (raw.get("thisWeek") or [])]
    order = [i for i in ids if i in seen] + [m["id"] for m in methods]
    top, paid = [], 0
    for i in order:
        m = next(x for x in methods if x["id"] == i)
        if i in top or i in skipped:
            continue
        if m["costUSD"] > 0 and (paid >= 1 or m["costUSD"] > left):
            continue
        paid += m["costUSD"] > 0
        top.append(i)
        if len(top) == 3:
            break
    plan = {"date": str(TODAY), "createdAt": ISO, "headline": str(raw.get("headline", ""))[:200],
            "summary": str(raw.get("summary", ""))[:800], "thisWeek": top, "methods": methods[:16],
            "followUps": [f for f in (raw.get("followUps") or []) if isinstance(f, dict)][:10],
            "budget": {"total": BUDGET, "spent": spent, "left": round(left, 2)},
            "research": {"chunks": len(chunks), "of": len(TOPICS), "missing": missing,
                         "oldestDays": max(c["daysOld"] for c in chunks)}}
    patch = {"at": ISO, "plan": plan, "store": store,
             "log": [str(x)[:240] for x in (raw.get("log") or [])][:3] or [f"Ranked {len(methods)} cheap growth methods, picked 3 for this week."]}
    os.makedirs(os.path.dirname(PATCH), exist_ok=True)
    json.dump(patch, open(PATCH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"cheap-growth plan: {len(methods)} methods, this week = {top}, research {len(chunks)}/{len(TOPICS)} chunks")


def apply():
    """Merge the plan into the LATEST state.json. Never touches cheapGrowthTried (Omar's own record)."""
    patch = load(PATCH)
    if not patch:
        raise SystemExit("!! no patch to apply")
    s = load(STATE, {})
    plan = patch["plan"]
    old = s.get("cheapGrowth")
    if old and old.get("date") != plan["date"]:
        s["cheapGrowthHistory"] = ([{"date": old.get("date"), "headline": old.get("headline"), "thisWeek": old.get("thisWeek")}]
                                   + s.get("cheapGrowthHistory", []))[:12]
    s["cheapGrowth"] = plan
    if patch.get("store"):
        s["cheapGrowthStore"] = ([patch["store"]] + s.get("cheapGrowthStore", []))[:26]
    s["log"] = ([{"t": patch["at"], "agent": "Cheap Growth", "msg": m} for m in patch["log"]] + s.get("log", []))[:100]
    names = [next((m["name"] for m in plan["methods"] if m["id"] == i), i) for i in plan["thisWeek"]]
    entry = {"id": "cheap", "name": "Cheap Growth", "role": "$0-50 ways to get installs, weekly", "status": "ok",
             "doing": ("This week: " + "; ".join(names))[:140], "lastRun": patch["at"]}
    ag = s.setdefault("agents", [])
    for a in ag:
        if a.get("id") == "cheap":
            a.update(entry); break
    else:
        ag.append(entry)
    s["updatedAt"] = patch["at"]
    json.dump(s, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("merged cheap growth plan into data/linkedai/state.json")


def status():
    for key, name, _ in TOPICS:
        f = load(topic_file(key), {})
        a = f"{age_days(f['at']):.1f} days old, {len(f.get('methods', []))} methods" if f.get("methods") else "not collected yet"
        if f.get("failedAt"):
            a += f" (last fail {f['failedAt']}: {f.get('lastError', '')[:80]})"
        print(f"{key:12} {name:38} {a}")


if __name__ == "__main__":
    {"chunk": chunk, "assemble": assemble, "apply": apply, "status": status}[sys.argv[1] if len(sys.argv) > 1 else "status"]()
