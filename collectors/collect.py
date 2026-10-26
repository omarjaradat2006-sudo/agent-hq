#!/usr/bin/env python3
"""Agent HQ data collectors. Run hourly by GitHub Actions.

Writes data/<team>/metrics.json. Every source is optional: if its keys are
missing, that part is skipped and the site shows "waiting for access".
No third-party packages, standard library only.

Secrets (GitHub repo -> Settings -> Secrets and variables -> Actions):
  YT_API_KEY                       YouTube Data API key (public data, trending)
  YT_CLIENT_ID, YT_CLIENT_SECRET   Google OAuth client (your own analytics)
  YT_REFRESH_TOKEN_1, _2           one per YouTube channel you own
  TT_CLIENT_KEY, TT_CLIENT_SECRET  TikTok developer app
  TT_REFRESH_TOKEN                 from scripts/tiktok_connect.py
"""
import json, os, sys, time, datetime, urllib.request, urllib.parse, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NOW = datetime.datetime.now(datetime.timezone.utc)
ISO = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
CFG = json.load(open(os.path.join(ROOT, "collectors", "niches.json")))
env = lambda k: (os.environ.get(k) or "").strip()


def http(url, data=None, headers=None, method=None):
    body = None
    h = dict(headers or {})
    if data is not None:
        if h.get("Content-Type") == "application/json":
            body = json.dumps(data).encode()
        else:
            body = urllib.parse.urlencode(data).encode()
            h.setdefault("Content-Type", "application/x-www-form-urlencoded")
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        detail = e.read().decode()[:300]
        raise RuntimeError(f"HTTP {e.code} from {urllib.parse.urlparse(url).netloc}: {detail}")


def load_metrics(team):
    p = os.path.join(ROOT, "data", team, "metrics.json")
    try:
        return json.load(open(p))
    except Exception:
        return {}


def save_metrics(team, m):
    p = os.path.join(ROOT, "data", team, "metrics.json")
    m["log"] = (m.get("log") or [])[:40]
    json.dump(m, open(p, "w"), indent=1)


def log(m, msg, agent="Data Collector"):
    m.setdefault("log", []).insert(0, {"t": ISO, "agent": agent, "msg": msg})


def hours_since(iso):
    if not iso:
        return 1e9
    try:
        t = datetime.datetime.strptime(iso, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)
        return (NOW - t).total_seconds() / 3600
    except Exception:
        return 1e9


def age_label(published):
    try:
        t = datetime.datetime.strptime(published[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=datetime.timezone.utc)
        d = (NOW - t).days
        return "today" if d == 0 else f"{d}d old"
    except Exception:
        return None


# ---------------- YouTube public data ----------------
YT = "https://www.googleapis.com/youtube/v3/"


def yt_trending(queries, shorts_only=False):
    key = env("YT_API_KEY")
    after = (NOW - datetime.timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ids = []
    for q in queries:
        params = {"part": "snippet", "q": q, "type": "video", "order": "viewCount", "publishedAfter": after,
                  "maxResults": 8, "regionCode": CFG.get("region", "CA"), "relevanceLanguage": "en", "key": key}
        if shorts_only:
            params["videoDuration"] = "short"
        res = http(YT + "search?" + urllib.parse.urlencode(params))
        ids += [i["id"]["videoId"] for i in res.get("items", []) if i.get("id", {}).get("videoId")]
    ids = list(dict.fromkeys(ids))[:50]
    if not ids:
        return []
    vids = http(YT + "videos?" + urllib.parse.urlencode({"part": "snippet,statistics", "id": ",".join(ids), "key": key})).get("items", [])
    chan_ids = list({v["snippet"]["channelId"] for v in vids})[:50]
    chans = {c["id"]: c for c in http(YT + "channels?" + urllib.parse.urlencode({"part": "statistics", "id": ",".join(chan_ids), "key": key})).get("items", [])}
    out = []
    for v in vids:
        views = int(v.get("statistics", {}).get("viewCount", 0))
        cs = chans.get(v["snippet"]["channelId"], {}).get("statistics", {})
        vc, tv = int(cs.get("videoCount", 0) or 0), int(cs.get("viewCount", 0) or 0)
        avg = (tv / vc) if vc else 0
        mult = round(views / avg, 1) if avg else None
        out.append({"title": v["snippet"]["title"], "url": "https://www.youtube.com/watch?v=" + v["id"],
                    "channel": v["snippet"]["channelTitle"], "views": views,
                    "outlier": mult, "age": (f"{mult}x channel avg · " if mult else "") + (age_label(v["snippet"]["publishedAt"]) or "")})
    # rank by how unusual the video is for its channel, then raw views
    out.sort(key=lambda x: ((x["outlier"] or 0), x["views"]), reverse=True)
    return out[:15]


# ---------------- YouTube private analytics ----------------
def iso_secs(d):
    import re
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", d or "")
    return (int(m.group(1) or 0) * 3600 + int(m.group(2) or 0) * 60 + int(m.group(3) or 0)) if m else 0

def google_access_token(refresh):
    r = http("https://oauth2.googleapis.com/token", {"client_id": env("YT_CLIENT_ID"), "client_secret": env("YT_CLIENT_SECRET"),
                                                    "refresh_token": refresh, "grant_type": "refresh_token"})
    return r["access_token"]


def yt_own_channel(refresh):
    tok = google_access_token(refresh)
    H = {"Authorization": "Bearer " + tok}
    ch = http(YT + "channels?part=snippet,statistics,contentDetails&mine=true", headers=H)["items"][0]
    name = ch["snippet"]["title"]
    end = NOW.date().isoformat()
    start = (NOW.date() - datetime.timedelta(days=28)).isoformat()
    rep = http("https://youtubeanalytics.googleapis.com/v2/reports?" + urllib.parse.urlencode({
        "ids": "channel==MINE", "startDate": start, "endDate": end,
        "metrics": "views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost"}), headers=H)
    row = (rep.get("rows") or [[0, 0, 0, 0, 0]])[0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    pl = http(YT + "playlistItems?" + urllib.parse.urlencode({"part": "contentDetails", "playlistId": uploads, "maxResults": 50}), headers=H)
    recent_ids = [i["contentDetails"]["videoId"] for i in pl.get("items", [])]
    # Per-video analytics over 90 days, sorted by views: this is where the hits
    # (and their retention) live. YouTube analytics lag 2-3 days, and Omar posts
    # 17 videos a day, so the newest uploads alone never show what worked.
    per, top_ids = {}, []
    start90 = (NOW.date() - datetime.timedelta(days=90)).isoformat()
    try:
        vr = http("https://youtubeanalytics.googleapis.com/v2/reports?" + urllib.parse.urlencode({
            "ids": "channel==MINE", "startDate": start90, "endDate": end, "dimensions": "video", "sort": "-views", "maxResults": 200,
            "metrics": "views,averageViewDuration,averageViewPercentage,likes,shares,subscribersGained"}), headers=H)
        for r in vr.get("rows") or []:
            per[r[0]] = {"views90": int(r[1]), "avgViewSec": int(r[2]), "avgViewPct": round(float(r[3]), 1), "shares": int(r[5]), "subsGained": int(r[6])}
            top_ids.append(r[0])
    except Exception as e:
        print("per-video analytics skipped:", str(e)[:160])
    # top 40 by views + the 40 lowest that have analytics (to compare hits vs misses) + newest uploads
    analysed = top_ids[:40] + [v for v in top_ids[40:][-40:]]
    want = list(dict.fromkeys(analysed + recent_ids[:30]))
    vids = []
    for i in range(0, len(want), 50):
        chunk = want[i:i + 50]
        for v in http(YT + "videos?" + urllib.parse.urlencode({"part": "snippet,statistics,contentDetails", "id": ",".join(chunk)}), headers=H).get("items", []):
            s = v.get("statistics", {}); dur = v.get("contentDetails", {}).get("duration", "")
            pub = v["snippet"]["publishedAt"]
            age = (NOW - datetime.datetime.strptime(pub, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=datetime.timezone.utc)).days
            item = {"title": f"[{name}] " + v["snippet"]["title"], "channel": name, "url": "https://www.youtube.com/watch?v=" + v["id"], "id": v["id"],
                    "views": int(s.get("viewCount", 0)), "likes": int(s.get("likeCount", 0) or 0), "comments": int(s.get("commentCount", 0) or 0),
                    "published": pub, "ageDays": age, "duration": dur, "seconds": iso_secs(dur), "isShort": iso_secs(dur) <= 180}
            item.update(per.get(v["id"], {}))
            vids.append(item)
    vids.sort(key=lambda x: x["views"], reverse=True)
    subs = int(ch["statistics"].get("subscriberCount", 0))
    kpis = [
        {"label": f"{name} · subscribers", "value": subs, "delta": int(row[3]) - int(row[4]), "deltaLabel": "28d"},
        {"label": f"{name} · views (28d)", "value": int(row[0])},
        {"label": f"{name} · watch hours (28d)", "value": round(int(row[1]) / 60)},
        {"label": f"{name} · avg view (sec)", "value": int(row[2])},
    ]
    return name, kpis, vids


# ---------------- TikTok (Display API, your own account) ----------------
def tiktok_own():
    tok = http("https://open.tiktokapis.com/v2/oauth/token/", {"client_key": env("TT_CLIENT_KEY"), "client_secret": env("TT_CLIENT_SECRET"),
                                                             "grant_type": "refresh_token", "refresh_token": env("TT_REFRESH_TOKEN")})
    if "access_token" not in tok:
        raise RuntimeError("TikTok token refresh failed: " + json.dumps(tok)[:200])
    H = {"Authorization": "Bearer " + tok["access_token"]}
    u = http("https://open.tiktokapis.com/v2/user/info/?fields=display_name,follower_count,likes_count,video_count", headers=H)
    user = u.get("data", {}).get("user", {})
    fields = "id,title,video_description,create_time,share_url,view_count,like_count,comment_count,share_count,duration,cover_image_url"
    vl = http("https://open.tiktokapis.com/v2/video/list/?fields=" + fields, {"max_count": 20},
              headers={**H, "Content-Type": "application/json"}, method="POST")
    vids = []
    for v in vl.get("data", {}).get("videos", []):
        vids.append({"title": (v.get("title") or v.get("video_description") or "Untitled")[:120], "url": v.get("share_url"),
                     "views": v.get("view_count", 0), "likes": v.get("like_count", 0), "comments": v.get("comment_count", 0),
                     "shares": v.get("share_count", 0), "duration": v.get("duration"), "cover": v.get("cover_image_url"),
                     "description": (v.get("video_description") or "")[:500], "id": v.get("id"),
                     "published": datetime.datetime.fromtimestamp(v.get("create_time", 0), datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")})
    vids.sort(key=lambda x: x["published"], reverse=True)
    recent = vids[:10]
    avg = round(sum(v["views"] for v in recent) / len(recent)) if recent else 0
    best = max(recent, key=lambda v: v["views"]) if recent else None
    kpis = [{"label": "Followers", "value": user.get("follower_count", 0)},
            {"label": "Total likes", "value": user.get("likes_count", 0)},
            {"label": "Avg views (last 10)", "value": avg},
            {"label": "Videos posted", "value": user.get("video_count", 0)}]
    return kpis, vids, best, avg


def run_youtube():
    m = load_metrics("youtube")
    m.setdefault("kpis", []); m.setdefault("topVideos", []); m.setdefault("trending", [])
    did, problems = [], []
    if env("YT_API_KEY") and hours_since(m.get("trendingAt")) >= CFG.get("trending_every_hours", 6):
        try:
            m["trending"] = yt_trending(CFG["youtube"]["queries"])
            m["trendingAt"] = ISO
            top = m["trending"][0] if m["trending"] else None
            did.append(f"scanned {len(CFG['youtube']['queries'])} niches" + (f", top outlier: \"{top['title'][:60]}\" ({top['age']})" if top else ""))
        except Exception as e:
            problems.append("trending: " + str(e))
    refresh = [env("YT_REFRESH_TOKEN_1"), env("YT_REFRESH_TOKEN_2")]
    if env("YT_CLIENT_ID") and any(refresh):
        kpis, vids = [], []
        for r in refresh:
            if not r:
                continue
            try:
                name, k, v = yt_own_channel(r)
                kpis += k; vids += v
            except Exception as e:
                problems.append("analytics: " + str(e))
        if kpis:
            m["kpis"], m["topVideos"] = kpis, sorted(vids, key=lambda x: (x.get("channel", ""), -x["views"]))[:260]
            did.append(f"pulled your stats for {len(kpis)//4} channel(s)")
    finish(m, "youtube", did, problems, needs="Add YT_API_KEY (and your Google sign-in tokens) to start. See SETUP.md.")


def run_tiktok():
    m = load_metrics("tiktok")
    m.setdefault("kpis", []); m.setdefault("topVideos", []); m.setdefault("trending", [])
    did, problems = [], []
    if env("YT_API_KEY") and hours_since(m.get("trendingAt")) >= CFG.get("trending_every_hours", 6):
        try:
            m["trending"] = yt_trending(CFG["tiktok"]["queries"], shorts_only=True)
            m["trendingAt"] = ISO
            did.append("scanned short-form videos in your niche")
        except Exception as e:
            problems.append("niche shorts: " + str(e))
    if env("TT_CLIENT_KEY") and env("TT_REFRESH_TOKEN"):
        try:
            kpis, vids, best, avg = tiktok_own()
            prev = {k["label"]: k["value"] for k in m.get("kpis", [])}
            for k in kpis:
                if k["label"] in prev and isinstance(prev[k["label"]], (int, float)):
                    k["delta"] = k["value"] - prev[k["label"]]; k["deltaLabel"] = "since last check"
            m["kpis"], m["topVideos"] = kpis, vids[:20]
            did.append(f"pulled your TikTok stats (avg {avg:,} views on last 10" + (f", best: {best['views']:,}" if best else "") + ")")
        except Exception as e:
            problems.append("tiktok: " + str(e))
    finish(m, "tiktok", did, problems, needs="Connect your TikTok account and add YT_API_KEY to start. See SETUP.md.")


def finish(m, team, did, problems, needs):
    m["updatedAt"] = ISO
    m["source"] = "hourly collector"
    has_data = bool(m.get("kpis") or m.get("trending"))
    if problems:
        m["status"] = "error"; m["message"] = "; ".join(problems)[:300]
        log(m, "Hit a problem: " + m["message"])
    elif did:
        m["status"] = "ok"; m["message"] = "Collected: " + "; ".join(did)
        log(m, m["message"][0].upper() + m["message"][1:] + ".")
    elif not has_data:
        if m.get("status") == "needs_setup":
            print(team, "still waiting for keys; nothing to commit"); return
        m["status"] = "needs_setup"; m["message"] = needs
    else:
        m["status"] = "ok"; m["message"] = "Up to date. Trend scan runs every few hours."
    save_metrics(team, m)
    print(team, m["status"], m["message"])


if __name__ == "__main__":
    which = sys.argv[1:] or ["youtube", "tiktok"]
    for w in which:
        {"youtube": run_youtube, "tiktok": run_tiktok}[w]()
