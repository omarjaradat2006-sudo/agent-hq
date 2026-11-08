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


def model():
    """GEMINI_MODEL if set, else the newest free Flash text model this key can use."""
    global _model
    if _model:
        return _model
    _model = (os.environ.get("GEMINI_MODEL") or "").strip()
    if not _model:
        names = []
        for m in _req("GET", "models?pageSize=200").get("models", []):
            n = m["name"].split("/")[-1]
            if "generateContent" not in m.get("supportedGenerationMethods", []):
                continue
            if "flash" in n and not re.search(r"lite|image|tts|live|audio|thinking|exp|preview", n):
                names.append(n)
        def ver(n):
            v = re.search(r"gemini-(\d+(?:\.\d+)?)", n)
            return float(v.group(1)) if v else 0
        names.sort(key=lambda n: (ver(n), "latest" not in n), reverse=True)
        if not names:
            raise RuntimeError("No Gemini Flash model available for this key")
        _model = names[0]
    print("Gemini model:", _model, flush=True)
    return _model


def generate(prompt, system=None, search=False, json_out=False, temperature=0.8, retries=4):
    """Returns (text, sources). sources = [(title, url)] from Google Search grounding."""
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    if search:
        body["tools"] = [{"google_search": {}}]
    if json_out and not search:
        body["generationConfig"]["responseMimeType"] = "application/json"
    for attempt in range(retries):
        try:
            r = _req("POST", f"models/{model()}:generateContent", body)
            cand = (r.get("candidates") or [{}])[0]
            text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
            meta = cand.get("groundingMetadata") or {}
            sources = [(c["web"].get("title", ""), c["web"].get("uri", ""))
                       for c in meta.get("groundingChunks", []) if "web" in c]
            if not text.strip():
                raise RuntimeError(f"empty reply: {json.dumps(r)[:300]}")
            return text, sources
        except urllib.error.HTTPError as e:
            msg = e.read().decode()[:400]
            if e.code in (429, 500, 503) and attempt < retries - 1:
                wait = 30 * (attempt + 1)
                print(f"Gemini {e.code}, retrying in {wait}s: {msg[:150]}", flush=True)
                time.sleep(wait)
                continue
            raise RuntimeError(f"Gemini HTTP {e.code}: {msg}")
        except (urllib.error.URLError, TimeoutError, RuntimeError) as e:
            if attempt < retries - 1:
                time.sleep(20)
                continue
            raise


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
