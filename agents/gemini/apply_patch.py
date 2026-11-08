"""Merge out/<job>_patch.json into data/<team>/state.json on the LATEST commit. Never changes Omar's idea statuses."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
job = sys.argv[1]
patch = json.load(open(os.path.join(ROOT, "out", f"{job}_patch.json"), encoding="utf-8"))
team = patch["team"]
path = os.path.join(ROOT, "data", team, "state.json")
s = json.load(open(path, encoding="utf-8"))
ids = {i.get("id") for i in s.get("ideas", [])}
s.setdefault("ideas", []).extend(i for i in patch.get("ideas", []) if i["id"] not in ids)
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
for rid, ans in (patch.get("requestAnswers") or {}).items():
    for r in s.get("requests", []):
        if r.get("id") == rid and r.get("status") != "answered":
            r.update(status="answered", answer=str(ans)[:300], answeredAt=patch["at"])
s["log"] = (patch.get("log", [])[::-1] + s.get("log", []))[:100]
known = {a.get("id") for a in s.get("agents", [])}
for a in s.get("agents", []):
    if a.get("id") in patch.get("agents", {}):
        a.update(patch["agents"][a["id"]])
s["updatedAt"] = patch["at"]
json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("merged", job, "into", team)
