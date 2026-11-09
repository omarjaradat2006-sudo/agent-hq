"""Small shared helpers: .env, HTTP, time in New York, JSON files, logging."""
import json, os, sys, time, urllib.request, urllib.error, urllib.parse
from datetime import datetime, timezone, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent          # agent-hq repo root
DATA = ROOT / "data" / "trading"                       # what the Trading tab reads (committed)
LOCAL = ROOT / "trading_bot" / "local"                 # private working files (git-ignored)
ET = ZoneInfo("America/New_York")
UA = "AgentHQ-PaperTradingBot/1.0 (+https://github.com/omarjaradat2006-sudo/agent-hq)"


def load_env():
    """Read trading_bot/.env (KEY=value lines). Keys never leave this machine."""
    p = ROOT / "trading_bot" / ".env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    # TradingAgents reads GOOGLE_API_KEY; Omar's key is GEMINI_API_KEY.
    if os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
        os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


def now_utc():
    return datetime.now(timezone.utc)


def now_et():
    return datetime.now(ET)


def iso(dt=None):
    return (dt or now_utc()).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(s):
    if not s:
        return None
    if isinstance(s, datetime):
        return s if s.tzinfo else s.replace(tzinfo=timezone.utc)
    s = str(s).strip()
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        if "." in s:   # trim nanoseconds Alpaca sometimes sends
            head, _, tail = s.partition(".")
            frac = "".join(ch for ch in tail if ch.isdigit())[:6]
            rest = tail[len("".join(ch for ch in tail if ch.isdigit())):]
            s = f"{head}.{frac}{rest}"
        d = datetime.fromisoformat(s)
        return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
    except ValueError:
        from email.utils import parsedate_to_datetime
        try:
            return parsedate_to_datetime(s)
        except (TypeError, ValueError):
            return None


def http(method, url, params=None, body=None, headers=None, timeout=30, retries=2):
    """JSON (or text) HTTP call. Returns parsed JSON when possible, else text."""
    if params:
        url += ("&" if "?" in url else "?") + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    data = json.dumps(body).encode() if body is not None else None
    h = {"User-Agent": UA, "Accept": "application/json, application/xml, text/xml, */*"}
    if body is not None:
        h["Content-Type"] = "application/json"
    h.update(headers or {})
    last = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                raw = r.read().decode("utf-8", "replace")
                if not raw:
                    return None
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    return raw
        except urllib.error.HTTPError as e:
            msg = e.read().decode("utf-8", "replace")[:400]
            last = HttpError(e.code, msg, url)
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(3 * (attempt + 1))
                continue
            raise last
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = HttpError(0, str(e), url)
            if attempt < retries:
                time.sleep(3 * (attempt + 1))
                continue
            raise last
    raise last


class HttpError(Exception):
    def __init__(self, code, msg, url):
        super().__init__(f"HTTP {code} {url.split('?')[0]}: {msg[:200]}")
        self.code, self.msg, self.url = code, msg, url


def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def write_json(path, obj):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    os.replace(tmp, p)


_LOG = []


def log(msg, agent="Trader"):
    """Print + keep for the dashboard activity log."""
    line = f"[{now_et():%m-%d %H:%M}] {agent}: {msg}"
    try:
        print(line, flush=True)
    except UnicodeEncodeError:
        print(line.encode("ascii", "replace").decode(), flush=True)
    _LOG.append({"t": iso(), "agent": agent, "msg": msg})
    LOCAL.mkdir(parents=True, exist_ok=True)
    with open(LOCAL / "bot.log", "a", encoding="utf-8") as f:
        f.write(line + "\n")


def drain_log():
    out = list(_LOG)
    _LOG.clear()
    return out


class SingleInstance:
    """Stops a second copy (double-click + Task Scheduler) from trading at the same time."""

    def __init__(self, name="bot.lock"):
        LOCAL.mkdir(parents=True, exist_ok=True)
        self.path = LOCAL / name
        self.f = None

    def __enter__(self):
        self.f = open(self.path, "a+")
        try:
            if sys.platform == "win32":
                import msvcrt
                self.f.seek(0)
                msvcrt.locking(self.f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            self.f.close()
            print("The trading bot is already running in another window. Close that one first.", flush=True)
            raise SystemExit(3)
        return self

    def __exit__(self, *a):
        try:
            self.f.close()
        except OSError:
            pass


def trading_days_between(start_date, end_date, calendar_dates):
    """Number of market days strictly after start_date up to and including end_date."""
    return sum(1 for d in calendar_dates if start_date < d <= end_date)


def round_price(p):
    return round(p, 2) if p >= 1 else round(p, 4)


__all__ = ["ROOT", "DATA", "LOCAL", "ET", "timedelta"]
