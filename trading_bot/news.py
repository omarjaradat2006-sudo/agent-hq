"""The eyes: news feeds + X/Reddit (Agent Reach, Omar's SECONDARY accounts).

Every item is normalized to:
  {id, publisher, kind: "news"|"social", title, summary, url, time, symbols}
"""
import hashlib, json, re, shutil, subprocess, time
import xml.etree.ElementTree as ET_XML
from datetime import timedelta
from html import unescape
from . import config as C
from .util import http, HttpError, iso, now_utc, parse_time, log

PUBLISHER_ALIASES = {"reuters": "Reuters", "associated press": "AP", "ap news": "AP", "apnews": "AP",
                     "cnbc": "CNBC", "benzinga": "Benzinga", "bloomberg": "Bloomberg", "wsj": "WSJ",
                     "the wall street journal": "WSJ", "financial times": "FT", "marketwatch": "MarketWatch",
                     "yahoo finance": "Yahoo Finance", "barron's": "Barron's", "cnn": "CNN", "bbc": "BBC",
                     "al jazeera": "Al Jazeera", "the associated press": "AP"}


def norm_publisher(p):
    p = (p or "").strip()
    return PUBLISHER_ALIASES.get(p.lower(), p) or "Unknown"


def _id(*parts):
    return hashlib.sha1("|".join(str(p) for p in parts).encode()).hexdigest()[:16]


def _clean(s, n=400):
    s = unescape(re.sub(r"<[^>]+>", " ", s or ""))
    return re.sub(r"\s+", " ", s).strip()[:n]


def item(publisher, kind, title, summary, url, t, symbols=()):
    title = _clean(title, 300)
    return {"id": _id(publisher, title.lower()[:120]), "publisher": norm_publisher(publisher), "kind": kind,
            "title": title, "summary": _clean(summary), "url": url, "time": iso(parse_time(t) or now_utc()),
            "symbols": sorted({s.upper() for s in symbols if s})}


# ------------------------------------------------------------------ news feeds
def alpaca_news(alpaca, since):
    out = []
    for n in alpaca.news(start=iso(since), limit=50, max_pages=3):
        out.append(item(n.get("source") or "Benzinga", "news", n.get("headline"), n.get("summary"), n.get("url"),
                        n.get("created_at"), n.get("symbols") or []))
    return out


def parse_rss(xml_text, default_publisher):
    out = []
    try:
        root = ET_XML.fromstring(xml_text)
    except ET_XML.ParseError:
        return out
    for it in root.iter("item"):
        title = it.findtext("title") or ""
        src = it.find("source")
        pub = src.text if src is not None and src.text else default_publisher
        if default_publisher == "Google News":   # "Headline - Reuters"
            m = re.match(r"(.*)\s+-\s+([^-]+)$", title)
            if m:
                title, pub = m.group(1), (src.text if src is not None and src.text else m.group(2))
        out.append(item(pub, "news", title, it.findtext("description"), it.findtext("link"), it.findtext("pubDate")))
    return out


def rss_news(since):
    out = []
    feeds = [(name, url) for name, url in C.CNBC_FEEDS.items()]
    feeds += [("Google News", "https://news.google.com/rss/search?q=" + q.replace(" ", "+") + "&hl=en-US&gl=US&ceid=US:en")
              for q in C.GOOGLE_NEWS_QUERIES]
    for name, url in feeds:
        try:
            xml = http("GET", url, timeout=20, retries=1)
            if isinstance(xml, str):
                pub = "CNBC" if name.startswith("CNBC") else name
                out.extend(i for i in parse_rss(xml, pub) if parse_time(i["time"]) >= since)
        except HttpError as e:
            log(f"{name} feed skipped: {e}", "News Scout")
    return out


# ------------------------------------------------------------------ X + Reddit (Agent Reach)
def agent_reach_available():
    return shutil.which("agent-reach") is not None


def _reach(args, timeout=90):
    """Run `agent-reach <args>` and return its items (it prints one JSON object)."""
    exe = shutil.which("agent-reach")
    try:
        p = subprocess.run([exe, *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, f"agent-reach {args[0]} {args[1]}: {e}"
    try:
        payload = json.loads((p.stdout or "").strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        return None, f"agent-reach {' '.join(args[:2])}: no JSON ({(p.stderr or '')[:120]})"
    if not payload.get("ok"):
        err = payload.get("error") or {}
        return None, f"agent-reach {' '.join(args[:2])}: {err.get('code')} {err.get('hint') or err.get('message')}"
    return _find_items(payload.get("result")), None


def _find_items(obj):
    if isinstance(obj, list) and obj and all(isinstance(x, dict) for x in obj) and any(("text" in x or "title" in x) for x in obj):
        return obj
    if isinstance(obj, dict):
        for k in ("items", "data", "result", "results"):
            if k in obj:
                found = _find_items(obj[k])
                if found is not None:
                    return found
        for v in obj.values():
            found = _find_items(v)
            if found:
                return found
    return [] if isinstance(obj, (list, dict)) else None


def social_news(since, state):
    """X accounts + subreddits through Agent Reach. Spaced out to stay polite (>=10s per platform)."""
    if not agent_reach_available():
        return []
    out, problems = [], []
    for user in C.X_ACCOUNTS:
        items, err = _reach(["twitter", "tweets", user, "--limit", "5"])
        if err:
            problems.append(err)
            if "NEED_LOGIN" in err or "NEED_SETUP" in err:
                break
        for x in items or []:
            t = parse_time(x.get("published_at"))
            if t and t < since:
                continue
            txt = x.get("text") or x.get("title") or ""
            out.append(item("X", "social", f"@{user}: {txt[:260]}", txt, x.get("url"), t or now_utc()))
            out[-1]["account"] = user
        time.sleep(10)
    for sub in C.SUBREDDITS:
        items, err = _reach(["reddit", "subreddit", sub, "--limit", "10"])
        if err:
            problems.append(err)
            if "NEED_LOGIN" in err or "NEED_SETUP" in err:
                break
        for x in items or []:
            t = parse_time(x.get("published_at"))
            if t and t < since:
                continue
            out.append(item("Reddit", "social", f"r/{sub}: {x.get('title') or ''}", x.get("text"), x.get("url"), t or now_utc()))
        time.sleep(10)
    state["socialStatus"] = {"at": iso(), "items": len(out), "problems": problems[:5]}
    if problems:
        log(f"X/Reddit: {problems[0]}", "News Scout")
    return out


# ------------------------------------------------------------------ collect
def collect(alpaca, state, include_social):
    """New, unseen items since the last cycle (max 3h back)."""
    last = parse_time(state.get("newsCursor")) or (now_utc() - timedelta(hours=2))
    since = max(last - timedelta(minutes=10), now_utc() - timedelta(hours=3))
    items = []
    try:
        items += alpaca_news(alpaca, since)
    except HttpError as e:
        log(f"Alpaca news skipped: {e}", "News Scout")
    items += rss_news(since)
    if include_social:
        items += social_news(since, state)
    seen = set(state.get("seenNews") or [])
    fresh, ids = [], set()
    for i in items:
        if i["id"] in seen or i["id"] in ids or not i["title"]:
            continue
        ids.add(i["id"])
        fresh.append(i)
    state["seenNews"] = (list(ids) + list(seen))[:4000]
    state["newsCursor"] = iso()
    return sorted(fresh, key=lambda i: i["time"], reverse=True)
