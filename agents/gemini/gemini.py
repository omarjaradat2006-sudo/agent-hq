"""Tiny Gemini API client (stdlib only). Key comes from the GEMINI_API_KEY environment variable."""
import json, os, re, time, urllib.request, urllib.error

BASE = "https://generativelanguage.googleapis.com/v1beta"
KEY = (os.environ.get("GEMINI_API_KEY") or "").strip()
_model = None


def _req(method, path, body=None, timeout=180):
    url = f"{BASE}/{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json", "x-goog-api-key": KEY})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def models():
    """Models to try, best first. GEMINI_MODEL (if set) goes first, then free Flash models
    newest-first, then Flash-Lite. If one is busy (503) or out of free quota (429),
    the next one is used."""
    global _model
    if _model:
        return _model
    pinned = (os.environ.get("GEMINI_MODEL") or "").strip()
    flash, lite = [], []
    try:
        for m in _req("GET", "models?pageSize=200").get("models", []):
            n = m["name"].split("/")[-1]
            if "generateContent" not in m.get("supportedGenerationMethods", []):
                continue
            if "flash" not in n or re.search(r"image|tts|live|audio|thinking|exp|preview|omni", n):  # omni: not on the free tier
                continue
            (lite if "lite" in n else flash).append(n)
    except Exception as e:
        print("Could not list models:", e, flush=True)
    def ver(n):
        v = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
        return float(v.group(1)) if v else 0
    key = lambda n: (ver(n), "latest" not in n)
    flash, lite = sorted(flash, key=key, reverse=True), sorted(lite, key=key, reverse=True)
    order = flash[:4] + lite[:2]          # always keep Flash-Lite as a fallback (separate free quota)
    order += [n for n in flash + lite if n not in order]
    if pinned:
        order = [pinned] + [n for n in order if n != pinned]
    if not order:
        raise RuntimeError("No Gemini Flash model available for this key")
    _model = order[:6]
    print("Gemini models to try:", ", ".join(_model), flush=True)
    return _model


def model():
    return models()[0]


def generate(prompt, system=None, search=False, json_out=False, temperature=0.8, retries=2):
    """Returns (text, sources). sources = [(title, url)] from Google Search grounding.
    Tries each model in models(); on 429/503 moves to the next model."""
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if search:
        body["tools"] = [{"google_search": {}}]
    if json_out and not search:
        body["generationConfig"]["responseMimeType"] = "application/json"
    last = None
    for rnd in range(retries):
        for name in list(models()):
            try:
                r = _req("POST", f"models/{name}:generateContent", body)
                cand = (r.get("candidates") or [{}])[0]
                text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
                meta = cand.get("groundingMetadata") or {}
                sources = [(c["web"].get("title", ""), c["web"].get("uri", ""))
                           for c in meta.get("groundingChunks", []) if "web" in c]
                if not text.strip():
                    raise RuntimeError(f"empty reply: {json.dumps(r)[:300]}")
                if name != models()[0]:
                    print(f"(answered by {name})", flush=True)
                return text, sources
            except urllib.error.HTTPError as e:
                msg = e.read().decode()[:300]
                last = f"Gemini HTTP {e.code} on {name}: {msg}"
                print(f"Gemini {e.code} on {name}, trying next model", flush=True)
                if e.code == 429 and len(_model) > 1:  # out of quota: stop trying it first this run
                    _model.remove(name); _model.append(name)
                if e.code not in (429, 500, 503, 404, 400):
                    raise RuntimeError(last)
            except (urllib.error.URLError, TimeoutError, RuntimeError) as e:
                last = f"{name}: {e}"
                print("Gemini error on", name, "-", str(e)[:150], flush=True)
            time.sleep(4)
        if rnd < retries - 1:
            print("All models busy, waiting 60s", flush=True)
            time.sleep(60)
    raise RuntimeError("All Gemini models failed. Last error: " + str(last))


def parse_json(text):
    """Pull the first JSON object/array out of a reply (handles ```json fences)."""
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"(\{.*\}|\[.*\])", t, re.S)
        if not m:
            raise
        return json.loads(m.group(1))
