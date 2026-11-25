"""Research Lab: a separate agent whose only job is to study how successful traders and investors actually work,
then PROVE which ideas hold up on real prices before any of them touch the bot.

For the set number of days (default 7) it loops, politely, on its own Gemini keys:
  1. READ:   YouTube videos (Gemini watches them directly from the link), books and trader methods (Google-grounded
             summaries), and research papers (arXiv), for a long list of stock, swing, day and crypto traders,
             famous investors, and academic findings.
  2. EXTRACT: every lesson, tagged with a theme (cut losses, trend, sizing, patience, news...), and when possible an
             exact rule the test engine can run (lab_engine.py).
  3. TEST:   every rule on ~3 years of daily prices of the halal stocks + coins, in three separate periods and the
             recent drop, plus small changes to its numbers (a real edge survives them).
  4. LOOK BACK: replays the bot's own losing trades with other stops / filters to show what went wrong.
  5. REPORT: progress on the Trading tab all week; at the end a full report, the common factors across everyone,
             the playbook of rules that passed, and a skill file.

Never trades. Never touches keys other than its own. Halal: long only, cash only.

    python -m trading_bot.lab run          (the service runs this)
    python -m trading_bot.lab status
    python -m trading_bot.lab report       (write the final report now, even before the time is up)
"""
import hashlib, json, os, re, sys, time, urllib.parse, urllib.request
from collections import Counter, defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo
from . import config as C
from . import lab_engine as E
from .util import load_env, read_json, write_json, iso, now_utc, parse_time, log, ROOT, DATA, LOCAL, UA

sys.path.insert(0, str(ROOT / "agents" / "gemini"))
import gemini  # noqa: E402

HOME = LOCAL / "lab"
STATE = HOME / "state.json"
OUT = DATA / "lab"
PT = ZoneInfo("America/Los_Angeles")        # Gemini's free daily quotas reset at midnight Pacific
PAUSE = 8                                    # seconds between Gemini calls (stays under per-minute limits)
VIDEO_MAX_S = 2400                           # watch at most the first 40 minutes of a video (keeps token use sane)

THEMES = ["cut_losses_fast", "let_winners_run", "trade_with_the_trend", "market_regime_filter", "position_sizing",
          "risk_per_trade", "buy_strength_new_highs", "buy_pullbacks_in_uptrends", "buy_dips_mean_reversion",
          "volume_confirmation", "earnings_and_fundamentals", "news_trading", "patience_wait_for_setup",
          "avoid_overtrading", "discipline_follow_rules", "psychology_emotions", "journaling_review_mistakes",
          "concentration_vs_diversification", "long_term_holding", "momentum", "volatility_contraction_bases",
          "crypto_cycles_halving", "crypto_onchain_sentiment", "macro_liquidity", "cash_is_a_position",
          "backtest_and_edge", "costs_and_fees", "other"]

# Who and what to study. Advice from people with very different styles, then the tests decide.
CURRICULUM = [
    # trend / momentum traders
    ("person", "Jesse Livermore", "stocks"), ("person", "William O'Neil CANSLIM", "stocks"),
    ("person", "Mark Minervini SEPA VCP", "stocks"), ("person", "Nicolas Darvas box method", "stocks"),
    ("person", "Kristjan Kullamagi Qullamaggie breakouts", "stocks"), ("person", "Dan Zanger chart patterns", "stocks"),
    ("person", "Paul Tudor Jones 200-day moving average rule", "stocks"), ("person", "Stanley Druckenmiller", "macro"),
    ("person", "Ed Seykota trend following", "stocks"), ("person", "Richard Dennis Turtle Traders rules", "stocks"),
    ("person", "Tom Basso position sizing", "stocks"), ("person", "Van Tharp position sizing R-multiples", "stocks"),
    ("person", "Larry Williams short-term trading", "stocks"), ("person", "Linda Raschke swing trading", "stocks"),
    ("person", "Larry Connors RSI-2 mean reversion", "stocks"), ("person", "Minervini Trend Template", "stocks"),
    # day traders
    ("person", "Ross Cameron Warrior Trading momentum day trading", "daytrading"),
    ("person", "Andrew Aziz day trading strategies", "daytrading"), ("person", "Brian Shannon VWAP moving averages", "daytrading"),
    ("person", "Oliver Kell cycle of price action", "stocks"),
    # investors
    ("person", "Warren Buffett investing principles", "investing"), ("person", "Peter Lynch One Up on Wall Street", "investing"),
    ("person", "Jim Simons Renaissance Technologies principles", "quant"), ("person", "Ray Dalio principles risk parity", "macro"),
    ("person", "George Soros reflexivity", "macro"), ("person", "Howard Marks market cycles", "investing"),
    ("person", "Cliff Asness AQR momentum and value", "quant"), ("person", "Meb Faber trend following moving average", "quant"),
    ("person", "Gary Antonacci dual momentum", "quant"),
    # crypto
    ("person", "Benjamin Cowen crypto risk metric cycles", "crypto"), ("person", "Raoul Pal crypto macro", "crypto"),
    ("person", "Willy Woo bitcoin on-chain analysis", "crypto"), ("person", "PlanB bitcoin stock to flow criticism", "crypto"),
    ("person", "Arthur Hayes crypto liquidity", "crypto"), ("person", "crypto trend following strategy bitcoin moving average", "crypto"),
    # academic topics
    ("topic", "time series momentum trend following", "paper"), ("topic", "cross-sectional momentum stocks", "paper"),
    ("topic", "stop-loss rules when do stop losses stop losses", "paper"), ("topic", "52-week high momentum", "paper"),
    ("topic", "post-earnings announcement drift", "paper"), ("topic", "short-term reversal stocks", "paper"),
    ("topic", "news sentiment stock returns speed of reaction", "paper"), ("topic", "volatility targeting momentum crashes", "paper"),
    ("topic", "retail day traders performance losses", "paper"), ("topic", "cryptocurrency momentum trend", "paper"),
    ("topic", "overnight returns intraday returns", "paper"), ("topic", "moving average trading rules profitability", "paper"),
]

RULE_SPEC = """When a lesson is an exact, testable trading rule, also give "rule" in this format (otherwise null):
{"name": short name, "universe": "stocks"|"crypto"|"both", "max_positions": 1-20,
 "regime": "none"|"spy_above_200"|"spy_above_50",
 "entry": [conditions, ALL must be true at the daily close],
 "rank": "momentum_126"|"momentum_63"|"momentum_252"|"rsi_low"|"volume_surge",
 "exit": {"stop_pct": n|null, "trail_pct": n|null, "atr_stop": multiple of 14-day ATR|null, "target_pct": n|null,
          "exit_below_sma": days|null, "max_days": n|null}}
Conditions (use only these, numbers are yours to fill):
 {"f":"close_above_sma","n":50} {"f":"close_below_sma","n":20} {"f":"sma_above_sma","a":50,"b":200}
 {"f":"return_above","days":126,"pct":0} {"f":"return_below","days":5,"pct":-5}
 {"f":"near_high","days":252,"within_pct":10} {"f":"breakout","days":20}
 {"f":"rsi_below","n":2,"value":10} {"f":"rsi_above","n":14,"value":60} {"f":"pullback_to_sma","n":20,"within_pct":2}
 {"f":"volume_surge","days":50,"mult":1.5} {"f":"gap_up","pct":3} {"f":"down_days","n":3}
 {"f":"volatility_contraction","short":10,"long":50,"ratio":0.6} {"f":"top_momentum","days":126,"top":10}
Daily prices only (no intraday, no fundamentals, no news). Long only: never shorting, leverage or options."""

EXTRACT_SYSTEM = f"""You are the research analyst of a halal, long-only trading lab. You study what successful traders,
investors and researchers teach, without hype. Pull out every concrete lesson. Separate what the person CLAIMS from what
is SHOWN with evidence. Keep the person's own nuance (when the rule applies, when it fails).
Reply with JSON only:
{{"person": who is teaching, "style": "day trading"|"swing"|"position/trend"|"investing"|"quant"|"crypto"|"academic",
  "summary": 2-3 plain sentences,
  "lessons": [{{"theme": one of {THEMES}, "lesson": one plain sentence, "evidence": "claim"|"example"|"track record"|"backtest"|"academic study",
               "rule": null or a rule}}],
  "mentions": [other traders, books or studies this source points to, max 5]}}
{RULE_SPEC}"""


# ---------------------------------------------------------------- Gemini with several keys, quota-aware
class OutOfQuota(Exception):
    pass


class Busy(Exception):
    pass


class Brain:
    """Spreads calls over LAB_GEMINI_KEYS (comma separated). Falls back to the shared key with a small daily cap so
    the agent teams and the trading bot never run dry. A key that hits its daily limit rests until midnight Pacific."""
    def __init__(self, st):
        own = [k.strip() for k in (os.environ.get("LAB_GEMINI_KEYS") or "").split(",") if k.strip()]
        shared = (os.environ.get("GEMINI_API_KEY") or "").strip()
        self.keys = [(k, int(os.environ.get("LAB_CAP_PER_KEY") or 250), 12) for k in own]
        if shared and shared not in own:
            self.keys.append((shared, int(os.environ.get("LAB_SHARED_CAP") or 40), 2))
        self.st = st.setdefault("keys", {})
        self.models = None

    def _day(self):
        return now_utc().astimezone(PT).date().isoformat()

    def _slot(self, k):
        h = hashlib.sha1(k.encode()).hexdigest()[:8]
        s = self.st.setdefault(h, {})
        if s.get("day") != self._day():
            s.clear(); s["day"] = self._day()
        return s

    def available(self, video=False):
        for k, cap, vcap in self.keys:
            s = self._slot(k)
            if s.get("calls", 0) < cap and not s.get("done") and (not video or (s.get("videos", 0) < vcap and not s.get("videoDone"))):
                yield k, s

    def _model_list(self, key):
        if self.models is None:
            gemini.KEY = key
            log("Checking which Gemini models the lab keys can use...", "Research Lab")
            names = [m["name"].split("/")[-1] for m in gemini._req("GET", "models?pageSize=200").get("models", [])
                     if "generateContent" in m.get("supportedGenerationMethods", []) and gemini.text_model_ok(m["name"].split("/")[-1])]
            ver = lambda n: float((re.search(r"gemini-(\d+(?:\.\d+)?)", n) or [0, 0])[1] or 0)
            flash = sorted([n for n in names if "flash" in n and "lite" not in n], key=ver, reverse=True)[:2]
            lite = sorted([n for n in names if "flash-lite" in n], key=ver, reverse=True)[:2]
            self.models = {"strong": flash + lite, "lite": lite + flash}
            log(f"Lab models: {', '.join(flash + lite)}", "Research Lab")
        return self.models

    def ask(self, parts, video=False, search=False, json_out=True, strong=False, temperature=0.3):
        import urllib.error
        body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": {"temperature": temperature}}
        if video:
            body["generationConfig"]["mediaResolution"] = "MEDIA_RESOLUTION_LOW"
        if search:
            body["tools"] = [{"google_search": {}}]
        elif json_out:
            body["generationConfig"]["responseMimeType"] = "application/json"
        for key, s in list(self.available(video)):
            gemini.KEY = key
            kh = hashlib.sha1(key.encode()).hexdigest()[:6]
            bad = s.setdefault("badModels", [])
            for name in self._model_list(key)["strong" if (strong or video or search) else "lite"]:
                if name in bad:
                    continue
                for attempt in range(2):
                    time.sleep(PAUSE)
                    try:
                        s["calls"] = s.get("calls", 0) + 1
                        r = gemini._req("POST", f"models/{name}:generateContent", body, timeout=300)
                        cand = (r.get("candidates") or [{}])[0]
                        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
                        if not text.strip():
                            raise RuntimeError("empty reply")
                        if video:
                            s["videos"] = s.get("videos", 0) + 1
                        meta = cand.get("groundingMetadata") or {}
                        srcs = [(c["web"].get("title", ""), c["web"].get("uri", "")) for c in meta.get("groundingChunks", []) if "web" in c]
                        return (gemini.parse_json(text) if json_out else text), srcs
                    except urllib.error.HTTPError as e:
                        full = e.read().decode(errors="ignore")
                        log(f"Gemini {e.code} on {name} (key #{kh}): {re.sub(r'\s+', ' ', full)[:140]}", "Research Lab")
                        if e.code == 429 and ("limit: 0" in full or "PerDay" in full):
                            bad.append(name)            # no free quota for this model on this key today: skip it
                            break
                        if e.code == 429:
                            time.sleep(30); break       # per-minute burst: rest briefly, then the next model
                        if e.code == 400 and video:
                            raise ValueError(f"video not readable: {full[:160]}")
                        if e.code in (403, 404):
                            bad.append(name); break
                        if e.code in (500, 503, 504) and attempt == 0:
                            time.sleep(15); continue
                        break
                    except (urllib.error.URLError, TimeoutError, RuntimeError, ValueError) as e:
                        if isinstance(e, ValueError) and "video" in str(e):
                            raise
                        log(f"Gemini error on {name} (key #{kh}): {str(e)[:120]}", "Research Lab")
                        break
            tier = self._model_list(key)["strong" if (strong or video or search) else "lite"]
            if all(m in bad for m in tier):              # every model on this key is out of quota today
                if video:
                    s["videoDone"] = True
                else:
                    s["done"] = True
        if not list(self.available(video)):
            raise OutOfQuota("every lab key is out of quota for today")
        raise Busy("Gemini busy right now")


# ---------------------------------------------------------------- finding sources
YT_ID = re.compile(r"(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/)([A-Za-z0-9_-]{11})")


def youtube_ids(text):
    return list(dict.fromkeys(YT_ID.findall(text or "")))


def _get_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def video_info(vid):
    """Checks the video really exists (Gemini sometimes invents links). Returns {title, author} or None."""
    try:
        j = _get_json("https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(f"https://www.youtube.com/watch?v={vid}"))
        return {"title": j.get("title", ""), "author": j.get("author_name", "")}
    except Exception:  # noqa: BLE001
        return None


def find_videos(brain, query, n=4):
    yk = os.environ.get("YOUTUBE_API_KEY")
    ids = []
    if yk:
        try:
            q = urllib.parse.urlencode({"part": "snippet", "q": query, "type": "video", "maxResults": n + 2,
                                        "videoDuration": "medium", "relevanceLanguage": "en", "key": yk})
            ids = [it["id"]["videoId"] for it in _get_json("https://www.googleapis.com/youtube/v3/search?" + q).get("items", [])]
        except Exception:  # noqa: BLE001
            ids = []
    if not ids:
        text, _ = brain.ask([{"text": f"Search YouTube and the web. List up to {n + 3} real, public YouTube videos (full "
                                      f"youtube.com/watch?v= links) where this is explained in depth, ideally by the person "
                                      f"themselves or a well-known interview: {query}. One link per line, then the title."}],
                            search=True, json_out=False)
        ids = youtube_ids(text)
    out = []
    for vid in ids:
        info = video_info(vid)
        if info:
            out.append({"kind": "video", "id": vid, "url": f"https://www.youtube.com/watch?v={vid}", **info})
        if len(out) >= n:
            break
    return out


def find_papers(topic, n=4):
    q = urllib.parse.urlencode({"search_query": f'all:"{topic}" AND (cat:q-fin.* OR cat:econ.*)', "max_results": n,
                                "sortBy": "relevance"})
    try:
        req = urllib.request.Request("http://export.arxiv.org/api/query?" + q, headers={"User-Agent": UA})
        xml = urllib.request.urlopen(req, timeout=30).read().decode()
    except Exception:  # noqa: BLE001
        return []
    out = []
    for entry in re.findall(r"<entry>(.*?)</entry>", xml, re.S):
        title = re.sub(r"\s+", " ", (re.search(r"<title>(.*?)</title>", entry, re.S) or [None, ""])[1]).strip()
        abst = re.sub(r"\s+", " ", (re.search(r"<summary>(.*?)</summary>", entry, re.S) or [None, ""])[1]).strip()
        link = (re.search(r"<id>(.*?)</id>", entry) or [None, ""])[1]
        if title and abst:
            out.append({"kind": "paper", "id": link, "url": link, "title": title, "abstract": abst[:2500]})
    return out


# ---------------------------------------------------------------- reading
def read_source(brain, src, about):
    if src["kind"] == "video":
        parts = [{"file_data": {"file_uri": src["url"]}, "video_metadata": {"end_offset": f"{VIDEO_MAX_S}s"}},
                 {"text": f"{EXTRACT_SYSTEM}\n\nWatch this video ({src.get('title')} by {src.get('author')}), about: {about}. "
                          "Extract every lesson and rule. Reply with the JSON only."}]
        j, _ = brain.ask(parts, video=True)
        return j, []
    if src["kind"] == "paper":
        j, _ = brain.ask([{"text": f"{EXTRACT_SYSTEM}\n\nResearch paper: {src['title']}\nAbstract: {src['abstract']}\n"
                                   "Extract its findings as lessons (evidence: academic study). JSON only."}])
        return j, []
    # written: Google-grounded summary of a trader's or investor's documented method (books, interviews, articles)
    text, srcs = brain.ask([{"text": f"{EXTRACT_SYSTEM}\n\nUse Google Search. Study what {about} actually teaches in their "
                                     "books, interviews and documented trading: exact entries, exits, stops, position "
                                     "sizing, market filters, psychology, and their real track record and the main "
                                     "criticisms. Reply with ONLY the JSON object."}], search=True, json_out=False)
    return gemini.parse_json(text), srcs


# ---------------------------------------------------------------- the bot's own trades, replayed
def post_mortem(a, ledger):
    """For every closed bot trade: what would have happened with a wider stop, an ATR stop, holding longer,
    and was the stock / market in an uptrend when it bought?"""
    closed = [t for t in ledger.get("trades", []) if t.get("status") == "closed" and t.get("entryPrice") and t.get("cost")]
    if not closed:
        return None
    syms = sorted({t["symbol"] for t in closed} | {"SPY"})
    start = iso(min(parse_time(t["openedAt"]) for t in closed) - timedelta(days=420))
    bars = {}
    st = [s for s in syms if "/" not in s]
    for i in range(0, len(st), 50):
        bars.update(a.stock_bars(st[i:i + 50], "1Day", start, adjustment="all"))
    co = [s for s in syms if "/" in s]
    if co:
        bars.update(a.crypto_bars(co, "1Day", start))
    data = E.load_series(bars)
    spy = data.get("SPY")
    alts = {"actual": 0.0, "stop_8pct": 0.0, "atr_2x": 0.0, "hold_10_days": 0.0, "trend_filter_only": 0.0}
    filt = defaultdict(lambda: [0, 0.0])
    rows = []
    for t in closed:
        s = data.get(t["symbol"])
        d0 = parse_time(t["openedAt"]).astimezone(ZoneInfo("America/New_York")).date().isoformat()
        if not s or d0 not in s.ix:
            continue
        i0, px, cost = s.ix[d0], float(t["entryPrice"]), float(t["cost"])
        actual = float(t.get("pnl") or 0)
        alts["actual"] += actual
        atr = s.atr()[i0 - 1] if i0 else None

        def run(stop=None, days=10):
            for j in range(i0 + 1, min(len(s.c), i0 + 1 + days)):
                if stop and s.l[j] <= stop:
                    return (min(s.o[j], stop) / px - 1)
            j = min(len(s.c) - 1, i0 + days)
            return s.c[j] / px - 1
        r8, ra, r10 = run(px * 0.92), run(px - 2 * atr if atr else px * 0.92), run(None)
        alts["stop_8pct"] += r8 * cost; alts["atr_2x"] += ra * cost; alts["hold_10_days"] += r10 * cost
        up50 = E.cond(s, {"f": "close_above_sma", "n": 50}, i0 - 1, {}) if i0 else False
        spy_i = spy.ix.get(d0) if spy else None
        mkt = E.cond(spy, {"f": "close_above_sma", "n": 50}, spy_i - 1, {}) if spy_i else None
        trend_ok = up50 and bool(mkt)
        if trend_ok:
            alts["trend_filter_only"] += actual
        for name, ok in (("stock above its 50-day", up50), ("market (SPY) above its 50-day", mkt), ("both", trend_ok)):
            filt[f"{name}: {'yes' if ok else 'no'}"][0] += 1
            filt[f"{name}: {'yes' if ok else 'no'}"][1] += actual
        rows.append({"symbol": t["symbol"], "date": d0, "pnl": round(actual), "stop8": round(r8 * cost), "atr2": round(ra * cost),
                     "hold10": round(r10 * cost), "stockUptrend": up50, "marketUptrend": mkt,
                     "moveBeforeBuyPct": (t.get("reason") or {}).get("movePct"), "exit": t.get("exitReason")})
    return {"builtAt": iso(), "trades": len(rows), "alternatives": {k: round(v) for k, v in alts.items()},
            "filters": {k: {"trades": v[0], "pnl": round(v[1])} for k, v in sorted(filt.items())}, "rows": rows,
            "note": "Daily prices after the buy day; the buy day's own path is unknown, so this is an estimate."}


# ---------------------------------------------------------------- the run loop
def fresh_state(days):
    return {"startedAt": iso(), "endsAt": iso(now_utc() + timedelta(days=days)), "days": days,
            "queue": [{"kind": k, "about": about, "tag": tag} for k, about, tag in CURRICULUM],
            "pendingSources": [], "doneSources": [], "failedSources": [], "lessons": [], "rules": {},
            "mentions": [], "counts": {"videos": 0, "papers": 0, "written": 0, "lessons": 0, "rulesTested": 0},
            "pass": 1, "log": []}


def note(st, msg):
    log(msg, "Research Lab")
    st.setdefault("log", []).insert(0, f"{now_utc():%m-%d %H:%M} {msg}")
    del st["log"][60:]


def next_task(st):
    if st["pendingSources"]:
        # round-robin so one person doesn't take the whole day
        last = st.get("lastAbout")
        for i, s in enumerate(st["pendingSources"]):
            if s["about"] != last:
                return "read", st["pendingSources"].pop(i)
        return "read", st["pendingSources"].pop(0)
    if st["queue"]:
        return "find", st["queue"].pop(0)
    # second pass: people and books the sources pointed to, then deeper digs on the top themes
    if st.get("pass", 1) == 1:
        st["pass"] = 2
        top = [m for m, _ in Counter(st.get("mentions", [])).most_common(25)]
        known = " ".join(a for _, a, _ in CURRICULUM).lower()
        st["queue"] = [{"kind": "person", "about": m, "tag": "mentioned"} for m in top if m.lower()[:12] not in known][:20]
        themes = Counter(l["theme"] for l in st["lessons"]).most_common(6)
        st["queue"] += [{"kind": "topic", "about": th.replace("_", " ") + " trading evidence", "tag": "deep"} for th, _ in themes]
        if st["queue"]:
            return "find", st["queue"].pop(0)
    return "idle", None


def add_lessons(st, src, j):
    if not isinstance(j, dict):
        return 0
    person = j.get("person") or src.get("author") or src.get("about")
    n = 0
    for le in (j.get("lessons") or [])[:40]:
        if not isinstance(le, dict) or not le.get("lesson"):
            continue
        theme = le.get("theme") if le.get("theme") in THEMES else "other"
        item = {"theme": theme, "lesson": str(le["lesson"])[:300], "evidence": le.get("evidence") or "claim",
                "person": str(person)[:80], "style": j.get("style"), "source": src.get("url") or src.get("about"),
                "sourceTitle": src.get("title") or src.get("about")}
        r = E.validate(le.get("rule")) if le.get("rule") else None
        if r:
            rid = E.rule_id(r)
            item["ruleId"] = rid
            if rid not in st["rules"]:
                r["from"] = item["person"]; r["lesson"] = item["lesson"]
                st["rules"][rid] = {"rule": r, "status": "untested"}
        st["lessons"].append(item)
        n += 1
    st["mentions"] += [str(m)[:60] for m in (j.get("mentions") or [])[:5] if m]
    st["counts"]["lessons"] = len(st["lessons"])
    return n


def test_rules(st, data, budget_s=600):
    t0 = time.time()
    for rid, r in st["rules"].items():
        if r["status"] != "untested":
            continue
        if time.time() - t0 > budget_s:
            break
        t1 = time.time()
        try:
            ev = E.evaluate(r["rule"], data)
            r.update({"status": ev["verdict"], "why": ev["why"], "score": ev.get("score"), "periods": ev["periods"]})
            if ev["verdict"] in ("passed", "promising"):
                r["robustness"] = E.robustness(r["rule"], data)
                if r["status"] == "passed" and (r["robustness"] or 0) < 0.6:
                    r.update({"status": "promising", "why": "worked, but small changes to its numbers break it (likely a lucky fit)"})
            log(f"Tested '{r['rule']['name'][:50]}': {r['status']} ({time.time() - t1:.0f}s)", "Research Lab")
        except Exception as ex:  # noqa: BLE001  (one bad rule never stops the lab)
            r.update({"status": "error", "why": str(ex)[:150]})
        st["counts"]["rulesTested"] = sum(1 for x in st["rules"].values() if x["status"] != "untested")


def baseline_rules():
    """Rules the lab always tests, so there is a fair comparison even before anything is read."""
    return [
        {"name": "Faber: hold SPY-like leaders over the 200-day", "universe": "stocks", "max_positions": 10, "regime": "spy_above_200",
         "entry": [{"f": "close_above_sma", "n": 200}, {"f": "top_momentum", "days": 126, "top": 10}], "rank": "momentum_126",
         "exit": {"exit_below_sma": 200}},
        {"name": "What the bot did: buy, -3% stop / +6% target, 3 days", "universe": "stocks", "max_positions": 8, "regime": "none",
         "entry": [{"f": "return_above", "days": 1, "pct": 0.5}, {"f": "volume_surge", "days": 20, "mult": 1.2}], "rank": "volume_surge",
         "exit": {"stop_pct": 3, "target_pct": 6, "max_days": 3}},
        {"name": "Minervini-style trend template + breakout", "universe": "stocks", "max_positions": 8, "regime": "spy_above_50",
         "entry": [{"f": "sma_above_sma", "a": 50, "b": 200}, {"f": "near_high", "days": 252, "within_pct": 25},
                   {"f": "breakout", "days": 20}, {"f": "volume_surge", "days": 50, "mult": 1.3}], "rank": "momentum_126",
         "exit": {"stop_pct": 8, "trail_pct": 15}},
        {"name": "Connors RSI-2 pullback in uptrend", "universe": "stocks", "max_positions": 5, "regime": "none",
         "entry": [{"f": "close_above_sma", "n": 200}, {"f": "rsi_below", "n": 2, "value": 10}], "rank": "rsi_low",
         "exit": {"stop_pct": 10, "max_days": 7, "target_pct": 5}},
        {"name": "Crypto above 50-day", "universe": "crypto", "max_positions": 3, "regime": "none",
         "entry": [{"f": "close_above_sma", "n": 50}, {"f": "return_above", "days": 63, "pct": 0}], "rank": "momentum_63",
         "exit": {"exit_below_sma": 50}},
    ]


def market_data(a, st):
    """~3.5 years of daily prices for every halal stock + coin + SPY, cached for the day."""
    from . import halal
    cache = HOME / "bars.json"
    j = read_json(cache, {}) or {}
    if j.get("day") == now_utc().date().isoformat():
        return E.load_series(j["bars"])
    log("Downloading ~3.5 years of daily prices...", "Research Lab")
    t0 = time.time()
    uni = halal.build_universe(a)
    log(f"Halal list ready ({len(uni.get('stocks') or {})} stocks, {len(uni.get('crypto') or {})} coins) in {time.time() - t0:.0f}s", "Research Lab")
    stocks = sorted(set((uni.get("stocks") or {})) | {"SPY"})
    coins = sorted((uni.get("crypto") or {}))
    start = iso(now_utc() - timedelta(days=int(3.6 * 365)))
    bars = {}
    for i in range(0, len(stocks), 50):
        bars.update(a.stock_bars(stocks[i:i + 50], "1Day", start, adjustment="all"))
    if coins:
        bars.update(a.crypto_bars(coins, "1Day", start))
    bars = {s: [{k: b[k] for k in ("t", "o", "h", "l", "c", "v")} for b in bs] for s, bs in bars.items()}
    write_json(cache, {"day": now_utc().date().isoformat(), "bars": bars})
    log(f"Prices ready: {len(bars)} symbols in {time.time() - t0:.0f}s", "Research Lab")
    return E.load_series(bars)


def run(days=7):
    load_env()
    from .alpaca import Alpaca
    a = Alpaca()
    st = read_json(STATE, None) or fresh_state(days)
    if st.get("done"):
        log("The lab already finished. See the report on the Trading tab (tb lab reset to start a new one).", "Research Lab")
        return
    write_json(STATE, st)
    brain = Brain(st)
    if not brain.keys:
        log("No Gemini key for the lab. Add keys with: tb lab keys", "Research Lab")
        return
    note(st, f"Lab running with {len(brain.keys)} Gemini key(s) until {st['endsAt'][:16]} UTC")
    if not any(r["rule"].get("baseline") for r in st["rules"].values()):
        for r in baseline_rules():
            r = E.validate(r); r["baseline"] = True; r["from"] = "baseline"
            st["rules"][E.rule_id(r)] = {"rule": r, "status": "untested"}
    data, data_day = None, None
    while True:
        if now_utc() >= parse_time(st["endsAt"]) or st.get("finishNow"):
            data = data or market_data(a, st)
            test_rules(st, data, budget_s=3600)
            final_report(st, brain)
            st["done"] = True; write_json(STATE, st); publish(st)
            note(st, "Finished. Report is on the Trading tab.")
            return
        if data_day != now_utc().date().isoformat():
            data = market_data(a, st); data_day = now_utc().date().isoformat()
            log("Replaying the bot's own trades...", "Research Lab")
            try:
                st["postMortem"] = post_mortem(a, read_json(DATA / "ledger.json", {}) or {})
                note(st, f"Replayed the bot's {(st['postMortem'] or {}).get('trades', 0)} trades")
            except Exception as ex:  # noqa: BLE001
                note(st, f"post-mortem failed: {ex}")
            test_rules(st, data)
            publish(st)
        kind, task = next_task(st)
        log(f"Next: {kind} {(task or {}).get('title') or (task or {}).get('about') or ''}"[:120], "Research Lab")
        try:
            if kind == "find":
                found = []
                if task["kind"] == "topic":
                    found += [{**p, "about": task["about"]} for p in find_papers(task["about"])]
                if task["kind"] == "person" or task.get("tag") == "deep":
                    found.append({"kind": "written", "id": "w:" + task["about"], "about": task["about"]})
                    found += [{**v, "about": task["about"]} for v in find_videos(brain, task["about"] + " trading strategy explained")]
                seen = set(st["doneSources"]) | set(st["failedSources"]) | {s["id"] for s in st["pendingSources"]}
                new = [f for f in found if f["id"] not in seen]
                st["pendingSources"] += new
                note(st, f"Found {len(new)} sources on {task['about']}")
            elif kind == "read":
                st["lastAbout"] = task["about"]
                j, srcs = read_source(brain, task, task["about"])
                n = add_lessons(st, task, j)
                st["doneSources"].append(task["id"])
                key = {"video": "videos", "paper": "papers"}.get(task["kind"], "written")
                st["counts"][key] += 1
                note(st, f"Read {task['kind']}: {(task.get('title') or task['about'])[:70]}, {n} lessons")
                test_rules(st, data, budget_s=180)
            else:
                # nothing left to read: test, then wait for more quota or the end
                test_rules(st, data)
                publish(st); write_json(STATE, st)
                time.sleep(1800)
        except OutOfQuota:
            if kind == "read":
                st["pendingSources"].insert(0, task)
            elif kind == "find":
                st["queue"].insert(0, task)
            note(st, "All lab keys used up for today: resting until Gemini resets (midnight Pacific)")
            publish(st); write_json(STATE, st)
            tomorrow = (now_utc().astimezone(PT) + timedelta(days=1)).replace(hour=0, minute=10, second=0, microsecond=0)
            time.sleep(max(600, min(6 * 3600, (tomorrow - now_utc().astimezone(PT)).total_seconds())))
        except Busy:
            if kind == "read":
                st["pendingSources"].insert(0, task)
            elif kind == "find":
                st["queue"].insert(0, task)
            note(st, "Gemini busy, trying again in 5 minutes")
            time.sleep(300)
        except ValueError as ex:          # a video Gemini can't open: skip it
            st["failedSources"].append(task["id"])
            note(st, f"Skipped {task.get('title', task['about'])[:60]}: {str(ex)[:80]}")
        except Exception as ex:  # noqa: BLE001
            if kind == "read":
                st["failedSources"].append(task["id"])
            note(st, f"{kind} failed ({str(ex)[:120]}), moving on")
        write_json(STATE, st)
        if len(st["doneSources"]) % 5 == 0:
            publish(st)


# ---------------------------------------------------------------- what the Trading tab shows
def consensus(st):
    """Common factors: how many DIFFERENT people teach each theme."""
    people = defaultdict(set)
    ex = defaultdict(list)
    for le in st["lessons"]:
        people[le["theme"]].add(le["person"])
        if len(ex[le["theme"]]) < 4:
            ex[le["theme"]].append(f"{le['person']}: {le['lesson']}")
    return [{"theme": th, "people": len(p), "examples": ex[th]} for th, p in sorted(people.items(), key=lambda x: -len(x[1]))]


def leaderboard(st, n=15):
    rs = [dict(r["rule"], id=rid, status=r["status"], why=r.get("why"), score=r.get("score"), robustness=r.get("robustness"),
               full=(r.get("periods") or {}).get("full"), last60=(r.get("periods") or {}).get("last60"))
          for rid, r in st["rules"].items() if r["status"] in ("passed", "promising", "failed")]
    order = {"passed": 0, "promising": 1, "failed": 2}
    rs.sort(key=lambda r: (order[r["status"]], -(r["score"] or -99)))
    return rs[:n]


def publish(st):
    tested = [r for r in st["rules"].values() if r["status"] != "untested"]
    out = {"updatedAt": iso(), "startedAt": st["startedAt"], "endsAt": st["endsAt"], "done": bool(st.get("done")),
           "counts": {**st["counts"], "sourcesRead": len(st["doneSources"]), "waiting": len(st["pendingSources"]) + len(st["queue"]),
                      "rules": len(st["rules"]), "passed": sum(1 for r in tested if r["status"] == "passed"),
                      "promising": sum(1 for r in tested if r["status"] == "promising")},
           "consensus": consensus(st)[:15], "leaderboard": leaderboard(st), "postMortem": st.get("postMortem"),
           "log": st.get("log", [])[:20], "reportUrl": "data/trading/lab/report.md" if st.get("done") or st.get("reported") else None}
    write_json(OUT / "lab.json", out)
    return out


def final_report(st, brain):
    pub = publish(st)
    facts = {"counts": pub["counts"], "commonFactors": pub["consensus"], "rules": pub["leaderboard"],
             "botPostMortem": {k: v for k, v in (st.get("postMortem") or {}).items() if k != "rows"},
             "botSettingsNow": {"stopLossPct": C.RISK.get("stop_loss_pct"), "takeProfitPct": C.RISK.get("take_profit_pct"),
                                "maxHoldDays": C.RISK.get("stock_max_hold_trading_days"), "entry": "buys on news within minutes, "
                                "-3% stop or 3% trailing stop, 3-day limit"}}
    prompt = ("You are writing the final report of a trading research lab for Omar, a beginner who wants the truth in plain "
              "words (no emojis, no arrow math, short sentences, bold headers and bullets). Use ONLY the facts below.\n"
              "Sections: **The short answer** (3 lines). **What everyone agrees on** (common factors across the most "
              "different people, and where they disagree). **What the bot was doing wrong** (from the post-mortem numbers). "
              "**Rules that passed the tests** (with return, worst drop vs SPY, robustness; say plainly if none passed). "
              "**The new playbook** (exact rules for the bot, ONLY from rules that passed, plus the strongest common factors; "
              "'promising' rules are NOT proven, random noise often looks promising). **What is still unproven**. Then a final section starting with the line '---SKILL---' containing a "
              "Claude skill (markdown with a short YAML header: name: trading-playbook, description) that a future Claude can "
              "follow daily to run this playbook for a halal, long-only, cash-only paper account.\n\nFACTS:\n"
              + json.dumps(facts)[:60000])
    try:
        text, _ = brain.ask([{"text": prompt}], json_out=False, strong=True, temperature=0.4)
    except Exception as ex:  # noqa: BLE001
        text = "Report writer could not run (" + str(ex)[:120] + "). Raw results:\n\n" + json.dumps(facts, indent=1)[:20000]
    report, _, skill = text.partition("---SKILL---")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "report.md").write_text(report.strip() + "\n", encoding="utf-8")
    if skill.strip():
        (OUT / "skill.md").write_text(skill.strip() + "\n", encoding="utf-8")
    play = [r for r in pub["leaderboard"] if r["status"] == "passed"]          # promising = unproven: never in the playbook
    write_json(OUT / "playbook.json", {"builtAt": iso(), "rules": play[:6]})
    st["reported"] = True
    publish(st)


def status():
    st = read_json(STATE, None)
    if not st:
        print("The lab hasn't started. Start it with: tb lab start 7")
        return
    p = publish(st)
    c = p["counts"]
    print(f"Running since {st['startedAt'][:16]} UTC, ends {st['endsAt'][:16]} UTC{' (DONE)' if st.get('done') else ''}")
    print(f"Read: {c['videos']} videos, {c['written']} trader write-ups, {c['papers']} papers. {c['lessons']} lessons. "
          f"{c['waiting']} sources waiting.")
    print(f"Rules: {c['rules']} found, {c['rulesTested']} tested, {c['passed']} passed, {c['promising']} promising.")
    for th in p["consensus"][:6]:
        print(f"  {th['people']:>3} people teach: {th['theme'].replace('_', ' ')}")
    for r in p["leaderboard"][:5]:
        f = r.get("full") or {}
        print(f"  [{r['status']}] {r['name'][:60]}: {f.get('returnPct')}% (worst drop {f.get('maxDrawdownPct')}%, SPY {f.get('spyReturnPct')}%)")
    for line in st.get("log", [])[:5]:
        print("  " + line)


def main(argv):
    cmd = argv[0] if argv else "status"
    if cmd == "run":
        run(int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 7)
    elif cmd == "init":
        days = int(argv[1]) if len(argv) > 1 and argv[1].isdigit() else 7
        st = read_json(STATE, None)
        if st and not st.get("done"):
            print(f"Already running, ends {st['endsAt'][:16]} UTC.")
            return
        write_json(STATE, fresh_state(days))
        print(f"Lab set for {days} days.")
    elif cmd == "status":
        status()
    elif cmd == "report":
        st = read_json(STATE, None)
        if not st:
            print("Nothing to report yet."); return
        st["finishNow"] = True; write_json(STATE, st)
        print("The lab will write the final report at its next step (watch: tb lab status).")
    elif cmd == "reset":
        if STATE.exists():
            STATE.unlink()
        print("Lab state cleared. Start again with: tb lab start <days>")


if __name__ == "__main__":
    main(sys.argv[1:])
