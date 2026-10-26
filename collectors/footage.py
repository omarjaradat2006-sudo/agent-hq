#!/usr/bin/env python3
"""Fetch free stock footage for the YouTube lineup. Run by GitHub Actions.

The YouTube team writes a "footage" list into data/youtube/state.json:
  {"file": "AE-rain-window-01.mp4", "query": "rain on window night", "orientation": "landscape",
   "minSeconds": 10, "for": "L1", "status": "wanted"}
For each wanted item this script searches Pexels (and Pixabay as a fallback), downloads the best
HD match, attaches it to a GitHub Release (so big files never go in the repo), and writes back
url / page / credit / status. The batch skill then downloads from those URLs.

Secrets: PEXELS_API_KEY (required), PIXABAY_API_KEY (optional). GITHUB_TOKEN comes from Actions.
"""
import json, os, sys, subprocess, tempfile, datetime, urllib.request, urllib.parse, urllib.error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "data", "youtube", "state.json")
USED = os.path.join(ROOT, "data", "youtube", "footage_used.json")
REPO = os.environ.get("GITHUB_REPOSITORY", "omarjaradat2006-sudo/agent-hq")
NOW = datetime.datetime.now(datetime.timezone.utc)
ISO = NOW.strftime("%Y-%m-%dT%H:%M:%SZ")
TAG = "footage-" + NOW.strftime("%Y-%m-%d")
env = lambda k: (os.environ.get(k) or "").strip()


def get(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": "agent-hq/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode())


def pick_file(files, landscape):
    """Prefer a 1080p-class H.264 file in the right orientation; avoid 4K to keep sizes sane."""
    best, score = None, 1e9
    for f in files:
        w, h = f.get("width") or 0, f.get("height") or 0
        if not w or not h or (w > h) != landscape:
            continue
        long_side = max(w, h)
        s = abs(long_side - 1920) + (0 if (f.get("file_type") or "video/mp4") == "video/mp4" else 500)
        if long_side > 2600:
            s += 800
        if s < score:
            best, score = f, s
    return best


def pexels(item, used):
    key = env("PEXELS_API_KEY")
    if not key:
        return None
    landscape = item.get("orientation", "landscape") != "portrait"
    q = urllib.parse.urlencode({"query": item["query"], "orientation": "landscape" if landscape else "portrait",
                                "size": "medium", "per_page": 15})
    res = get("https://api.pexels.com/videos/search?" + q, {"Authorization": key})
    for v in res.get("videos", []):
        vid = "pexels:" + str(v["id"])
        if vid in used or (v.get("duration") or 0) < item.get("minSeconds", 8):
            continue
        f = pick_file(v.get("video_files", []), landscape)
        if not f:
            continue
        who = (v.get("user") or {}).get("name") or "a Pexels creator"
        return {"id": vid, "download": f["link"], "page": v.get("url"), "credit": f"Video by {who} on Pexels",
                "seconds": v.get("duration"), "width": f.get("width"), "height": f.get("height"), "preview": v.get("image")}
    return None


def pixabay(item, used):
    key = env("PIXABAY_API_KEY")
    if not key:
        return None
    landscape = item.get("orientation", "landscape") != "portrait"
    q = urllib.parse.urlencode({"key": key, "q": item["query"][:100], "per_page": 20, "safesearch": "true"})
    res = get("https://pixabay.com/api/videos/?" + q)
    for v in res.get("hits", []):
        vid = "pixabay:" + str(v["id"])
        if vid in used or (v.get("duration") or 0) < item.get("minSeconds", 8):
            continue
        vids = v.get("videos", {})
        cand = [dict(vids[k], k=k) for k in ("large", "medium") if vids.get(k, {}).get("url")]
        cand = [c for c in cand if (c.get("width", 0) > c.get("height", 0)) == landscape]
        if not cand:
            continue
        c = cand[0]
        return {"id": vid, "download": c["url"], "page": v.get("pageURL"), "credit": f"Video by {v.get('user','a Pixabay creator')} on Pixabay",
                "seconds": v.get("duration"), "width": c.get("width"), "height": c.get("height"), "preview": c.get("thumbnail")}
    return None


def gh(*args):
    return subprocess.run(["gh", *args], capture_output=True, text=True)


def ensure_release():
    if gh("release", "view", TAG, "-R", REPO).returncode != 0:
        r = gh("release", "create", TAG, "-R", REPO, "--title", f"Footage {TAG[9:]}",
               "--notes", "Free stock footage fetched for the YouTube lineup (Pexels/Pixabay licence). Used by the batch skills.")
        if r.returncode != 0:
            raise RuntimeError("could not create release: " + r.stderr[:200])


def main():
    if not os.path.exists(STATE):
        print("no youtube state"); return
    s = json.load(open(STATE))
    items = s.get("footage") or []
    wanted = [i for i in items if i.get("status", "wanted") in ("wanted", "error") and i.get("file") and i.get("query")]
    if not wanted:
        print("nothing to fetch"); return
    if not env("PEXELS_API_KEY") and not env("PIXABAY_API_KEY"):
        for i in wanted:
            i["status"] = "needs_key"
        s.setdefault("log", []).insert(0, {"t": ISO, "agent": "Footage Fetcher", "msg": "Waiting for a Pexels API key (add PEXELS_API_KEY in GitHub Secrets)."})
        json.dump(s, open(STATE, "w"), indent=1); print("no api key"); return
    used = set(json.load(open(USED))) if os.path.exists(USED) else set()
    ensure_release()
    got = 0
    for i in wanted[:12]:
        try:
            hit = pexels(i, used) or pixabay(i, used)
            if not hit:
                i["status"] = "not_found"; i["note"] = "No free clip matched. The team will try a different search."; continue
            with tempfile.TemporaryDirectory() as d:
                path = os.path.join(d, i["file"])
                req = urllib.request.Request(hit["download"], headers={"User-Agent": "agent-hq/1.0"})
                with urllib.request.urlopen(req, timeout=180) as r, open(path, "wb") as out:
                    while True:
                        b = r.read(1 << 20)
                        if not b: break
                        out.write(b)
                mb = os.path.getsize(path) / 1e6
                up = gh("release", "upload", TAG, path, "-R", REPO, "--clobber")
                if up.returncode != 0:
                    raise RuntimeError(up.stderr[:200])
            i.update(status="ready", url=f"https://github.com/{REPO}/releases/download/{TAG}/{urllib.parse.quote(i['file'])}",
                     page=hit["page"], credit=hit["credit"], seconds=hit["seconds"], size=f"{hit['width']}x{hit['height']}",
                     mb=round(mb, 1), preview=hit.get("preview"), fetchedAt=ISO, sourceId=hit["id"])
            used.add(hit["id"]); got += 1
        except Exception as e:
            i["status"] = "error"; i["note"] = str(e)[:200]
    s.setdefault("log", []).insert(0, {"t": ISO, "agent": "Footage Fetcher", "msg": f"Downloaded {got} free stock clip(s) for today's lineup."})
    s["log"] = s["log"][:100]
    json.dump(s, open(STATE, "w"), indent=1)
    json.dump(sorted(used), open(USED, "w"))
    print("fetched", got)


if __name__ == "__main__":
    main()
