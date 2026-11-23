"""Gemini triage: is this real market-moving news, which allowed assets, which way, how sure?

Gemini only proposes. Code then drops any asset that isn't in the halal universe, and the
confirmation + risk rules decide whether anything happens.
"""
import json, sys
from datetime import timedelta
from . import config as C
from .util import ROOT, iso, now_utc, parse_time, log, event

sys.path.insert(0, str(ROOT / "agents" / "gemini"))
import gemini  # noqa: E402  (Agent HQ's shared Gemini client, key from GEMINI_API_KEY)


def use_triage_model():
    """Triage runs every few minutes, so it uses Flash-Lite (bigger free daily quota) unless TRIAGE_MODEL is set.
    TradingAgents keeps the stronger Flash model for the deep analysis."""
    if getattr(gemini, "_triage_set", False):
        return
    import os
    gemini.KEY = gemini.KEY or os.environ.get("GEMINI_API_KEY", "").strip()
    m = os.environ.get("TRIAGE_MODEL")
    lites = [m] if m else []
    if not lites:
        try:
            names = [x["name"].split("/")[-1] for x in gemini._req("GET", "models?pageSize=200").get("models", [])
                     if "generateContent" in x.get("supportedGenerationMethods", [])]
            lites = sorted([n for n in names if "flash-lite" in n and gemini.text_model_ok(n)], reverse=True)[:3]
            FLASH_BACKUP[:] = sorted([n for n in names if "flash" in n and "lite" not in n and gemini.text_model_ok(n)], reverse=True)[:2]
        except Exception:  # noqa: BLE001
            lites = []
    if lites:
        # Must be a LIST: gemini.generate() loops over it (a plain string made it try one letter at a time,
        # so every triage call failed). Flash-Lite only, so a quota hit here never spends the Flash quota
        # the 9 agent teams need: triage just skips that cycle (= no trades, which is safe).
        gemini._model = list(lites)
    gemini._triage_set = True

SYSTEM = """You are the news triage desk of a cautious, rules-based paper-trading bot.
You read raw headlines and decide which are REAL, market-moving news. Most headlines are not.
You only map news to assets from the ALLOWED list you are given. You never invent tickers.
Long-only bot: "up" means a reason to buy, "down" means a reason to sell if already held.
Confidence is your honest probability (0-1) that the asset moves that way over the next 1-3 days because of this news.
Be conservative: if it is opinion, a recap, a rumour, old news, or unclear, mark is_market_news false or give no assets.
Return JSON only."""

SCHEMA = """{"events": [{
  "key": "short-kebab-slug for this story (reuse an OPEN EVENT key if it is the same story)",
  "is_market_news": true,
  "category": "war_escalation|deescalation|central_bank_dovish|central_bank_hawkish|inflation|earnings_beat|earnings_miss|contract|company_bad_news|tariffs|crypto_positive|crypto_negative|oil_supply|other",
  "summary": "one plain sentence",
  "item_ids": ["ids of the headlines about this story"],
  "assets": [{"symbol": "TICKER or BTC/USD", "direction": "up|down", "confidence": 0.0, "why": "short reason"}],
  "meme_coins": [{"name": "coin name", "ticker": "TICKER", "direction": "up|down", "why": "short"}]
}]}"""


FLASH_BACKUP = []    # used only when Flash-Lite is overloaded (503), never when out of quota
FAILED_IDS = []      # headlines Gemini couldn't read this cycle (overloaded): the bot re-reads them next cycle


def triage(items, events, universe, held, raise_on_fail=False):
    FAILED_IDS.clear()
    if not items:
        return []
    use_triage_model()
    allowed = sorted(list((universe.get("stocks") or {}).keys()) + list((universe.get("crypto") or {}).keys()))
    themes = {}
    for s, v in (universe.get("stocks") or {}).items():
        themes.setdefault(v.get("theme", "other"), []).append(s)
    themes["crypto"] = list((universe.get("crypto") or {}).keys())
    open_ev = [{"key": k, "summary": e["summary"]} for k, e in list(events.items())[-40:]]
    out = []
    for i in range(0, len(items), 70):
        batch = items[i:i + 70]
        heads = [{"id": x["id"], "publisher": x["publisher"], "time": x["time"], "title": x["title"],
                  "summary": x["summary"][:200], "tickers": x["symbols"][:6]} for x in batch]
        prompt = (f"PLAYBOOK (Omar's rules, expand with common sense):\n{C.PLAYBOOK}\n"
                  f"ALLOWED assets by theme (halal-screened): {json.dumps(themes)}\n"
                  f"Currently HELD: {json.dumps(sorted(held))}\n"
                  f"Meme / celebrity coins to WATCH (never trade, just report): {sorted(C.MEME_COINS)} plus any brand-new celebrity/politician coin.\n"
                  f"OPEN EVENTS (attach to these keys when it's the same story): {json.dumps(open_ev)}\n\n"
                  f"HEADLINES:\n{json.dumps(heads, ensure_ascii=False)}\n\n"
                  f"Group headlines into stories. Return only stories that matter, as JSON in this shape:\n{SCHEMA}")
        try:
            try:
                text, _ = gemini.generate(prompt, system=SYSTEM, json_out=True, temperature=0.2)
            except Exception as e1:  # noqa: BLE001
                if "503" not in str(e1) and "overload" not in str(e1).lower() and "UNAVAILABLE" not in str(e1):
                    raise
                # Flash-Lite overloaded (not out of quota): wait, then retry with Flash allowed as a backup
                import time as _t
                _t.sleep(20)
                saved = list(gemini._model or [])
                try:
                    gemini._model = saved + [m for m in FLASH_BACKUP if m not in saved]
                    text, _ = gemini.generate(prompt, system=SYSTEM, json_out=True, temperature=0.2)
                finally:
                    gemini._model = saved
            data = gemini.parse_json(text)
        except Exception as e:  # noqa: BLE001  (network/quota) -> no events this cycle, no trades
            log(f"Gemini triage failed, skipping this batch: {str(e)[:160]}", "News Analyst")
            event("error", "gemini_triage", str(e)[:200])
            FAILED_IDS.extend(x["id"] for x in batch)
            if raise_on_fail:
                raise
            continue
        for ev in (data.get("events") if isinstance(data, dict) else data) or []:
            if not isinstance(ev, dict) or not ev.get("key"):
                continue
            ev["assets"] = [a for a in ev.get("assets") or []
                            if isinstance(a, dict) and a.get("symbol") in allowed and a.get("direction") in ("up", "down")]
            for a in ev["assets"]:
                try:
                    a["confidence"] = max(0.0, min(1.0, float(a.get("confidence", 0))))
                except (TypeError, ValueError):
                    a["confidence"] = 0.0
            ev["item_ids"] = [x for x in ev.get("item_ids") or [] if x in {b["id"] for b in batch}]
            out.append(ev)
    return out


def merge(events, triaged, items_by_id):
    """Fold triage output into the running event store (state['events'])."""
    now = iso()
    for ev in triaged:
        if not ev.get("is_market_news", True) and not ev.get("meme_coins"):
            continue
        # A story that keeps coming back (e.g. "Nvidia surges" on Nov 12 and again on Nov 23) must count as NEW news
        # each time, not as the old story: otherwise it looks days old (too stale to trade) and is "already decided".
        # New headlines more than event_fresh_hours after the current wave started open a new wave with its own key.
        new_t = max([items_by_id[i]["time"] for i in ev.get("item_ids") or [] if i in items_by_id and items_by_id[i].get("time")]
                    or [now])
        waves = sorted([k for k in events if k == ev["key"] or k.startswith(ev["key"] + "@")],
                       key=lambda k: events[k].get("firstSeen", ""))
        key = waves[-1] if waves else ev["key"]
        cur = events.get(key)
        if cur and (parse_time(new_t) - parse_time(cur["firstSeen"])) > timedelta(hours=C.CONFIRM["event_fresh_hours"]):
            key = f"{ev['key']}@{parse_time(new_t):%Y%m%d%H%M}"
        e = events.setdefault(key, {"key": key, "category": ev.get("category", "other"),
                                    "summary": ev.get("summary", ""), "firstSeen": new_t, "items": [],
                                    "assets": {}, "memes": []})
        e["lastSeen"] = now
        if ev.get("summary"):
            e["summary"] = ev["summary"]
        have = {x["id"] for x in e["items"]}
        for iid in ev.get("item_ids") or []:
            it = items_by_id.get(iid)
            if it and iid not in have:
                e["items"].append({k: it.get(k) for k in ("id", "publisher", "kind", "title", "url", "time")})
                if it.get("time") and it["time"] < e["firstSeen"] and \
                        parse_time(e["firstSeen"]) - parse_time(it["time"]) <= timedelta(hours=C.CONFIRM["event_fresh_hours"]):
                    e["firstSeen"] = it["time"]
        for a in ev.get("assets") or []:
            prev = e["assets"].get(a["symbol"])
            if not prev or a["confidence"] >= prev.get("confidence", 0) or prev.get("direction") != a["direction"]:
                e["assets"][a["symbol"]] = {"direction": a["direction"], "confidence": a["confidence"], "why": a.get("why", "")}
        for m in ev.get("meme_coins") or []:
            if isinstance(m, dict) and (m.get("ticker") or m.get("name")):
                e["memes"].append({**m, "at": now})
    cutoff = now_utc() - timedelta(hours=24)
    for k in [k for k, e in events.items() if (parse_time(e.get("lastSeen")) or now_utc()) < cutoff]:
        events.pop(k)
    return events


def publishers(event):
    pubs = {x["publisher"] for x in event["items"]} - {"Unknown", "Google News"}
    news = {p for p in pubs if p not in C.SOCIAL_PUBLISHERS}
    return pubs, news
