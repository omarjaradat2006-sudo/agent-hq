"""Merge out/<team>_patch.json into data/<team>/state.json on the LATEST commit (never touches idea statuses)."""
import json, os, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
team = sys.argv[1]
patch = json.load(open(os.path.join(ROOT, "out", f"{team}_patch.json"), encoding="utf-8"))
path = os.path.join(ROOT, "data", team, "state.json")
s = json.load(open(path, encoding="utf-8"))
ids = {i["id"] for i in s.get("ideas", [])}
s.setdefault("ideas", []).extend(i for i in patch.get("ideas", []) if i["id"] not in ids)
for k in ("review", "brief"):
    if k in patch:
        s[k] = patch[k]
if k := patch.get("review"):
    s.setdefault("reviewHistory", []).insert(0, {"date": k.get("date"), "headline": k.get("headline")})
    s["reviewHistory"] = s["reviewHistory"][:30]
if "research" in patch:
    s.setdefault("research", []).insert(0, patch["research"]); s["research"] = s["research"][:14]
s["log"] = (patch.get("log", [])[::-1] + s.get("log", []))[:100]
for a in s.get("agents", []):
    if a.get("id") in patch.get("agents", {}):
        a.update(patch["agents"][a["id"]])
s["updatedAt"] = patch["at"]
json.dump(s, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("merged", team)
