"""Files: data/fight/state.json (what Agent HQ shows) and data/fight/ledger.json (every bet ever posted + result)."""
import datetime, json, os
from zoneinfo import ZoneInfo
import config as C

TZ = ZoneInfo("America/Toronto")
STATE = os.path.join(C.DATA, "state.json")
LEDGER = os.path.join(C.DATA, "ledger.json")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today():
    return datetime.datetime.now(TZ).date().isoformat()


def load(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save(path, obj):
    if path == LEDGER:
        obj["savedAt"] = now_iso()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, path)


def state():
    return load(STATE, {"team": "fight", "hired": True, "agents": [], "log": []})


def ledger():
    lg = load(LEDGER, {"bets": [], "cards": []})
    lg.setdefault("bets", []); lg.setdefault("cards", [])
    return lg


def log(s, agent, msg):
    s["log"] = ([{"t": now_iso(), "agent": agent, "msg": str(msg)[:240]}] + s.get("log", []))[:100]


def agent(s, aid, status, doing):
    for a in s.get("agents", []):
        if a.get("id") == aid:
            a.update(status=status, doing=str(doing)[:160], lastRun=now_iso())


def sanitize(text):
    """No 'lock' / 'guaranteed' / 'safest' wording, and no Bet365, in anything shown."""
    if not isinstance(text, str):
        return text
    def sub(m):
        w = m.group(0).lower()
        return "lean" if w.startswith("lock") else "most analyzed" if w == "safest" else "likely"
    return C.BANNED.sub("[excluded book]", C.FORBIDDEN.sub(sub, text))


def clean(obj):
    if isinstance(obj, str):
        return sanitize(obj)
    if isinstance(obj, list):
        return [clean(x) for x in obj]
    if isinstance(obj, dict):
        return {k: clean(v) for k, v in obj.items()}
    return obj
