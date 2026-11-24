"""Inspo inbox: Omar drops a TikTok/Instagram link or a video file on Agent HQ (YouTube tab -> Inspo); the server turns it
into a template he can approve. No Claude. Runs every 3 days (run_inspo.sh) and once a day before the Bounce batch (promote).

    python inspo.py run        new items: get video -> Gemini watches it -> build -> test render -> judge vs inspo -> sample
    python inspo.py promote    approved items go live (Bounce code -> auto_templates; fact/Ambient -> board idea)

data/youtube/inspo.json  {"items": [{id, channel, link, file, note, addedAt, status, ...}]}
status: new -> (needs_upload) -> analyzed (Gemini breakdown) -> built (Claude Code, inspo-builder skill: template live + sample) -> done (Omar approved)\n        Server-side building (old flow: ready/approved/live) only with INSPO_SERVER_BUILD=1.
Kinds Gemini can recognise: physics (new Bounce code template on engine2), fact (narrated what-if: fact_what_if spec),
ambient (Ambient Escape format: production notes become a board idea; the Ambient engine renders from footage).
"""
import os, re, sys, ast, json, glob, time, shutil, datetime, subprocess
from zoneinfo import ZoneInfo
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini as G

HQ = os.environ.get("AGENT_HQ") or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
YT = os.path.join(HQ, "data", "youtube")
INBOX = os.path.join(YT, "inspo.json")
AUTO = os.path.join(YT, "auto_templates")
BUILDS = os.path.join(YT, "inspo_builds")
SAMPLES = os.path.join(YT, "inspo_samples")
WORK = os.path.expanduser("~/inspo-work")
PY = os.environ.get("BOUNCE_PY") or sys.executable
TZ = ZoneInfo("America/Toronto")
NOW = datetime.datetime.now(TZ).isoformat(timespec="seconds")
MAX_ITEMS, TRIES = 4, 4
SITE = "https://omarjaradat2006-sudo.github.io/agent-hq/"
RAW = "https://raw.githubusercontent.com/omarjaradat2006-sudo/agent-hq/main/"
ALLOWED_IMPORTS = {"auto_bounce2", "engine2", "math", "numpy", "random", "colorsys", "skia", "pymunk", "scipy"}
BANNED = {"open", "exec", "eval", "compile", "__import__", "globals", "locals", "vars", "getattr", "setattr", "delattr", "input",
          "breakpoint", "os", "sys", "subprocess", "shutil", "socket", "pathlib", "importlib", "builtins", "urllib", "requests"}


def say(*a): print(*a, flush=True)
def load(p, d):
    try: return json.load(open(p, encoding="utf-8"))
    except Exception: return d
def save(box): json.dump(box, open(INBOX, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
def sh(cmd, t=600): return subprocess.run(cmd, capture_output=True, text=True, timeout=t)


def probe(path):
    r = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_type,width,height", "-of", "json", path], 60)
    j = json.loads(r.stdout or "{}"); st = j.get("streams", [])
    v = next((s for s in st if s.get("codec_type") == "video"), {})
    return float(j.get("format", {}).get("duration") or 0), v.get("width"), v.get("height"), any(s.get("codec_type") == "audio" for s in st)


def sheet(path, out, n=6, w=180):
    d = probe(path)[0] or 10
    sh(["ffmpeg", "-v", "error", "-y", "-i", path, "-vf", f"fps={n / d},scale={w}:-2,tile={n}x1", "-frames:v", "1", out], 120)
    return out


# ------------------------------------------------------------------ 1. get the video
def fetch(it):
    os.makedirs(WORK, exist_ok=True)
    if it.get("file") and os.path.exists(os.path.join(HQ, it["file"])):
        return os.path.join(HQ, it["file"])
    if not it.get("link"):
        return None
    out = os.path.join(WORK, it["id"] + ".mp4")
    if os.path.exists(out): return out
    r = sh([PY, "-m", "yt_dlp", "-q", "--no-playlist", "-f", "mp4/best", "--merge-output-format", "mp4", "-o", out, it["link"]], 300)
    if r.returncode == 0 and os.path.exists(out): return out
    say("download failed:", (r.stderr or "")[-300:])
    return None


# ------------------------------------------------------------------ 2. Gemini watches it
ANALYZE = """You are breaking down a short-form video so a Python engine can make a NEW video in the same style (never a copy:
no logos, watermarks, names, copyrighted characters or music). Watch it fully, with sound. Return JSON:
{"kind": "physics" | "fact" | "ambient" | "other",
 "name": "snake_case template name, 2-3 words, describes the mechanic",
 "summary": "one line: what happens",
 "physics": "the physics/visual idea and the rule that drives it (what multiplies, breaks, bounces, races...)",
 "hook": "first 2 seconds: what is on screen, any text", "pacing": "how it builds and how it ends (payoff, loop)",
 "colours": "background, objects, palette", "length_s": number, "sound": "what you hear and when",
 "graphics": ["plain list of what the engine must draw, e.g. shaded 3D balls, soft-body sheet, rotating arms, narration voice, illustrations"],
 "buildable": true|false, "why_not": "if not buildable: what is too complex (e.g. hand-drawn illustration, real footage)",
 "spec": "for physics: a precise build spec (objects with sizes in px on a 1080x1920 canvas, rules, forces, win/end condition, on-screen title lines, sound events, 18-38 s). For fact: the narrated idea and its scenes. For ambient: full production notes (footage to look for, audio layers, length, title style)."}
kind physics = a simulation/satisfying physics clip; fact = a narrated science/space/what-if explainer; ambient = sleep/rain/relaxing/Islamic reminder style."""


def analyze(video, it):
    part = G.upload_file(video)
    txt = ANALYZE + (f"\nOmar's note: {it['note']}" if it.get("note") else "") + f"\nChannel he wants it for: {it.get('channel', 'Bounce Theory')}"
    text, _ = G.generate([part, {"text": txt}], json_out=True, temperature=0.3)
    return G.parse_json(text)


# ------------------------------------------------------------------ 3. build (physics -> engine2 code)
API = """ENGINE (from auto_bounce2 import * gives you all of this; nothing else may be imported except math, numpy, random, colorsys):
np, math, skia, pymunk, Delaunay, sparse, E (=engine2), W=1080, H=1920, FPS=60, TAU
Frame() -> fr; fr.clear(rgb_top, rgb_bottom=None); fr.c = skia canvas.   Writer(path, dry) -> V; V.write(fr) (V.write(None) when dry); return V.close(A)
Audio() -> A; A.tone(t, freq, vol, dur, kind) kinds: pluck chime pad thud boing clack crash tick whoosh pop; A.note(t, midi, vol, dur, kind); A.chord(t, root_midi, vol); E.midi(m)
draw_balls(c, xy_list, rgb_list, r, glow=0..1); draw_sprite(c, sphere(rgb_int_tuple), x, y, r) (shaded 3D ball); glow_dot(rgb)
stroke_paint(rgb, width, alpha=255, blur=0); fill_paint(rgb, alpha=255, blur=0, shader=None); polyline(points, close=False) -> skia.Path
draw_text(c, text, x, y, size, rgb, align="center"); title(c, line1, line2=None, y=200, size=78) (white + yellow hook)
hsv(h, s, v) -> rgb; mix(a, b, t); rgb(col, alpha) -> skia.Color.   Colours are RGB tuples of ints.
pymunk: Space, Body (KINEMATIC for moving obstacles: set position + velocity every substep), Circle, Segment, PinJoint; space.on_collision(1, 2, begin=fn(arbiter, space, data))."""

BUILD_RULES = """Write ONE complete Python module. Rules (code that breaks one is rejected automatically):
- First line exactly: from auto_bounce2 import *   (np, math, skia, pymunk, E and every helper below are already imported by it). Extra imports allowed: math, numpy, random, colorsys, skia, pymunk, scipy. No files, network, eval/exec, getattr/setattr, os/sys.
- Define exactly one public function  {name}(path, seed=1, text=True, dry=False, <knobs with defaults>)  that renders a 1080x1920 60 fps Short and returns its length in seconds (return V.close(A)). Helpers start with _.
- dry=True: run the same physics/timing but don't draw (V.write(None)); must return the same length.
- 18-38 s. Frame 1 already moving with the hook title on screen (title(c, l1, l2)). Keep text and action between y=120 and y=1450.
- Sound on every important event (bounce/hit/split/break), a payoff (crash/chord) at the end, a ~2 s payoff card, last frame close to the first (loop).
- Make the look rich like the example: shaded 3D balls (sphere/draw_balls), glow, soft shadows, near-black background, saturated colours.
- Knobs: expose 5-10 settings the YouTube team can vary (counts, sizes, colours as hue floats or palettes, speeds, l1/l2 text).
- Use pymunk for collisions when many bodies touch; numpy for fields/sheets. Keep it fast: under 3 minutes to render on 2 CPU cores."""


def build_code(a, name, feedback):
    ex = open(os.path.join(AUTO, "auto_bounce2.py"), encoding="utf-8").read()
    ex = ex[:ex.index("# ====================================================================== 4.")] if "# ======" in ex else ex[:30000]
    p = (f"Build a new Bounce Theory template from this breakdown of an inspiration video:\n{json.dumps(a, ensure_ascii=False)[:6000]}\n\n"
         f"{API}\n\n{BUILD_RULES.replace('{name}', name)}\n\nEXAMPLE MODULE (same engine; copy its quality, not its idea):\n```python\n{ex[:28000]}\n```\n"
         + (f"\nYOUR LAST TRY FAILED. Fix exactly this:\n{feedback}\n" if feedback else "")
         + "\nReply with ONE ```python code block only.")
    text, _ = G.generate(p, temperature=0.4)
    m = re.search(r"```python\n(.*?)```", text, re.S)
    return (m.group(1) if m else text).strip() + "\n"


def safe(code, name):
    try: tree = ast.parse(code)
    except SyntaxError as e: return f"syntax error: {e}"
    if not code.startswith("from auto_bounce2 import *"): return "first line must be: from auto_bounce2 import *"
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.split(".")[0] not in ALLOWED_IMPORTS: return f"import not allowed: {a.name}"
        if isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[0] not in ALLOWED_IMPORTS: return f"import not allowed: {n.module}"
        if isinstance(n, ast.Name) and n.id in BANNED: return f"not allowed: {n.id}"
        if isinstance(n, ast.Attribute) and n.attr.startswith("__"): return f"not allowed: .{n.attr}"
    fns = [n.name for n in tree.body if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]
    if fns != [name]: return f"module must define exactly one public function named {name} (found {fns})"
    return None


RUNNER = """import sys, json, time
sys.path[:0] = [sys.argv[1], sys.argv[2]]
m = __import__(sys.argv[3]); fn = getattr(m, sys.argv[4])
t = time.time(); d = fn(sys.argv[5], 1); r = time.time() - t
dd = fn(None, 1, dry=True)
print("RESULT " + json.dumps({"secs": d, "dry": dd, "render_s": r}))
"""


def test(code, name, it):
    d = os.path.join(WORK, it["id"]); os.makedirs(d, exist_ok=True)
    mod = f"auto_inspo_{name}"; open(os.path.join(d, mod + ".py"), "w").write(code)
    open(os.path.join(d, "_run.py"), "w").write(RUNNER.replace("getattr(m, sys.argv[4])", "m.__dict__[sys.argv[4]]"))
    out = os.path.join(d, "test.mp4")
    try:
        r = sh([PY, os.path.join(d, "_run.py"), d, AUTO, mod, name, out], 900)
    except subprocess.TimeoutExpired:
        return None, "render took over 15 minutes: make it much faster (fewer bodies, fewer substeps)"
    res = next((json.loads(l[7:]) for l in r.stdout.splitlines() if l.startswith("RESULT ")), None)
    if not res or not os.path.exists(out):
        tb = (r.stderr or r.stdout or "").strip().splitlines()
        return None, "it crashed. End of the error:\n" + "\n".join(tb[-12:])[-1500:]
    dur, w, h, aud = probe(out)
    if (w, h) != (1080, 1920): return None, f"video is {w}x{h}, must be 1080x1920"
    if not aud: return None, "no audio"
    if not 12 <= dur <= 40: return None, f"length {dur:.1f} s, must be 18-38 s"
    if abs((res.get("dry") or 0) - dur) > max(2.0, dur * 0.15): return None, f"dry run says {res.get('dry')} s but the video is {dur:.1f} s: dry must follow the same timing"
    # not black, actually moving
    import numpy as np
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", out, "-vf", "fps=2,scale=108:192,format=gray", "-f", "rawvideo", "-"], capture_output=True, timeout=120).stdout
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 192, 108).astype(float)
    if fr.mean() < 6: return None, "video is almost black"
    if len(fr) > 2 and np.abs(np.diff(fr, axis=0)).mean() < 0.4: return None, "almost nothing moves"
    return out, None


JUDGE = """Top strip: frames from Omar's INSPIRATION video. Bottom strip: frames from the NEW video our engine made.
Breakdown of the inspiration: {a}
Score 1-10 how well the new video captures the same idea, mechanic, look and energy (not a copy: same style is the goal).
6+ means good enough to show Omar. Return JSON {{"score": n, "good": "...", "missing": "what to change, concrete (sizes, colours, motion, text, timing)"}}"""


def judge(inspo, test_mp4, a, it):
    d = os.path.join(WORK, it["id"])
    a1, a2, both = sheet(inspo, os.path.join(d, "s1.jpg")), sheet(test_mp4, os.path.join(d, "s2.jpg")), os.path.join(d, "both.jpg")
    sh(["ffmpeg", "-v", "error", "-y", "-i", a1, "-i", a2, "-filter_complex", "[0]scale=1080:-2[a];[1]scale=1080:-2[b];[a][b]vstack", both], 60)
    if not os.path.exists(both): both = a2
    text, _ = G.generate([G.image_part(both), {"text": JUDGE.format(a=json.dumps(a, ensure_ascii=False)[:3000])}], json_out=True, temperature=0.2)
    j = G.parse_json(text) or {}
    return float(j.get("score") or 0), j


def publish_sample(src, it):
    os.makedirs(SAMPLES, exist_ok=True); out = os.path.join(SAMPLES, it["id"] + ".mp4")
    sh(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", "scale=540:-2", "-c:v", "libx264", "-preset", "veryfast", "-crf", "30",
        "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", out], 300)
    return os.path.relpath(out, HQ)


def build_prompt(it, a, name, problem):
    src = it.get("link") or (RAW + it["file"] if it.get("file") else "")
    return f"""Use the bounce-theory-videos skill. Build a NEW Bounce Theory template from an inspiration video, better than the server's try.

Inspiration: {src}
Omar's note: {it.get('note') or '-'}
Server's breakdown (Gemini watched it): {json.dumps(a, ensure_ascii=False)[:5000]}
Server's try: {('data/youtube/inspo_builds/auto_inspo_' + name + '.py') if name else 'none'}  ({problem or 'Omar rejected it'})

Do this:
1. git clone https://github.com/omarjaradat2006-sudo/agent-hq and read data/youtube/auto_templates/engine2.py + auto_bounce2.py (Engine 2: Skia drawing, pymunk physics, Kokoro voice). Download the inspiration and look at it frame by frame (contact sheets).
2. Write data/youtube/auto_templates/auto_inspo_{name or 'new'}.py: first line `from auto_bounce2 import *`, one public function (path, seed=1, text=True, dry=False, **knobs) returning seconds, 18-38 s, 1080x1920 60 fps, hook title on frame 1, sound on every event, payoff + loop, 5-10 knobs. dry=True must give the same length.
3. Render it, check it (ffprobe + contact sheet vs the inspiration), fix until it really matches the style.
4. In data/youtube/inspo.json set item {it['id']} to "status": "live", "template": "<function name>". Commit and push to main.
The server's daily Bounce run smoke-tests it and adds it to the template menu."""


# ------------------------------------------------------------------ fact videos -> fact_what_if spec
def build_fact(a, it):
    sys.path.insert(0, AUTO)
    import facts
    p = (f"Write a NEW narrated 'what if' Short in the style of this inspiration (a different topic, same energy):\n{json.dumps(a, ensure_ascii=False)[:4000]}\n\n"
         f"{facts.SPEC_GUIDE}\nOnly real textbook numbers. Return the JSON spec only.")
    text, _ = G.generate(p, json_out=True, temperature=0.6)
    spec = G.parse_json(text)
    d = os.path.join(WORK, it["id"]); os.makedirs(d, exist_ok=True); out = os.path.join(d, "test.mp4")
    open(os.path.join(d, "spec.json"), "w").write(json.dumps(spec))
    r = sh([PY, "-c", f"import sys,json;sys.path.insert(0,{AUTO!r});import facts;print(facts.fact_short({out!r}, json.load(open({os.path.join(d, 'spec.json')!r}))))"], 900)
    if r.returncode or not os.path.exists(out): return None, spec, "fact render failed: " + r.stderr[-800:]
    return out, spec, None


# ------------------------------------------------------------------ run / promote
def run():
    box = load(INBOX, {"items": []}); todo = [i for i in box["items"] if i.get("status") in ("new", None)][:MAX_ITEMS]
    say(f"inspo: {len(todo)} new item(s)")
    for it in todo:
        it["status"] = "building"; it["startedAt"] = NOW
        try:
            v = fetch(it)
            if not v:
                it.update(status="needs_upload", error="The server couldn't download that link (TikTok/Instagram block servers). Upload the video file instead."); continue
            a = analyze(v, it) or {}; it["analysis"] = a
            it["graphics"] = a.get("graphics") or []
            kind = a.get("kind")
            if os.environ.get("INSPO_SERVER_BUILD") != "1":   # Omar's choice: Claude Code builds (inspo-builder skill); the server only watches + breaks down
                it.update(status="analyzed", kind=kind, explain=a.get("summary")); continue
            if kind == "ambient" or it.get("channel") == "Ambient Escape":
                it.update(status="ready", kind="ambient", explain="Ambient Escape format: the server will make it from free footage + audio layers using these production notes (no sample until the daily Ambient run).")
                continue
            if kind == "fact":
                out, spec, err = build_fact(a, it)
                if err: it.update(status="failed", error=err, buildPrompt=build_prompt(it, a, None, err)); continue
                it.update(status="ready", kind="fact", spec=spec, sample=publish_sample(out, it), template="fact_what_if",
                          explain="Narrated what-if Short on the fact_what_if template (AI voice + word captions). Approve and the YouTube team writes new facts in this style.")
                continue
            if not a.get("buildable", True):
                it.update(status="failed", error="Too complex for the engine: " + str(a.get("why_not", "")), buildPrompt=build_prompt(it, a, None, a.get("why_not")))
                continue
            name = re.sub(r"[^a-z0-9_]", "", str(a.get("name") or "inspo").lower().replace(" ", "_"))[:28].strip("_") or "inspo"
            menu = load(os.path.join(YT, "bounce_templates.json"), {}).get("templates", {})
            while name in menu or os.path.exists(os.path.join(BUILDS, f"auto_inspo_{name}.py")): name += "2"
            feedback, best = None, (0, None, None, None)
            for k in range(TRIES):
                code = build_code(a, name, feedback)
                err = safe(code, name)
                if err: feedback = err; say("try", k + 1, "rejected:", err); continue
                out, err = test(code, name, it)
                if err: feedback = err; say("try", k + 1, "test failed:", err[:200]); continue
                score, j = judge(v, out, a, it); say("try", k + 1, "score", score)
                if score > best[0]: best = (score, code, out, j)
                if score >= 6: break
                feedback = f"It works but doesn't match the inspiration well enough (score {score}/10). Change: {j.get('missing')}"
            if not best[1]:
                it.update(status="failed", error=feedback, buildPrompt=build_prompt(it, a, None, feedback)); continue
            os.makedirs(BUILDS, exist_ok=True); open(os.path.join(BUILDS, f"auto_inspo_{name}.py"), "w").write(best[1])
            it.update(status="ready", kind="physics", template=name, score=best[0], judge=best[3], sample=publish_sample(best[2], it),
                      explain=f"New Engine 2 template '{name}': " + ", ".join(it["graphics"][:6]),
                      buildPrompt=build_prompt(it, a, name, f"server score {best[0]}/10: {best[3].get('missing')}"))
        except Exception as e:
            it.update(status="failed", error=f"{type(e).__name__}: {str(e)[:400]}")
        finally:
            it["updatedAt"] = NOW; save(box)
    save(box)


def promote():
    box = load(INBOX, {"items": []}); st_p = os.path.join(YT, "state.json"); st = load(st_p, None); n = 0
    for it in box["items"]:
        if it.get("status") != "approved": continue
        if it.get("kind") == "physics":
            src = os.path.join(BUILDS, f"auto_inspo_{it['template']}.py")
            if not os.path.exists(src): continue
            shutil.copy(src, os.path.join(AUTO, os.path.basename(src)))
        elif st is not None:   # fact + ambient: a board idea the lineup uses first (ideas-first rule)
            a = it.get("analysis") or {}
            idea = {"id": f"youtube-inspo-{it['id']}", "title": ("Ambient Escape: " if it.get("kind") == "ambient" else "Bounce Theory: ") + str(a.get("summary") or "Inspo idea")[:90],
                    "status": "approved", "format": "Ambient Escape · inspo" if it.get("kind") == "ambient" else "Bounce Theory · fact_what_if",
                    "channel": "Ambient Escape" if it.get("kind") == "ambient" else "Bounce Theory", "hook": a.get("hook"), "createdAt": NOW, "madeBy": "inspo",
                    "script": (a.get("spec") if it.get("kind") == "ambient" else "Use template fact_what_if with spec_json in this style (new topic each time): " + json.dumps(it.get("spec"), ensure_ascii=False))[:6000]}
            if not any(i.get("id") == idea["id"] for i in st.get("ideas", [])): st.setdefault("ideas", []).append(idea)
        it.update(status="live", liveAt=NOW); n += 1
    if n:
        save(box)
        if st is not None: json.dump(st, open(st_p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    say(f"inspo promote: {n} item(s) live")


if __name__ == "__main__":
    {"run": run, "promote": promote}[sys.argv[1]]()
