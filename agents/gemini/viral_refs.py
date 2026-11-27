"""Viral references for Omar's TikTok: real viral videos from his niche, why each one worked, and his own version.

Runs in SMALL chunks so the free Gemini quota never gets hit all at once:
  viral_refs.py chunk    cron, every hour 3:52-8:52 AM Toronto (after the 3 AM quota reset). Each run does only
                         the NEXT piece of today's research (max 2 Gemini calls) and saves it on the server in
                         ~/research/tiktok-refs/. Anything already collected recently is skipped.
  viral_refs.py status   prints what is saved for today (for Omar over SSH).
  assemble(state)        called by tiktok_team.py at 9:41 AM: joins the saved research into the site. No Gemini.

Real links and numbers only:
  - Links come from the YouTube Data API (via the hourly GitHub collector, data/tiktok/refs_candidates.json), from Omar's own pasted links, or from Gemini web search results.
    Every link is opened by the server (yt-dlp / YouTube API) and views, creator and date are read from the
    platform itself. Gemini never supplies a link or a number; a link that can't be opened is dropped.
  - The breakdown is written by Gemini WATCHING the actual video (YouTube URL passed straight in, or the
    TikTok file uploaded to the Gemini File API), not guessing from a title.
Gemini calls per day: about 6 (1 TikTok web search + 1 per video). Zero Claude.
"""
import json, os, re, sys, time, math, shutil, subprocess, datetime, tempfile, urllib.request, urllib.parse, urllib.error
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(__file__))
import gemini as G

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATE = os.path.join(ROOT, "data", "tiktok", "state.json")
FORMAT = os.path.join(ROOT, "agents", "formats", "tiktok-scripts.md")
CFG = json.load(open(os.path.join(ROOT, "collectors", "niches.json"), encoding="utf-8"))["refs"]
RDIR = os.path.expanduser(os.environ.get("REFS_DIR", "~/research/tiktok-refs"))
TZ = ZoneInfo("America/Toronto")
NOW = datetime.datetime.now(datetime.timezone.utc)
ISO = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
TODAY = NOW.astimezone(TZ).date()
DAYDIR = os.path.join(RDIR, str(TODAY))
CAND = os.path.join(DAYDIR, "candidates.json")
CACHE = os.path.join(RDIR, "breakdowns")
SEEN = os.path.join(RDIR, "seen.json")
MAX_CALLS = int(os.environ.get("REFS_CALLS_PER_CHUNK", "2"))
PER_DAY = int(CFG.get("per_day", 5))
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}

# No job / resume / LinkedIn / LinkedAI content in this, ever (Omar's rule).
BLOCK = re.compile(r"linkedai|linked ?in\b|\bresume|r[eé]sum[eé]|cover letter|job (search|hunt|interview|application|offer)|"
                   r"interview (tips|questions)|recruiter|\bhiring\b|get hired|\bcv\b|#ad\b|sponsored|"
                   r"ex[- ]?muslim|apostate|left islam|leaving islam|why i left|debunk(ing|ed)? islam", re.I)   # never anti-Islam content
FAITH = re.compile(r"\b(allah|quran|qur'an|salah|salat|prayer|pray|islam|islamic|muslim|hadith|deen|dua|prophet|sunnah|ayah|jannah|iman|ramadan)\b", re.I)
AIBIZ = re.compile(r"\b(ai|chatgpt|gpt|claude|gemini|automation|startup|side hustle|business)\b", re.I)


# ---------------- small helpers ----------------
def rjson(p, default=None):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return default


def wjson(p, obj):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    json.dump(obj, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def say(msg):
    print(f"{time.strftime('%F %T')} refs: {msg}", flush=True)


def http_json(url, timeout=30):
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:   # keep the reason (e.g. "API not enabled") in the log, never the key
        body = re.sub(r"key=[\w-]+", "key=***", e.read().decode(errors="ignore"))
        msg = re.search(r'"message":\s*"([^"]+)', body)
        raise urllib.error.HTTPError(e.url, e.code, f"{e.code} {msg.group(1) if msg else e.reason}"[:300], e.headers, None)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def resolve(url, hops=4):
    """Follow redirects by hand (Gemini search gives vertexaisearch redirect links, TikTok gives vm.tiktok.com short links)."""
    op = urllib.request.build_opener(_NoRedirect)
    for _ in range(hops):
        try:
            op.open(urllib.request.Request(url, headers=UA, method="GET"), timeout=15)
            return url
        except urllib.error.HTTPError as e:
            loc = e.headers.get("Location")
            if e.code in (301, 302, 303, 307, 308) and loc:
                url = urllib.parse.urljoin(url, loc)
                continue
            return url
        except Exception:
            return url
    return url


def ytdlp_cmd():
    c = os.environ.get("YTDLP") or shutil.which("yt-dlp") or os.path.expanduser("~/bounce-venv/bin/yt-dlp")
    return [c] if c and os.path.exists(c) else [sys.executable, "-m", "yt_dlp"]


def ytdlp_json(url, extra=(), timeout=120):
    try:
        r = subprocess.run(ytdlp_cmd() + ["-J", "--no-warnings", "--no-playlist", *extra, url],
                           capture_output=True, text=True, timeout=timeout)
        if r.returncode != 0:
            say(f"yt-dlp couldn't open {url}: {r.stderr.strip()[-200:]}")
            return None
        return json.loads(r.stdout)
    except Exception as e:
        say(f"yt-dlp error on {url}: {e}")
        return None


def tiktok_url(u):
    m = re.search(r"tiktok\.com/@([\w.\-]+)/video/(\d{8,25})", u or "")
    return (f"https://www.tiktok.com/@{m.group(1)}/video/{m.group(2)}", m.group(2)) if m else (None, None)


def youtube_id(u):
    m = re.search(r"(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)([\w-]{11})", u or "")
    return m.group(1) if m else None


def topic_of(text, hint=None):
    if hint:
        return hint
    return "faith" if FAITH.search(text or "") else "ai" if AIBIZ.search(text or "") else "self"


def day(ts=None, ymd=None):
    if ymd and re.fullmatch(r"\d{8}", str(ymd)):
        return f"{ymd[:4]}-{ymd[4:6]}-{ymd[6:]}"
    if ts:
        return datetime.datetime.fromtimestamp(int(ts), datetime.timezone.utc).strftime("%Y-%m-%d")
    return None


# ---------------- verifying a link (the platform's own numbers, never Gemini's) ----------------
def from_ytdlp(info, platform, source, hint=None):
    if not info or info.get("view_count") is None:
        return None
    if platform == "tiktok":
        url, vid = tiktok_url(info.get("webpage_url") or "")
        if not url:
            handle = info.get("uploader") or info.get("channel")
            vid = str(info.get("id") or "")
            url = f"https://www.tiktok.com/@{handle}/video/{vid}" if handle and vid.isdigit() else None
        if not url:
            return None
        handle = url.split("/@")[1].split("/")[0]
        creator, curl = "@" + handle, f"https://www.tiktok.com/@{handle}"
    else:
        vid = info.get("id")
        url = f"https://www.youtube.com/shorts/{vid}"
        creator, curl = info.get("channel") or info.get("uploader") or "", info.get("channel_url") or info.get("uploader_url") or ""
    title = (info.get("title") or info.get("description") or "").strip()
    return {"platform": platform, "id": str(vid), "url": url, "creator": creator, "creatorUrl": curl,
            "title": title[:160], "views": int(info["view_count"]), "likes": info.get("like_count"),
            "comments": info.get("comment_count"), "shares": info.get("repost_count"),
            "followers": info.get("channel_follower_count"), "seconds": info.get("duration"),
            "posted": day(info.get("timestamp"), info.get("upload_date")), "outlier": None,
            "source": source, "topic": topic_of(title, hint), "viewsCheckedAt": ISO, "status": "todo", "tries": 0}


def verify(url, source, hint=None):
    """Open the link and read its real stats. Returns a candidate, or None if the link doesn't exist / can't be read."""
    if re.search(r"vm\.tiktok\.com|tiktok\.com/t/", url or ""):
        url = resolve(url)
    tt, _ = tiktok_url(url)
    if tt:
        return from_ytdlp(ytdlp_json(tt), "tiktok", source, hint)
    yid = youtube_id(url)
    if yid:
        if os.environ.get("YT_API_KEY"):
            try:
                got = yt_api_videos([yid], source, hint)
                if got:
                    return got[0]
            except Exception as e:
                say(f"YouTube API couldn't read {yid}: {e}")
        return from_ytdlp(ytdlp_json(f"https://www.youtube.com/watch?v={yid}"), "youtube", source, hint)
    return None


# ---------------- finding candidates ----------------
YT = "https://www.googleapis.com/youtube/v3/"


def iso_secs(d):
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    return (int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)) if m else 0


def yt_api_videos(ids, source, hint=None):
    key = os.environ["YT_API_KEY"]
    q = urllib.parse.urlencode({"part": "snippet,statistics,contentDetails", "id": ",".join(ids[:50]), "key": key})
    vids = http_json(YT + "videos?" + q).get("items", [])
    chans = {}
    cids = list({v["snippet"]["channelId"] for v in vids})[:50]
    if cids:
        cq = urllib.parse.urlencode({"part": "statistics", "id": ",".join(cids), "key": key})
        chans = {c["id"]: c.get("statistics", {}) for c in http_json(YT + "channels?" + cq).get("items", [])}
    out = []
    for v in vids:
        st, sn = v.get("statistics", {}), v["snippet"]
        if "viewCount" not in st:
            continue
        views = int(st["viewCount"])
        cs = chans.get(sn["channelId"], {})
        vc, tv = int(cs.get("videoCount", 0) or 0), int(cs.get("viewCount", 0) or 0)
        out.append({"platform": "youtube", "id": v["id"], "url": f"https://www.youtube.com/shorts/{v['id']}",
                    "creator": sn.get("channelTitle", ""), "creatorUrl": f"https://www.youtube.com/channel/{sn['channelId']}",
                    "title": sn.get("title", "")[:160], "views": views, "likes": int(st["likeCount"]) if "likeCount" in st else None,
                    "comments": int(st["commentCount"]) if "commentCount" in st else None, "shares": None,
                    "followers": int(cs["subscriberCount"]) if cs.get("subscriberCount") else None,
                    "seconds": iso_secs(v.get("contentDetails", {}).get("duration")), "posted": sn.get("publishedAt", "")[:10],
                    "outlier": round(views / (tv / vc), 1) if vc and tv else None, "source": source,
                    "topic": topic_of(sn.get("title", ""), hint), "viewsCheckedAt": ISO, "status": "todo", "tries": 0})
    return out


def collector_candidates():
    """Niche Shorts the hourly GitHub collector saved with real YouTube API numbers (data/tiktok/refs_candidates.json)."""
    d = rjson(os.path.join(ROOT, "data", "tiktok", "refs_candidates.json"), {})
    if not d.get("videos"):
        return []
    try:
        age = (NOW - datetime.datetime.strptime(d["updatedAt"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)).total_seconds() / 3600
    except Exception:
        age = 999
    if age > 72:
        say(f"collector list is {age:.0f}h old, not using it")
        return []
    out = []
    for v in d["videos"]:
        out.append({"platform": "youtube", "id": v["id"], "url": f"https://www.youtube.com/shorts/{v['id']}", "creator": v.get("channel", ""),
                    "creatorUrl": f"https://www.youtube.com/channel/{v['channelId']}" if v.get("channelId") else "",
                    "title": (v.get("title") or "")[:160], "views": int(v["views"]), "likes": v.get("likes"), "comments": v.get("comments"),
                    "shares": None, "followers": v.get("subscribers"), "seconds": v.get("duration"), "posted": (v.get("published") or "")[:10],
                    "outlier": v.get("outlier"), "source": "YouTube Shorts search", "topic": topic_of(v.get("title", ""), query_topic(v.get("query") or "")),
                    "viewsCheckedAt": d["updatedAt"], "status": "todo", "tries": 0})
    say(f"using {len(out)} Shorts from the GitHub collector (checked {age:.0f}h ago)")
    return out


def english(t):
    """Omar's audience is English: skip titles that are mostly non-Latin script (saves a Gemini call per video)."""
    letters = [ch for ch in t or "" if ch.isalpha()]
    if letters and sum(ch.isascii() for ch in letters) / len(letters) < 0.8:
        return False
    return len(HINGLISH.findall(t or "")) < 2   # Hindi/Urdu written in English letters

HINGLISH = re.compile(r"\b(hai|hain|nahi|nahin|mein|kya|aur|tha|thi|ek|ki|ka|ke|ko|se|ne|bhi|kaise|kyun|wala|wali|dil|zindagi|kismat|bana|di)\b", re.I)


def query_topic(q):
    return "faith" if FAITH.search(q) else "ai" if q in CFG.get("ai_queries", []) else "self"


def youtube_candidates():
    """YouTube Shorts in the niche (same short-form audience; lots of TikTokers cross-post). 0 Gemini calls."""
    out = []
    after = (NOW - datetime.timedelta(days=int(CFG.get("max_age_days", 45)))).strftime("%Y-%m-%dT%H:%M:%SZ")
    if os.environ.get("YT_API_KEY"):
        for q in CFG["youtube_queries"]:
            try:
                p = urllib.parse.urlencode({"part": "snippet", "q": q, "type": "video", "order": "viewCount", "publishedAfter": after,
                                            "videoDuration": "short", "maxResults": 10, "relevanceLanguage": "en", "key": os.environ["YT_API_KEY"]})
                ids = [i["id"]["videoId"] for i in http_json(YT + "search?" + p).get("items", []) if i.get("id", {}).get("videoId")]
                out += yt_api_videos(ids, "YouTube Shorts search", query_topic(q)) if ids else []
            except Exception as e:
                say(f"YouTube API search '{q}' failed: {e}")
        if out:
            return out
        say("Server YouTube key gave nothing, using the GitHub collector's list instead")
    out = collector_candidates()
    if out:
        return out
    say("No collector list either, trying yt-dlp search (YouTube often blocks this from the server)")
    # No key (or API failed): YouTube's own search page, sorted by view count, uploaded this month, under 4 minutes
    # (sp=CAMSBAgEGAE). The search list has no view counts, so the top few get opened one by one for the real numbers.
    for q in CFG["youtube_queries"]:
        url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q) + "&sp=CAMSBAgEGAE%3D"
        info = ytdlp_json(url, ["--flat-playlist", "--playlist-end", "10"], timeout=90) or {}
        ents = [e for e in info.get("entries") or [] if e.get("id") and 0 < (e.get("duration") or 999) <= CFG.get("max_seconds", 180)]
        for e in ents[:4]:
            c = verify(f"https://www.youtube.com/watch?v={e['id']}", "YouTube Shorts search", query_topic(q))
            if c:
                out.append(c)
    return out


def tiktok_candidates():
    """ONE Gemini web-search call for TikTok video links in the niche. Gemini only gives links; every link is then opened
    and its numbers read from TikTok itself. Free-tier search is limited, so a failure here just means no TikTok finds today."""
    prompt = f"""Today is {TODAY}. Use Google Search to find individual TikTok VIDEOS (not profiles, not hashtag pages, not articles) that went viral in the last 60 days in this niche: {CFG['tiktok_search_topics']}.
Prefer one person talking to the camera. Skip anything about jobs, resumes, LinkedIn or interviews.
List up to 12, one per line: the exact video URL as it appears in the search results (https://www.tiktok.com/@username/video/NUMBER) | creator | 5-word description.
Only list URLs you actually saw in the results. Do not write view counts or any other numbers; those get checked separately."""
    try:
        text, sources = G.generate(prompt, search=True, temperature=0.2, retries=1)
    except Exception as e:
        say(f"Gemini TikTok search failed (free-tier search quota is small): {str(e)[:200]}")
        return [], 1
    urls = set()
    for u in re.findall(r"https?://[^\s|)\]>\"'<,]+", text):
        tt, _ = tiktok_url(u)
        if tt or "vm.tiktok.com" in u or "tiktok.com/t/" in u:
            urls.add(tt or u)
    for _, u in sources[:20]:            # grounding sources are redirect links: open them to see where they really go
        tt, _ = tiktok_url(resolve(u))
        if tt:
            urls.add(tt)
    say(f"Gemini search suggested {len(urls)} TikTok links; opening each one")
    out = [c for c in (verify(u, "Gemini web search (link checked on TikTok)") for u in list(urls)[:15]) if c]
    say(f"{len(out)} TikTok links are real and have readable view counts")
    return out, 1


def inbox_candidates(state, have):
    out = []
    for r in state.get("refInbox") or []:
        if r.get("status") == "done" or not r.get("url") or r["url"] in have:
            continue
        c = verify(r["url"], "your inbox")
        if c:
            c["inbox"] = r["url"]
            out.append(c)
        else:
            out.append({"inbox": r["url"], "url": r["url"], "status": "failed", "error": "link couldn't be opened or has no view count", "tries": 9})
    return out


# ---------------- picking ----------------
def key_of(c):
    return f"{c.get('platform')}_{c.get('id')}"


def score(c):
    s = math.log10(max(c.get("views") or 1, 1)) + 0.6 * math.log10(max(min(c.get("outlier") or 1, 60), 1))
    return s + (10 if c.get("source") == "your inbox" else 0) + (0.4 if c.get("platform") == "tiktok" else 0)


def pick(cands):
    seen = rjson(SEEN, {})
    cutoff = (TODAY - datetime.timedelta(days=int(CFG.get("repeat_after_days", 30)))).isoformat()
    oldest = (TODAY - datetime.timedelta(days=int(CFG.get("max_age_days", 45)) * 2)).isoformat()
    ok, by_key = [], {}
    for c in cands:
        if c.get("status") == "failed":
            ok.append(c); continue
        k = key_of(c)
        if k in by_key:
            continue
        inbox = c.get("source") == "your inbox"
        if not inbox:
            if BLOCK.search(c.get("title", "") + " " + c.get("creator", "")) or not english(c.get("title", "")):
                continue
            if seen.get(k, "") >= cutoff:                     # shown in the last 30 days: skip
                continue
            if (c.get("seconds") or 0) > CFG.get("max_seconds", 180):
                continue
            if c.get("posted") and c["posted"] < oldest:
                continue
        by_key[k] = c
        ok.append(c)
    live = sorted([c for c in ok if c.get("status") != "failed"], key=score, reverse=True)
    for floor in (CFG["min_views"], CFG["fallback_min_views"]):
        pool = [c for c in live if c.get("source") == "your inbox" or c["views"] >= floor]
        if len(pool) >= PER_DAY:
            break
    queue, creators, n = [], set(), {"faith": 0, "ai": 0}
    for c in pool:                                            # mix: max 1 per creator, max 2 faith, max 1 AI/business
        if c.get("source") != "your inbox":
            if c["creator"].lower() in creators:
                continue
            if c["topic"] == "faith" and n["faith"] >= 2 or c["topic"] == "ai" and n["ai"] >= 1:
                continue
        creators.add(c["creator"].lower())
        n[c["topic"]] = n.get(c["topic"], 0) + 1
        queue.append(c)
        if len(queue) >= PER_DAY * 2:                         # spares in case some can't be watched
            break
    return queue + [c for c in ok if c.get("status") == "failed"]


def discover(state):
    say("discovering today's candidates")
    calls = 0
    cands = inbox_candidates(state, set())
    try:
        cands += youtube_candidates()
    except Exception as e:
        say(f"YouTube discovery failed: {e}")
    tt, calls = tiktok_candidates()
    cands += tt
    queue = pick(cands)
    C = {"date": str(TODAY), "createdAt": ISO, "stage": "picked", "geminiCalls": calls,
         "found": {"youtube": sum(c.get("platform") == "youtube" for c in cands), "tiktok": len(tt),
                   "inbox": sum(c.get("source") == "your inbox" for c in cands)},
         "queue": queue, "chunks": []}
    say(f"found {len(cands)} real videos, queued {sum(c.get('status') == 'todo' for c in queue)}")
    return C


# ---------------- the breakdown (one Gemini call per video, Gemini watches it) ----------------
SYSTEM = """You are the Reference Scout on Omar Jaradat's TikTok team. Omar is a university student in Mississauga who makes sit-down talking-to-camera TikToks: self-improvement and discipline for young guys, living life the Islamic way, sometimes AI/business. He talks as a regular guy still figuring it out, never a guru, never rich.
You are given a REAL video that went viral. Describe only what is actually in it (picture and sound). If something isn't there, say so. Never invent numbers, quotes, studies, stories, hadith or names. If Omar's version needs his own story, write [fill in: ...]. Any hadith/ayah needs a real reference plus [verify source].
Never write job-search, LinkedIn, resume, cover-letter, interview or LinkedAI content."""


def prompt_for(c, fmt):
    stats = f"{c['views']:,} views" + (f", {c['outlier']}x the creator's normal views" if c.get("outlier") else "")
    return f"""This is a real {c['platform']} video that went viral: "{c['title']}" by {c['creator']} ({stats}).
Watch the WHOLE video, picture and sound.

PART 1, the breakdown (plain words, talking to Omar, 1-3 sentences each):
- fitsNiche: true only if it's about self-improvement / discipline / mindset for young guys, living life the Islamic way, or AI/business. false for jobs, resumes, LinkedIn, interviews, anything mocking or arguing against Islam or any religion, or anything else.
- hook: what happens in the first 2 seconds: the exact first words said (quote them), what's on screen, and why a scroller stops.
- pacing: how fast it moves: cuts per ~10 seconds, how fast they talk, where the pauses or zooms are.
- onScreenText: the text shown and when (quote it). Say "none" if there isn't any.
- structure: the beats in order with rough seconds (e.g. 0-2s hook, 2-8s problem, ...).
- framing: camera distance and angle, sitting/standing/walking, eye contact, lighting, background, any B-roll.
- emotion: the feeling it builds and how (voice, face, music).
- payoff: what the viewer gets at the end and whether it pays off the hook.
- watchedToEnd: why people stayed to the end (open loop, promise, re-hook), naming the moment.
- shared: why people shared, saved or commented.
- stealThis: 2-3 concrete moves Omar can copy in his own sit-down video.

PART 2, yourVersion: a NEW script for Omar with the SAME structure and beat timing as this video, but in his own words and his own angle on the topic. Don't copy their lines. He films sitting down, talking to the camera, one take. Follow his format exactly:
{fmt}

Return JSON only:
{{"fitsNiche":true,"topic":"self|faith|ai","language":"en",
 "breakdown":{{"hook":"","pacing":"","onScreenText":"","structure":"","framing":"","emotion":"","payoff":"","watchedToEnd":"","shared":"","stealThis":["",""]}},
 "yourVersion":{{"title":"","hookFamily":"","length":30,"onScreen":"","scenes":[{{"label":"Hook","time":"0-2s","line":"","delivery":""}}],
   "hooksToTest":["line (family)","line (family)","line (family)"],"captionLine":"one line, no hashtags","tags":["#tag1","#tag2"],"whyThisOne":"one sentence"}}}}
yourVersion.scenes must have 4-7 scenes, mirroring the reference's beats."""


def video_part(c, tmpdir):
    if c["platform"] == "youtube":
        return {"file_data": {"file_uri": f"https://www.youtube.com/watch?v={c['id']}"}}, None
    out = os.path.join(tmpdir, f"{c['id']}.%(ext)s")
    r = subprocess.run(ytdlp_cmd() + ["-q", "--no-warnings", "--no-playlist", "-f", "mp4/best", "--max-filesize", "60M", "-o", out, c["url"]],
                       capture_output=True, text=True, timeout=300)
    files = [os.path.join(tmpdir, f) for f in os.listdir(tmpdir) if f.startswith(c["id"])]
    if r.returncode != 0 or not files:
        raise RuntimeError("couldn't download the TikTok for Gemini to watch: " + r.stderr.strip()[-200:])
    part = G.upload_file(files[0], "video/mp4")
    return part, part["file_data"]["file_uri"]


def breakdown(c, fmt):
    with tempfile.TemporaryDirectory() as tmp:
        part, remote = video_part(c, tmp)
        try:
            text, _ = G.generate([part, {"text": prompt_for(c, fmt)}], SYSTEM, json_out=True, temperature=0.6,
                                 gen_extra={"mediaResolution": "MEDIA_RESOLUTION_LOW"})   # ~100 tokens/sec of video
        finally:
            if remote:
                try:
                    G._req("DELETE", "files/" + remote.rstrip("/").split("/")[-1])
                except Exception:
                    pass
    b = G.parse_json(text)
    v = b.get("yourVersion") or {}
    v["scenes"] = [s for s in v.get("scenes") or [] if isinstance(s, dict) and s.get("line")]
    if b.get("fitsNiche") is False or BLOCK.search(json.dumps(v)) or (b.get("language") or "en")[:2] != "en":
        return {"fit": False, "why": "not in Omar's niche (or job/resume content, or not English)", "at": ISO}
    if not 4 <= len(v["scenes"]) <= 7:
        raise ValueError(f"your version had {len(v['scenes'])} scenes")
    if not (b.get("breakdown") or {}).get("hook"):
        raise ValueError("breakdown missing the hook")
    return {"fit": True, "at": ISO, "topic": b.get("topic"), "breakdown": b["breakdown"], "yourVersion": v}


def cache_path(c):
    return os.path.join(CACHE, key_of(c) + ".json")


def cached(c):
    b = rjson(cache_path(c))
    if b and b.get("at", "") >= (NOW - datetime.timedelta(days=int(CFG.get("repeat_after_days", 30)))).strftime("%Y-%m-%d"):
        return b
    return None


def chunk():
    os.makedirs(DAYDIR, exist_ok=True)
    state = rjson(STATE, {})
    C = rjson(CAND)
    calls, did = 0, []
    if not C or C.get("stage") != "picked":
        C = discover(state)
        calls = C["geminiCalls"]          # already counted in C
        did.append(f"discovery ({C['found']})")
        wjson(CAND, C)
    else:   # links Omar pasted after this morning's discovery go to the front
        have = {c.get("inbox") for c in C["queue"]}
        new = inbox_candidates(state, have)
        if new:
            C["queue"] = new + C["queue"]
            did.append(f"{len(new)} new inbox link(s)")
    fmt = open(FORMAT, encoding="utf-8").read()
    done = sum(c.get("status") == "done" for c in C["queue"])
    for c in C["queue"]:
        if done >= PER_DAY or calls >= MAX_CALLS:
            break
        if c.get("status") != "todo":
            continue
        b = cached(c)
        if not b:
            if calls:
                time.sleep(20)                                  # stay far below the per-minute limit
            calls += 1
            try:
                say(f"Gemini is watching {c['url']}")
                b = breakdown(c, fmt)
                wjson(cache_path(c), b)
            except Exception as e:
                c["tries"] = c.get("tries", 0) + 1
                c["error"] = str(e)[:200]
                if c["tries"] >= 2:
                    c["status"] = "failed"
                say(f"breakdown failed ({c['tries']}/2): {str(e)[:200]}")
                wjson(CAND, C)
                continue
        c["status"] = "done" if b.get("fit") else "skipped"
        done += c["status"] == "done"
        did.append(("broke down " if b.get("fit") else "skipped (off-niche) ") + c["url"])
        wjson(CAND, C)
    disc = C["geminiCalls"] if did and did[0].startswith("discovery") else 0
    C["geminiCalls"] = (disc or C.get("geminiCalls", 0)) + calls - disc
    C["chunks"].append({"at": ISO, "calls": calls, "did": did or ["nothing left to do"]})
    wjson(CAND, C)
    say(f"chunk done: {calls} Gemini call(s); {done}/{PER_DAY} videos broken down; " + ("; ".join(did) or "nothing left to do"))


# ---------------- assembling for the site (9:41 AM, no Gemini) ----------------
TAGS = "#fyppppppppppppppppppppppp #viral #fyp"


def still_there(c):
    """Cheap re-check that the link still opens (oEmbed, no key, no Gemini). None = couldn't check (network), keep it."""
    api = "https://www.tiktok.com/oembed?url=" if c["platform"] == "tiktok" else "https://www.youtube.com/oembed?format=json&url="
    try:
        return bool(http_json(api + urllib.parse.quote(c["url"], safe=""), timeout=15))
    except urllib.error.HTTPError as e:
        return False if e.code in (400, 401, 403, 404) else None
    except Exception:
        return None


def formatted(letter, v, caption):
    out = [f"**VERSION {letter} - {v.get('hookFamily', '')} (~{v.get('length', 30)}s)**",
           f"- **Why this one:** {v.get('whyThisOne', '')}",
           f"- **On-screen text (first 3-5s):** {v.get('onScreen', '')}", ""]
    for n, s in enumerate(v["scenes"], 1):
        out += [f"**Scene {n} - {s.get('label', '')} ({s.get('time', '')})**", f"> {s['line']}", "", f"*Delivery:* {s.get('delivery', '')}", "", "[pause]", ""]
    out += [f"**Last line:** \"{v['scenes'][-1]['line']}\"", "", "- **Hooks to test:**"]
    out += [f"  - {h}" for h in (v.get("hooksToTest") or [])[:3]]
    out += [f"- **Caption:** {caption}"]
    return "\n".join(out)


def assemble(state=None):
    """Returns (refs, inbox_results, note). refs = up to 5 verified, broken-down videos for today's Viral references tab."""
    C = rjson(CAND)
    if not C:
        return [], {}, f"No research saved for {TODAY} (the 3:52-8:52 AM chunks didn't run)."
    refs, inbox = [], {}
    for c in C["queue"]:
        if c.get("inbox"):
            inbox[c["inbox"]] = {"todo": "not reached today", "done": "broken down", "skipped": "not in your niche",
                                 "failed": c.get("error", "couldn't be checked")}.get(c.get("status"), c.get("status"))
        if c.get("status") != "done" or len(refs) >= PER_DAY:
            continue
        b = rjson(cache_path(c))
        if not b or not b.get("fit"):
            continue
        ok = still_there(c)
        if ok is False:
            say(f"dropped {c['url']}: the link doesn't open any more")
            continue
        v = dict(b["yourVersion"])
        tags = [t if t.startswith("#") else "#" + t for t in (v.get("tags") or []) if t][:2]
        line = re.sub(r"#\S+", "", v.get("captionLine", "")).strip()
        caption = f"{line} {TAGS} {' '.join(tags)}".strip()
        v.update(caption=caption, script="\n[pause]\n".join(s["line"] for s in v["scenes"]),
                 formatted=formatted("ABCDE"[len(refs)], v, caption))
        refs.append({k: c.get(k) for k in ("platform", "id", "url", "creator", "creatorUrl", "title", "views", "likes", "comments",
                                           "shares", "followers", "seconds", "posted", "outlier", "source", "viewsCheckedAt")}
                    | {"key": key_of(c), "linkCheckedAt": ISO if ok else c.get("viewsCheckedAt"), "topic": b.get("topic") or c.get("topic"),
                       "breakdown": b["breakdown"], "yourVersion": v})
    seen = rjson(SEEN, {})
    for r in refs:
        seen[r["key"]] = str(TODAY)
    cutoff = (TODAY - datetime.timedelta(days=90)).isoformat()
    wjson(SEEN, {k: d for k, d in seen.items() if d >= cutoff})
    note = f"{len(refs)} verified videos · {C.get('geminiCalls', 0)} Gemini calls over {len(C.get('chunks', []))} small runs"
    if len(refs) < 3:
        note += " · fewer than 3 today: not enough videos could be checked and watched (see the server log)"
    return refs, inbox, note


def status():
    C = rjson(CAND)
    if not C:
        print(f"Nothing saved for {TODAY} yet in {DAYDIR}")
        return
    print(f"{TODAY}: found {C['found']}, Gemini calls so far: {C.get('geminiCalls')}")
    for c in C["queue"]:
        print(f"  [{c.get('status'):7}] {c.get('views') or '-':>10} views  {c.get('creator', '')[:24]:24}  {c.get('url')}  {c.get('error', '')}")
    for ch in C.get("chunks", []):
        print("  run", ch["at"], "-", ch["calls"], "call(s):", "; ".join(ch["did"])[:200])


if __name__ == "__main__":
    {"chunk": chunk, "status": status}[sys.argv[1] if len(sys.argv) > 1 else "chunk"]()
