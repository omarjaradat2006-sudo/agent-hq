"""Merge out/<job>_patch.json into data/<team>/state.json on the LATEST commit. Never changes Omar's idea statuses."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
job = sys.argv[1]
patch = json.load(open(os.path.join(ROOT, "out", f"{job}_patch.json"), encoding="utf-8"))
team = patch["team"]
path = os.path.join(ROOT, "data", team, "state.json")
s = json.load(open(path, encoding="utf-8"))
ids = {i.get("id") for i in s.get("ideas", [])}
s.setdefault("ideas", []).extend(i for i in patch.get("ideas", []) if isinstance(i, dict) and i.get("id") and i["id"] not in ids)
if "lineup" in patch and s.get("lineup"):
    s["pastLineups"] = ([s["lineup"]] + s.get("pastLineups", []))[:7]
for k in ("review", "brief", "competitors", "formatLeads", "teamLeads", "upgradeBrief", "lineup", "footage"):
    if k in patch:
        s[k] = patch[k]
if "competitors" in patch:
    s["competitorsUpdated"] = patch["at"]
if isinstance(patch.get("review"), dict):
    s.setdefault("reviewHistory", []).insert(0, {"date": patch["review"].get("date"), "headline": patch["review"].get("headline")})
    s["reviewHistory"] = s["reviewHistory"][:30]
for k, keep in (("research", 14), ("swarms", 10)):
    if k in patch:
        new = patch[k] if isinstance(patch[k], list) else [patch[k]]
        s[k] = (new + s.get(k, []))[:keep]
ra = patch.get("requestAnswers") or {}
if isinstance(ra, list):  # model sometimes returns [{"id"/"request":..., "answer":...}] or plain strings
    ra = {str((a.get("id") or a.get("request") or n) if isinstance(a, dict) else n):
          (a.get("answer") or a.get("text") or json.dumps(a)) if isinstance(a, dict) else a for n, a in enumerate(ra)}
open_reqs = [r for r in s.get("requests", []) if r.get("status") != "answered"]
for n, (rid, ans) in enumerate(ra.items()):
    match = [r for r in open_reqs if r.get("id") == rid or (r.get("text") and r["text"][:40] == str(rid)[:40])]
    if not match and n < len(open_reqs):  # requests without ids: answer them in order
        match = [open_reqs[n]]
    for r in match:
        if r.get("status") != "answered":
            r.update(status="answered", answer=str(ans)[:600], answeredAt=patch["at"])
log = patch.get("log", [])
s["log"] = ((log if isinstance(log, list) else [log])[::-1] + s.get("log", []))[:100]
known = {a.get("id") for a in s.get("agents", [])}
for a in s.get("agents", []):
    if isinstance(patch.get("agents"), dict) and a.get("id") in patch["agents"] and isinstance(patch["agents"][a["id"]], dict):
        a.update(patch["agents"][a["id"]])
s["updatedAt"] = patch["at"]
json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("merged", job, "into", team)
