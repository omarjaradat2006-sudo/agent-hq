"""LinkedAI Promo Studio (Gemini free tier, Oracle server). Connects the TikTok team and the LinkedAI team.

  promo_studio.py chunk   -> run about once an hour from 3:37 AM Toronto (after the Gemini daily quota resets).
                             Does ONE small research chunk (max 1 Gemini call), saves it to ~/research/promo/ and stops.
                             Anything collected recently is skipped. If nothing is due, it exits without calling Gemini.
  promo_studio.py build   -> Mon/Wed/Fri. Puts the saved research together in ONE Gemini call (retries only if the
                             rules check fails) and writes 2 promo videos for the LinkedAI floor (out/promo_patch.json).

Research chunks:
  style       weekly   your TikTok history (data/tiktok/history.json, pulled daily by the GitHub collector) + the TikTok
                       team's review -> what works for YOU. Numbers are computed by code; Gemini only explains them.
  watch:<id>  hourly   Gemini watches one real AI-tool marketing Short on YouTube (found + counted by the collector,
                       data/linkedai/ad_candidates.json) and breaks down hook, format, shots, why it works.
  social:<a>  max 2/day  Gemini web search for real TikTok / Instagram videos of AI software companies and indie founders
                       in one format. A link is kept only if Google actually loaded it or TikTok's oEmbed confirms it.
No links or numbers are ever invented: every link on the site comes from the research files, never from the writer model.
"""
import json, os, re, sys, glob, datetime, statistics, urllib.request, urllib.parse
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(__file__))
import gemini as G

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RES = os.path.expanduser(os.environ.get("PROMO_RESEARCH_DIR", "~/research/promo"))
TZ = ZoneInfo("America/Toronto")
NOW = datetime.datetime.now(datetime.timezone.utc)
ISO = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
TODAY = NOW.astimezone(TZ).date()
TAGS = "#fyppppppppppppppppppppppp #viral #fyp"
STORE = "https://chromewebstore.google.com/detail/linkedai-%E2%80%94-smart-linkedin/pjbdjikbmncplbhiljcdipkhoidklngp"
PROMO = re.compile(r"linkedai|linked ai|linkedin|resume|r[eé]sum[eé]|cover letter|job (search|hunt|interview|application)|recruiter|hiring|#ad\b|promo", re.I)
BUILDER = re.compile(r"\b(i|we) (just )?(built|made|created|coded|developed|launched)\b|\bmy (app|extension|tool|product|startup|software)\b|\bour (app|extension|tool|product)\b", re.I)
FAKE_RESULT = re.compile(r"\b(got|landed|booked|made)\s+(me\s+)?\$?\d", re.I)
ANGLES = [
    ("found-a-tool", '"I found a tool that..." / "this extension is crazy" creator recommendation videos for AI tools or Chrome extensions'),
    ("problem-solution", "problem-then-solution videos: a frustrating problem shown first, then an AI tool fixes it on screen"),
    ("screen-demo", "pure screen-recording demos of an AI tool or Chrome extension with voiceover or text, fast and satisfying"),
    ("skit", "skits / POV / acted scenes (boss vs employee, recruiter vs candidate, before vs after) used by AI startups to sell their tool"),
    ("reaction", "green-screen or reaction videos where a creator reacts to an AI tool's output, or 'testing AI tools so you don't have to'"),
    ("founder-story", "indie app founders and small AI startups growing on TikTok/Instagram (e.g. faceless demo accounts, 'day in the life', slideshows) and what format their best videos use"),
]
FORMATS = ["I found a tool", "Problem then solution", "Screen demo", "Skit / POV", "Reaction", "Listicle / top tools", "Talking head story", "Before vs after"]

SYSTEM = """You are the Promo Studio for Omar Jaradat's LinkedAI Chrome extension. Omar is a university student in Mississauga who films sit-down talking-head TikToks (self-improvement for young guys) in one take. LinkedAI promos must feel like a regular creator recommending a tool he found, NEVER the builder. Never invent stats, view counts, links, accounts, quotes or user results. If you didn't see a number, leave it empty. Plain English, short sentences."""


def load(p, d=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


def save(rel, obj):
    p = os.path.join(RES, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    obj["collectedAt"] = ISO
    json.dump(obj, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    idx = load(os.path.join(RES, "index.json"), {"runs": []})
    idx["runs"] = ([{"t": ISO, "chunk": rel}] + idx["runs"])[:400]
    json.dump(idx, open(os.path.join(RES, "index.json"), "w"), indent=1)
    print("saved research chunk:", rel, flush=True)


def age_days(obj):
    try:
        t = datetime.datetime.strptime(obj["collectedAt"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        return (NOW - t).total_seconds() / 86400
    except Exception:
        return 1e9


def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (AgentHQ research)"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.geturl(), r.read(200000).decode("utf-8", "ignore")


def my_videos():
    h = load(os.path.join(ROOT, "data", "tiktok", "history.json"), {}) or {}
    vids = h.get("videos") or (load(os.path.join(ROOT, "data", "tiktok", "metrics.json"), {}) or {}).get("topVideos", [])
    out = []
    for v in vids:
        text = f"{v.get('title', '')} {v.get('description', '')}"
        out.append({"id": str(v.get("id")), "title": re.sub(r"#\S+", "", v.get("title") or "").strip()[:110] or "(hashtags only)",
                    "caption": (v.get("description") or "")[:240], "url": (v.get("url") or "").split("?")[0], "views": int(v.get("views") or 0),
                    "likes": int(v.get("likes") or 0), "shares": int(v.get("shares") or 0), "comments": int(v.get("comments") or 0),
                    "duration": v.get("duration"), "published": v.get("published", ""), "promo": bool(PROMO.search(text))})
    return out


# ---------------- research chunks ----------------
def chunk_style():
    vids = my_videos()
    if not vids:
        print("no TikTok videos in the data yet; style chunk skipped"); return False
    org = [v for v in vids if not v["promo"]]
    promos = [v for v in vids if v["promo"]]
    med = statistics.median([v["views"] for v in org]) if org else 0
    buckets = {}
    for v in org:
        d = v.get("duration") or 0
        b = "under 20s" if d < 20 else "20-35s" if d < 35 else "35-50s" if d < 50 else "50-70s" if d < 70 else "70s+"
        buckets.setdefault(b, []).append(v["views"])
    by_len = {b: {"videos": len(x), "medianViews": int(statistics.median(x))} for b, x in buckets.items()}
    top = sorted(org, key=lambda v: v["views"], reverse=True)[:10]
    low = sorted([v for v in org if v["published"] < (NOW - datetime.timedelta(days=3)).strftime("%F")], key=lambda v: v["views"])[:6]
    tstate = load(os.path.join(ROOT, "data", "tiktok", "state.json"), {}) or {}
    rev = tstate.get("review") or {}
    prompt = f"""Today is {TODAY}. These are Omar's REAL TikTok numbers (computed by code, don't change them).
Organic videos: {len(org)}, median views {int(med)}. Median views by length: {json.dumps(by_len)}
Top organic videos: {json.dumps([{k: v[k] for k in ('id', 'title', 'caption', 'views', 'likes', 'shares', 'duration')} for v in top], ensure_ascii=False)}
Weakest organic videos (older than 3 days): {json.dumps([{k: v[k] for k in ('title', 'views', 'duration')} for v in low], ensure_ascii=False)}
His LinkedAI / job promo videos so far (some were PAID boosts, so views don't prove organic pull): {json.dumps([{k: v[k] for k in ('id', 'title', 'views', 'likes', 'shares', 'duration')} for v in promos][:8], ensure_ascii=False)}
His TikTok team's latest review: {json.dumps({k: rev.get(k) for k in ('headline', 'summary', 'doMore', 'stopDoing')}, ensure_ascii=False)[:2500]}
He films sit-down, one take, talking to camera, regular-guy voice (never a guru), edited automatically (captions, zooms at pauses).

Work out what works for HIM and how a LinkedAI promo should borrow it so it feels like his normal videos. Return JSON:
{{"summary":"2-3 sentences to 'you' with real numbers","whatWorks":["3-5 patterns, each tied to a real video title + views"],
"hookPatterns":["3-4 kinds of first lines that worked for him, with the real example"],"bestLength":"e.g. 35-50s, from the numbers",
"avoid":["2-3 things"],"promoLessons":["2-3 lessons from his past promo videos (say paid if likely)"],
"howToBlendPromos":["3 ways to make a LinkedAI promo feel like his own video"],"modelVideoIds":["ids of 3-4 of his videos that are the best models for a creator-style promo"]}}"""
    t, _ = G.generate(prompt, SYSTEM, json_out=True, temperature=0.4, retries=1)
    prof = G.parse_json(t)
    ids = {v["id"] for v in vids}
    prof["modelVideoIds"] = [i for i in (prof.get("modelVideoIds") or []) if str(i) in ids][:4]
    prof.update(organicVideos=len(org), medianViews=int(med), byLength=by_len,
                top=[{k: v[k] for k in ("id", "title", "url", "views", "duration")} for v in top[:6]],
                promos=[{k: v[k] for k in ("id", "title", "url", "views", "duration")} for v in promos[:6]])
    save("style.json", prof)
    return True


def candidates():
    c = load(os.path.join(ROOT, "data", "linkedai", "ad_candidates.json"), {}) or {}
    def english(t):   # skip titles mostly in other scripts (Hindi, Telugu, ...): Omar posts in English
        letters = [ch for ch in t if ch.isalpha()]
        return not letters or sum(ch.isascii() for ch in letters) / len(letters) > 0.8
    # 30M+ views on a brand channel = paid ad views, not a format that wins on its own
    return [v for v in c.get("videos", []) if (v.get("duration") or 0) <= 180 and (v.get("views") or 0) < 30_000_000 and english(v.get("title", ""))]


def chunk_watch(v):
    url = f"https://www.youtube.com/watch?v={v['id']}"
    prompt = [{"file_data": {"file_uri": url}}, {"text": f"""Watch this Short. Title: "{v.get('title')}" by {v.get('channel')} ({v.get('views')} views, real number from the YouTube API).
It markets an AI tool / app / Chrome extension (or it's a creator recommending one). Break down how it sells. Return JSON:
{{"isToolPromo":true,"tool":"name of the tool shown, or empty","speaker":"founder | creator recommending | faceless demo | skit actors | other",
"format":"one of {FORMATS}","hookSpoken":"first spoken line, max 15 words, or empty","hookOnScreen":"first on-screen text, max 12 words, or empty",
"beats":[{{"t":"0-3s","what":"what happens / is said, in your words"}}] (3-7 beats),
"screenShots":["what the screen recording shows, step by step"],"cta":"how it ends / what it asks",
"whyItWorks":"2-3 sentences: the mechanism (tension, payoff, proof)","copyForLinkedAI":"1-2 sentences: how a sit-down creator could reuse this format for a LinkedIn tool"}}
If it's not about a tool at all, set isToolPromo false and keep the rest short."""}]
    t, _ = G.generate(prompt, SYSTEM, json_out=True, temperature=0.3, retries=1)
    d = G.parse_json(t)
    d.update(id=v["id"], platform="YouTube Shorts", url=url, title=v.get("title"), account=v.get("channel"),
             views=v.get("views"), viewsChecked=True, published=v.get("published"), outlier=v.get("outlier"))
    save(f"watched/{v['id']}.json", d)
    return True


def tiktok_ok(url):
    try:
        _, body = http_get("https://www.tiktok.com/oembed?url=" + urllib.parse.quote(url, safe=""))
        j = json.loads(body)
        return j.get("author_name") or j.get("author_unique_id") or True
    except Exception:
        return None


def chunk_social(key, desc):
    prompt = f"""Today is {TODAY}. Search the web (TikTok, Instagram, news and marketing blogs that link to real videos) for REAL examples of: {desc}.
Focus on AI software companies, AI Chrome extensions, productivity / job-search / LinkedIn tools and indie app founders, from the last 12 months.
For each example give the exact video URL you actually found (tiktok.com/@.../video/... or instagram.com/reel/... or /p/...). Never guess a URL.
Return 4-6 examples in a ```json block:
[{{"platform":"TikTok|Instagram","account":"@handle","company":"tool / company","url":"","views":"only a number you actually saw, else empty","viewsSeenOn":"where you saw it",
"format":"one of {FORMATS}","whatHappens":"1-2 sentences in your words","whyItWorks":"1-2 sentences","copyForLinkedAI":"1 sentence"}}]"""
    t, sources = G.generate(prompt, SYSTEM, search=True, temperature=0.4, retries=1)
    items = G.parse_json(t)
    if isinstance(items, dict):
        items = items.get("items") or items.get("examples") or []
    real, pages = set(), []
    for title, u in sources[:25]:   # grounding links are Google redirects: follow them to the page Google actually read
        try:
            final, _ = http_get(u, timeout=12)
            real.add(final.split("?")[0].rstrip("/")); pages.append({"title": title, "url": final})
        except Exception:
            pass
    kept = []
    for it in items if isinstance(items, list) else []:
        u = (it.get("url") or "").strip().split("?")[0].rstrip("/")
        if not re.match(r"https://(www\.)?(tiktok\.com/@[\w.]+/(video|photo)/\d+|instagram\.com/(reel|reels|p)/[\w-]+)", u):
            continue
        how = None
        if u in real:
            how = "Google loaded this page"
        elif "tiktok.com" in u:
            a = tiktok_ok(u)
            if a:
                how = "TikTok confirmed the video exists" + (f" (by {a})" if isinstance(a, str) else "")
        if not how:
            continue   # unverified link: dropped, never shown
        it.update(url=u, linkCheck=how, viewsChecked=False, angle=key)
        if not re.search(r"\d", str(it.get("views", ""))):
            it["views"] = ""
        kept.append(it)
    save(f"social/{key}.json", {"angle": key, "items": kept, "pages": pages[:10], "dropped": max(0, len(items) - len(kept)) if isinstance(items, list) else 0})
    return True


def chunk():
    os.makedirs(RES, exist_ok=True)
    idx = load(os.path.join(RES, "index.json"), {"runs": []})
    today_runs = [r["chunk"] for r in idx["runs"] if r["t"][:10] == NOW.strftime("%F")]
    social_today = sum(1 for c in today_runs if c.startswith("social/"))
    st = load(os.path.join(RES, "style.json"))
    if not st or age_days(st) > 6:
        if chunk_style():
            return
    watched = {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(RES, "watched", "*.json"))}
    todo = [v for v in candidates() if v["id"] not in watched]
    todo.sort(key=lambda v: ((v.get("outlier") or 0) >= 3, v.get("views") or 0), reverse=True)
    due_social = [(k, d) for k, d in ANGLES if age_days(load(os.path.join(RES, "social", f"{k}.json"), {}) or {}) > 14]
    if due_social and social_today == 0:
        return chunk_social(*due_social[0])
    if todo:
        return chunk_watch(todo[0])
    if due_social and social_today < 2:
        return chunk_social(*due_social[0])
    print("nothing due: all research is fresh. No Gemini call made.")


# ---------------- build: put the research together ----------------
def library():
    lib = {}
    for p in glob.glob(os.path.join(RES, "watched", "*.json")):
        d = load(p) or {}
        if d.get("isToolPromo") is False:
            continue
        lib["yt:" + d["id"]] = {"whose": "theirs", "platform": "YouTube Shorts", "account": d.get("account"), "title": d.get("title"), "url": d.get("url"),
                               "views": d.get("views"), "viewsChecked": True, "format": d.get("format"), "tool": d.get("tool"), "speaker": d.get("speaker"),
                               "hook": d.get("hookSpoken") or d.get("hookOnScreen"), "beats": d.get("beats"), "screenShots": d.get("screenShots"),
                               "whyItWorks": d.get("whyItWorks"), "copyForLinkedAI": d.get("copyForLinkedAI"), "collectedAt": d.get("collectedAt")}
    n = 0
    for p in sorted(glob.glob(os.path.join(RES, "social", "*.json"))):
        d = load(p) or {}
        if age_days(d) > 45:
            continue
        for it in d.get("items", []):
            n += 1
            lib[f"so:{n}"] = {"whose": "theirs", "platform": it.get("platform"), "account": it.get("account"), "title": it.get("company"), "url": it["url"],
                              "views": it.get("views"), "viewsChecked": False, "viewsSeenOn": it.get("viewsSeenOn"), "linkCheck": it.get("linkCheck"),
                              "format": it.get("format"), "whatHappens": it.get("whatHappens"), "whyItWorks": it.get("whyItWorks"),
                              "copyForLinkedAI": it.get("copyForLinkedAI"), "collectedAt": d.get("collectedAt")}
    st = load(os.path.join(RES, "style.json"), {}) or {}
    mine = {v["id"]: v for v in my_videos()}
    for vid in list(st.get("modelVideoIds") or []) + [v["id"] for v in st.get("top", [])[:4]] + [v["id"] for v in st.get("promos", [])[:3]]:
        v = mine.get(str(vid))
        if v and "me:" + v["id"] not in lib:
            lib["me:" + v["id"]] = {"whose": "yours", "platform": "TikTok", "account": "@o.hustle44", "title": v["title"], "url": v["url"], "views": v["views"],
                                   "viewsChecked": True, "duration": v["duration"], "promo": v["promo"], "caption": v["caption"]}
    return lib, st


def linkedai_features():
    m = open(os.path.join(ROOT, "agents", "SYSTEM_MAP.md"), encoding="utf-8").read()
    s = m.split("## LINKEDAI", 1)[-1].split("\n## ", 1)[0]
    return s[:3500]


def fmt_md(letter, i, model):
    out = [f"**VERSION {letter} - {i['hookFamily']} (~{i['length']}s)**",
           f"- **Why this one:** {i.get('whyThisOne', '')}",
           f"- **On-screen text (first 3-5s):** {i['onScreen']}", ""]
    for n, s in enumerate(i["scenes"], 1):
        out += [f"**Scene {n} - {s['label']} ({s['time']})**", f"> {s['line']}", "", f"*Delivery:* {s['delivery']}", "", "[pause]", ""]
    out += [f"**Last line:** \"{i['scenes'][-1]['line']}\"", "", "- **Hooks to test:**"]
    out += [f"  - {h}" for h in i["hooksToTest"][:3]]
    out += [f"- **Caption:** {i['caption']}", "",
            f"**Modeled on ({'your video' if model['whose'] == 'yours' else 'their video'}):** {model.get('account') or ''} - {model.get('title') or ''}",
            f"- {model['url']}",
            f"- Views: {model.get('views') or 'not seen'}" + ("" if model.get("viewsChecked") else " (from search, not checked)"),
            f"- What to copy: {i.get('whyModel', '')}", "", "**Screen recordings to capture (LinkedAI):**"]
    out += [f"- {s.get('at', '')}: {s.get('record', '')}" + (f" ({s['how']})" if s.get("how") else "") for s in i["shots"]]
    return "\n".join(out)


def build():
    lib, st = library()
    if not lib:
        raise RuntimeError("No research saved yet on the server (~/research/promo). Let the hourly chunks run first.")
    lstate = load(os.path.join(ROOT, "data", "linkedai", "state.json"), {}) or {}
    prev = [i for i in lstate.get("ideas", []) if str(i.get("format", "")).startswith("Promo video")][-12:]
    used_models = [i.get("modeledOn", {}).get("url") for i in prev]
    fmt = "\n\n".join(open(os.path.join(ROOT, "agents", "formats", f), encoding="utf-8").read()[:9000]
                      for f in ("tiktok-scripts.md", "promo-scripts.md", "promo-videos.md"))
    brief_lib = {k: {x: v.get(x) for x in ("whose", "platform", "account", "title", "views", "viewsChecked", "format", "hook", "beats",
                                           "screenShots", "whatHappens", "whyItWorks", "copyForLinkedAI", "duration", "promo", "caption") if v.get(x)}
                 for k, v in lib.items()}
    comps = json.dumps(lstate.get("competitors"), ensure_ascii=False)[:2500]
    prompt = f"""Today is {TODAY} ({TODAY:%A}). Write 2 NEW LinkedAI promo videos Omar can film this week, in HIS style.

WHAT WORKS FOR OMAR (from his real TikTok numbers): {json.dumps({k: st.get(k) for k in ('summary', 'whatWorks', 'hookPatterns', 'bestLength', 'avoid', 'promoLessons', 'howToBlendPromos')}, ensure_ascii=False)[:4000]}

RESEARCH LIBRARY (real videos, each with an id; "yours" = Omar's own TikToks, "theirs" = AI tool companies / founders / creators):
{json.dumps(brief_lib, ensure_ascii=False)[:22000]}

LINKEDAI (only these features exist, never invent one): {linkedai_features()}
Competitors (from the LinkedAI team): {comps}
Recent promo videos already written (don't repeat their angle, hook or model): {json.dumps([{'title': i.get('title'), 'format': i.get('format'), 'hook': i.get('hook')} for i in prev], ensure_ascii=False)}
Models already used recently (prefer others): {used_models}

Rules:
- Each video is modeled on ONE library item: give its id in "modeledOnId" (must be an id from the library). The 2 videos use 2 DIFFERENT formats and 2 different models. At least one is modeled on a "theirs" video; borrow its format, then make it feel like Omar's own sit-down style.
- Speaker = a regular creator / student who found LinkedAI. NEVER "I built", "my app", "my extension", "we made". Problem first, tool second; "LinkedAI" lands after the hook. One CTA: "it's on the Chrome Web Store, search LinkedAI" or "link in bio".
- Never invent a result ("got 5 interviews"): write [fill in: your real result]. No job-search stats unless they're in the library.
- "shots": 3-5 screen recordings of the extension to capture, tied to scenes ("Scene 3"), each a concrete step on LinkedIn (which page, which button, what appears).
- Follow the format files below exactly (hook rules, scenes, hooksToTest, VoicePrint pass).
{fmt}

Return JSON only: {{"strategy":"one line","videos":[{{"title":"","angle":"one of {FORMATS}","modeledOnId":"","whyModel":"what to copy from it, 1-2 sentences",
"why":"why this will work for Omar, tied to his numbers or the library","hookFamily":"","length":35,"onScreen":"",
"scenes":[{{"label":"Hook","time":"0-3s","line":"","delivery":""}}, ...4-7 scenes],"hooksToTest":["","",""],
"shots":[{{"at":"Scene 3","record":"","how":""}}],"captionLine":"","tags":["#linkedin","#jobsearch"],"whyThisOne":"","score":7}} x2]}}"""
    last = None
    for attempt in range(3):
        try:
            t, _ = G.generate(prompt, SYSTEM, json_out=True, temperature=0.85, retries=1)
            raw = G.parse_json(t)
            vids = make_ideas(raw, lib, lstate)
            break
        except Exception as e:
            last = e; print("retrying build:", str(e)[:200], flush=True)
            prompt += f"\n\nYOUR LAST ANSWER FAILED THE RULES CHECK: {str(e)[:300]}. Fix it."
    else:
        raise RuntimeError(f"Promo build failed 3 times: {last}")
    adlib = sorted(({"id": k, **{x: v.get(x) for x in ("whose", "platform", "account", "title", "url", "views", "viewsChecked", "viewsSeenOn", "linkCheck",
                                                        "format", "hook", "whatHappens", "whyItWorks", "copyForLinkedAI", "collectedAt")}} for k, v in lib.items()),
                   key=lambda x: (x["whose"] == "theirs", x.get("collectedAt") or ""), reverse=True)[:40]
    idx = load(os.path.join(RES, "index.json"), {"runs": []})
    patch = {"team": "linkedai", "at": ISO, "ideas": vids, "adLibrary": adlib,
             "styleProfile": {k: st.get(k) for k in ("summary", "whatWorks", "hookPatterns", "bestLength", "avoid", "promoLessons", "howToBlendPromos",
                                                      "organicVideos", "medianViews", "top", "promos", "collectedAt")},
             "promoResearch": {"builtAt": ISO, "watched": sum(1 for k in lib if k.startswith("yt:")), "social": sum(1 for k in lib if k.startswith("so:")),
                               "chunksLast7Days": sum(1 for r in idx["runs"] if r["t"] >= (NOW - datetime.timedelta(days=7)).strftime("%FT%TZ"))},
             "log": [{"t": ISO, "agent": "Promo Director", "msg": f"Wrote {len(vids)} promo videos: " + "; ".join(v["title"] for v in vids)},
                     {"t": ISO, "agent": "Ad Scout", "msg": f"Library: {len(adlib)} real videos studied"}],
             "agents": {a: {"status": "ok", "lastRun": ISO, "doing": d} for a, d in (
                 ("director", f"Wrote {len(vids)} promo videos ({raw.get('strategy', '')[:80]})"),
                 ("adscout", f"{sum(1 for k in lib if not k.startswith('me:'))} competitor videos in the library"),
                 ("stylecoach", f"Style profile from {st.get('organicVideos', 0)} of your videos"))}}
    os.makedirs(os.path.join(ROOT, "out"), exist_ok=True)
    json.dump(patch, open(os.path.join(ROOT, "out", "promo_patch.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("Wrote out/promo_patch.json -", "; ".join(v["title"] for v in vids))


def make_ideas(raw, lib, lstate):
    used = {i.get("id") for i in lstate.get("ideas", [])}
    out, models = [], set()
    for k, r in enumerate((raw.get("videos") or [])[:2]):
        scenes = [s for s in r.get("scenes", []) if s.get("line")]
        if not 4 <= len(scenes) <= 7:
            raise ValueError(f"video {k + 1} has {len(scenes)} scenes (needs 4-7)")
        mid = str(r.get("modeledOnId", "")).strip()
        if mid not in lib:
            raise ValueError(f"video {k + 1} modeledOnId '{mid}' is not an id from the library")
        if mid in models:
            raise ValueError("both videos are modeled on the same library item")
        models.add(mid)
        words = " ".join(s["line"] for s in scenes) + " " + " ".join(r.get("hooksToTest") or [])
        if BUILDER.search(words):
            raise ValueError(f"video {k + 1} sounds like the builder ('{BUILDER.search(words).group(0)}'): must be a creator who found the tool")
        if FAKE_RESULT.search(words):
            raise ValueError(f"video {k + 1} claims a result ('{FAKE_RESULT.search(words).group(0)}'): use [fill in: your real result]")
        if not re.search(r"linked\s?ai", words, re.I):
            raise ValueError(f"video {k + 1} never says LinkedAI")
        shots = [s for s in (r.get("shots") or []) if s.get("record")][:5]
        if len(shots) < 2:
            raise ValueError(f"video {k + 1} needs 3-5 screen-recording shots")
        tags = [t if t.startswith("#") else "#" + t for t in (r.get("tags") or [])][:2]
        n = 1
        while f"linkedai-promo-{TODAY}-{n}" in used:
            n += 1
        iid = f"linkedai-promo-{TODAY}-{n}"; used.add(iid)
        m = lib[mid]
        idea = {"id": iid, "title": r.get("title", "LinkedAI promo"), "format": f"Promo video · {r.get('angle', '')}".strip(" ·"),
                "hook": scenes[0]["line"], "why": r.get("why", ""), "hookFamily": r.get("hookFamily", ""), "length": int(r.get("length") or 35),
                "onScreen": r.get("onScreen", ""), "scenes": scenes, "hooksToTest": (r.get("hooksToTest") or [])[:3], "shots": shots,
                "caption": f"{re.sub(r'#\S+', '', r.get('captionLine', '')).strip()} {TAGS} {' '.join(tags)}".strip(),
                "script": "\n[pause]\n".join(s["line"] for s in scenes), "score": int(r.get("score") or 6),
                "modeledOn": {"id": mid, "whose": m["whose"], "platform": m.get("platform"), "account": m.get("account"), "title": m.get("title"),
                              "url": m["url"], "views": m.get("views"), "viewsChecked": m.get("viewsChecked")},
                "sources": [{"title": f"Modeled on: {m.get('account') or ''} {m.get('platform') or ''}".strip(), "url": m["url"]},
                            {"title": "LinkedAI on the Chrome Web Store", "url": STORE}],
                "status": "pending", "createdAt": ISO, "madeBy": "gemini (promo studio)"}
        idea["formatted"] = fmt_md("AB"[k], {**idea, "whyThisOne": r.get("whyThisOne", ""), "whyModel": r.get("whyModel", "")}, m)
        out.append(idea)
    if len(out) != 2:
        raise ValueError(f"needs exactly 2 videos, got {len(out)}")
    if out[0]["format"] == out[1]["format"]:
        raise ValueError("the 2 videos use the same format: make them different")
    if any(v["whose"] == "theirs" for v in lib.values()) and all(v["modeledOn"]["whose"] == "yours" for v in out):
        raise ValueError("at least one video must be modeled on a 'theirs' library video")
    return out


if __name__ == "__main__":
    {"chunk": chunk, "build": build}[sys.argv[1]]()
