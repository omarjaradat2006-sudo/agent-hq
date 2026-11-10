"""Which Gemini models does Fight & Court's key actually get? Never prints the key.
Run on the server:  set -a; . ~/.agent-hq.env; set +a; python3 ~/agent-hq/agents/fight/gemini_check.py"""
import json, os, re, urllib.request, urllib.error

own = (os.environ.get("GEMINI_API_KEY_FIGHT") or "").strip()
key = own or (os.environ.get("GEMINI_API_KEY") or "").strip()
print("Key used:", "own key (GEMINI_API_KEY_FIGHT)" if own else "shared key (GEMINI_API_KEY)" if key else "NONE", "| length", len(key))
base = "https://generativelanguage.googleapis.com/v1beta"


def call(method, path, body=None):
    req = urllib.request.Request(f"{base}/{path}", data=json.dumps(body).encode() if body else None, method=method,
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return 200, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


code, ms = call("GET", "models?pageSize=200")
if code != 200:
    print("Listing models failed:", code, str(ms)[:300]); raise SystemExit
names = [m["name"].split("/")[-1] for m in ms.get("models", []) if "generateContent" in m.get("supportedGenerationMethods", [])
         and "flash" in m["name"] and not re.search(r"image|tts|live|audio|thinking|exp|preview", m["name"])]
print("Flash models on this key:", len(names))
for n in names:
    for search in (False, True):
        body = {"contents": [{"parts": [{"text": "Reply with the word ok."}]}]}
        if search:
            body["tools"] = [{"google_search": {}}]
        code, out = call("POST", f"models/{n}:generateContent", body)
        if code == 200:
            msg = "OK"
        else:
            t = str(out)
            lim = re.findall(r'"quotaId":\s*"([^"]+)"', t)
            msg = f"{code} " + ("limit 0 / not on free tier " if '"quotaValue": "0"' in t or "limit: 0" in t else "") + (lim[0] if lim else t[:120].replace("\n", " "))
        print(f"{n:32s} {'with search' if search else 'plain      '}  {msg}")
