"""Save results to GitHub a few times a day (only the data/trading folder) so the Trading tab can show them."""
import subprocess
from datetime import timedelta
from . import config as C
from .util import ROOT, iso, now_utc, now_et, parse_time, log

MIN_GAP = timedelta(minutes=45)


def _git(*args, timeout=120):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, timeout=timeout)


def due(s):
    """True at each scheduled time (once), or after a trade / alert (throttled)."""
    now = now_et()
    last = parse_time(s.get("lastPublish"))
    if last and now_utc() - last < MIN_GAP and not s.get("alert"):
        return False
    if s.get("publishNow"):
        return True
    done = s.get("publishedSlots") or {}
    day = now.date().isoformat()
    for slot in C.LOOP["publish_times_et"]:
        h, m = map(int, slot.split(":"))
        if now >= now.replace(hour=h, minute=m, second=0, microsecond=0) and done.get(slot) != day:
            return slot
    return False


def maybe(s):
    d = due(s)
    if not d:
        return False
    ok = push("Trading bot: paper results " + now_et().strftime("%b %d %H:%M"))
    if ok:
        s["lastPublish"] = iso()
        s["publishNow"] = False
        s.setdefault("publishedSlots", {})
        day = now_et().date().isoformat()
        for slot in C.LOOP["publish_times_et"]:   # mark every slot that has passed as done
            h, m = map(int, slot.split(":"))
            if now_et() >= now_et().replace(hour=h, minute=m, second=0, microsecond=0):
                s["publishedSlots"][slot] = day
    return ok


def push(message):
    try:
        _git("add", "data/trading")
        if _git("diff", "--cached", "--quiet", "--", "data/trading").returncode == 0:
            return True
        c = _git("-c", "user.name=Agent HQ Trading Bot", "-c", "user.email=actions@users.noreply.github.com",
                 "commit", "-q", "-m", message, "--", "data/trading")
        if c.returncode != 0:
            log(f"Save to GitHub: commit failed: {c.stderr.strip()[:150]}", "Trader")
            return False
        for _ in range(3):
            _git("pull", "-q", "--rebase", "--autostash", "origin", "main")
            p = _git("push", "-q", "origin", "HEAD:main")
            if p.returncode == 0:
                log("Saved results to the Agent HQ dashboard", "Trader")
                return True
        log(f"Save to GitHub failed (will retry later): {p.stderr.strip()[:150]}", "Trader")
    except (OSError, subprocess.TimeoutExpired) as e:
        log(f"Save to GitHub failed: {e}", "Trader")
    return False
