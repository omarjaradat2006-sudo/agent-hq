"""Weekly licence check: is each sportsbook still on the iGaming Ontario / AGCO list?
A brand is only switched on or off when the search cites igamingontario.ca or agco.ca.
Uses Gemini only (no Odds API credits). Bet365 is never checked, listed or used."""
import os, sys
import config as C
import store as S
from picks import SYSTEM

sys.path.insert(0, os.path.join(C.ROOT, "agents", "gemini"))
import gemini as G  # noqa: E402

PATH = os.path.join(C.DATA, "books.json")
OFFICIAL = ("igamingontario.ca", "agco.ca")


def run():
    st = S.state()
    cur = S.load(PATH, {"overrides": {}})
    names = {k: b["name"].replace(" (ESPN BET feed)", "") for k, b in C.BOOKS.items()}
    q = ("Search the iGaming Ontario operator directory (igamingontario.ca) and the AGCO registrar list (agco.ca). "
         "For each sportsbook brand below, is it CURRENTLY live and offering sports betting to players in Ontario? "
         "Reply JSON only: {\"books\":[{\"brand\":\"...\",\"ontario\":true|false|null,\"note\":\"...\"}]}. Use null if you can't confirm.\n"
         + "\n".join(f"- {n}" for n in names.values()))
    text, src = G.generate(q, SYSTEM, search=True, temperature=0)
    official = [u for _, u in src if any(d in u for d in OFFICIAL)]
    try:
        rows = G.parse_json(text).get("books", [])
    except Exception:
        rows = []
    changes, results = [], {}
    for k, n in names.items():
        r = next((x for x in rows if isinstance(x, dict) and str(x.get("brand", "")).lower().startswith(n.lower()[:6])), None)
        verdict = r.get("ontario") if r else None
        results[k] = {"name": n, "ontario": verdict, "note": S.sanitize(str((r or {}).get("note", "")))[:200]}
        if verdict is None or not official:
            continue  # only act on an official source
        was = cur["overrides"].get(k, {}).get("on", C.BOOKS[k]["on"])
        if bool(verdict) != was:
            cur["overrides"][k] = {"on": bool(verdict), "source": official[0], "at": S.now_iso()}
            changes.append(f"{n} {'added' if verdict else 'removed'}")
    cur.update(checkedAt=S.now_iso(), results=results, officialSources=official[:5])
    S.save(PATH, cur)
    msg = ("Licence check: " + ", ".join(changes)) if changes else (
        "Licence check: no changes" + ("" if official else " (no official iGO/AGCO page found, so nothing was changed)"))
    S.agent(st, "odds", "ok", msg)
    S.log(st, "Odds Scout", msg)
    import report
    report.refresh(st, S.ledger())
    print(msg)
