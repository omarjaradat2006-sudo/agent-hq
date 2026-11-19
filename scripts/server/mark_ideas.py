"""Mark YouTube board ideas "done" once their video is uploaded AND confirmed by YouTube.

    python mark_ideas.py bounce|ambient        (run by run_bounce.sh / run_ambient.sh after mark.py, before save_hq)

A lineup slot made from a board idea carries "ideaId". For today's lineup and the last 7 (pastLineups):
  uploaded  = the slot's title is in <BOUNCE_LOGS>/<Channel>_uploaded_log.json with a YouTube id
  confirmed = verify.py has deleted the local file (it only deletes after YouTube confirms the upload)
Then the idea gets status "done", doneAt, video (link) and doneNote. Ideas that still need a new template are never touched here.
"""
import os, re, sys, json, datetime
from zoneinfo import ZoneInfo

CH = {"bounce": ("Bounce Theory", "BounceTheory", "2 Bounce Theory - Upload Today"),
      "ambient": ("Ambient Escape", "AmbientEscape", "1 Ambient Escape - Upload Today")}
ch, logname, folder = CH[sys.argv[1]]
HQ = os.environ.get("AGENT_HQ") or os.path.expanduser("~/agent-hq")
LOGS = os.environ.get("BOUNCE_LOGS") or os.path.expanduser("~/bounce-data/logs")
OUTD = os.path.join(os.environ.get("BOUNCE_STUDIO") or os.path.expanduser("~/bounce-studio"), folder)
STATE = os.path.join(HQ, "data", "youtube", "state.json")


def norm(t):
    t = re.sub(r"#\S+", "", str(t or "").lower())
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def load(p, d):
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return d


s = load(STATE, None)
if not s:
    print("mark_ideas: no state.json"); sys.exit(0)
ups = load(os.path.join(LOGS, logname + "_uploaded_log.json"), []) or []
by_title = {}
for u in ups:
    if u.get("id") and u.get("title"):
        by_title[norm(u["title"])] = u
ideas = {i.get("id"): i for i in s.get("ideas", [])}
now = datetime.datetime.now(ZoneInfo("America/Toronto")).isoformat(timespec="seconds")
done = 0
for L in [s.get("lineup") or {}] + (s.get("pastLineups") or []):
    for sl in ((L.get("channels") or {}).get(ch) or []):
        if not isinstance(sl, dict) or not sl.get("ideaId"):
            continue
        idea = ideas.get(sl["ideaId"])
        if not idea or idea.get("status") != "approved":
            continue
        u = by_title.get(norm(sl.get("title")))
        if not u:
            continue
        f = u.get("file")
        if f and os.path.exists(os.path.join(OUTD, f)):      # not confirmed by YouTube yet (verify.py keeps it)
            continue
        idea.update(status="done", doneAt=now, video=f"https://youtu.be/{u['id']}", doneBy="server",
                    doneNote=f"Uploaded to {ch} {str(u.get('uploaded', ''))[:10]} (lineup {L.get('date')} {sl.get('slot', '')})")
        done += 1
if done:
    s.setdefault("log", []).insert(0, {"t": now, "agent": "Producer", "msg": f"Marked {done} board idea(s) done: uploaded and confirmed on {ch}"})
    json.dump(s, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print(f"mark_ideas {ch}: {done} idea(s) marked done")
