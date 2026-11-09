"""explainer2.py - Ambient Escape animated Islamic explainer Shorts, v2 (illustrated). Omar approved 2026-11-08.

Look: flat-illustration scenes that fill the whole 9:16, faceless characters with real poses (art.py),
fixed safe zones and one font family, Poppins (textkit.py), slow camera push-ins, pose changes,
word-by-word captions, 0.4 s cross-fades.  Sound: Kokoro narration ONLY + tiny sound effects
(pops, send swoosh, scene whoosh). NO background bed, NO music, NO tones, NO echo (Omar's rules).

VOICE: one male Kokoro voice per video, a DIFFERENT voice for every video. voice_for() rotates the
13 male voices so the day's explainers never repeat a voice and the start shifts every day.
Calm treatment (WARM): near-natural pitch, light low end, soft highs, gentle compression.

From a job file (render.py contract):
    import explainer2 as X2
    ("SHORT 01 - POV ... .mp4", lambda p: X2.make(p, SPEC_1, index=0))   # index = 0..7, k-th explainer today
SPEC = dict(accent=X2.SKY or X2.T.GOLD, scenes=[ ...scene dicts... ])   # voice=... only to force one
Scene dict keys:
    scene   one of SCENES (see scenes.py): living_room | phone (mode chat|type|delete_send) | reveal |
            street_walk | market (mode hook|word) | neighbors (mode smile|evening) | park | sunset
    label   small caps line above the title ("POV", "01 / 04", "The Prophet ﷺ told us")
    title   one *keyword* in stars (gold/sky + underline);  title_size (default 60)
    arabic  short Arabic line under the title (list points)
    source  "Sahih al-Bukhari 2442 · Sahih Muslim 2580" (shown in the source pill)
    lines   [dict(t="caption with *keyword*", say="what Kokoro reads", pre=extra pause before)]
    reveal  (reveal scene) [dict(ar="...", en="gloss", at=(line_index, fraction), kw=True)]
    tail / min / min_after_last   timing padding (seconds)
    scene text: bubble="..." (living_room, market word), chat=[(name, msg, "#hex")], chat_name, chat_members,
                draft="typed text", reply="sent reply" (phone modes)
New situations: add a scene function to scenes.py (same flat style, action inside y 450-1140, foreground
below y 1460 only, register it in SCENES) - never draw prophets, angels or faces.

CLI:  python explainer2.py render S01 S03     (the two approved samples)
      python explainer2.py stills S01 2 10 20 (check frames)
Needs: pip install pycairo kokoro-onnx soundfile opencv-python pillow numpy ; ffmpeg on PATH.
Kokoro model: KOKORO_DIR, else ./kokoro, else _system/assets/tools (laptop), else downloaded.
"""
import os, sys, json, math, subprocess
import numpy as np
import cairo
import soundfile as sf

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import art as A
import scenes as SC
import textkit as T

W, H, FPS, SR = 1080, 1920, 30, 24000
HERE = os.path.dirname(os.path.abspath(__file__))
KOK = os.environ.get("KOKORO_DIR", next((d for d in (os.path.join(HERE, "kokoro"), os.path.join(HERE, "..", "..", "..", "assets", "tools"))
                                         if os.path.exists(os.path.join(d, "voices-v1.0.bin"))), os.path.join(HERE, "kokoro")))
OUT = os.environ.get("OUT_DIR", os.path.join(HERE, "out"))
SPEED = 0.9
# every male Kokoro voice; each video gets ONE voice, and the voice changes from video to video
VOICES = ["am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael", "am_onyx", "am_puck", "am_santa",
          "bm_daniel", "bm_fable", "bm_george", "bm_lewis"]
WARM = ("asetrate=24000*0.98,aresample=24000,atempo=1.0204,highpass=f=70,equalizer=f=160:t=q:w=1:g=1.5,"
        "equalizer=f=3500:t=q:w=1.2:g=-2,equalizer=f=7500:t=q:w=1:g=-2.5,"
        "acompressor=threshold=-20dB:ratio=2.5:attack=8:release=120")   # calm, natural pitch, no echo


def voice_for(tag, day=None, index=None):
    """One voice per video, a different voice for every video.
    index = the video's position among the day's explainers (0, 1, 2...), so the day's videos
    never repeat a voice (13 voices > 8 explainers); the starting voice moves on every day.
    A spec can force a voice with voice=..."""
    import datetime, re as _re
    v = VIDEOS.get(tag, {})
    if v.get("voice"):
        return v["voice"]
    day = day or datetime.date.today().toordinal()
    if index is None:
        nums = sorted(int((_re.findall(r"\d+", k) or ["0"])[0]) for k in VIDEOS)
        index = nums.index(int((_re.findall(r"\d+", tag) or ["0"])[0]))
    return VOICES[(day * 8 + index) % len(VOICES)]


XFADE = 0.4
SKY = (156, 200, 240)

VIDEOS = {
 "S01": dict(
  file="SHORT 01 - POV your friend tells you his secret (v2).mp4", accent=SKY, voice="bm_george",
  scenes=[
   dict(scene="living_room", label="POV", title="Your friend trusts you with his *secret*",
        lines=[dict(t="POV: your friend trusts you with his *secret*.", say="P.O.V. Your friend trusts you with his secret."),
               dict(t="He leans in and whispers: “Don't tell *anyone*.”", say="He leans in, and whispers. Don't tell anyone.", pre=0.2)],
        tail=1.0),
   dict(scene="phone", mode="chat", label="POV", title="Later, the group chat *asks*",
        lines=[dict(t="Later, the group chat asks what's *wrong* with him.", say="Later, the group chat asks what's wrong with him.")],
        min=3.4),
   dict(scene="phone", mode="type", label="POV", title="One message could *expose* him",
        lines=[dict(t="You could expose him with *one message*.", say="And you could expose him, with one message.")],
        min=3.0),
   dict(scene="reveal", label="The Prophet ﷺ told us",
        source="Sahih al-Bukhari 2442 · Sahih Muslim 2580",
        lines=[dict(t="But the Prophet ﷺ told us, in meaning:", say="But the Prophet, peace be upon him, told us, in meaning,"),
               dict(t="whoever *covers* a Muslim,", say="whoever covers a Muslim,"),
               dict(t="Allah will cover him on the *Day of Resurrection*.", say="Allah will cover him, on the Day of Resurrection.")],
        reveal=[dict(ar="وَمَنْ سَتَرَ مُسْلِمًا", en="whoever covers a Muslim", at=(1, 0.0)),
                dict(ar="سَتَرَهُ اللَّهُ", en="Allah will cover him", at=(2, 0.0), kw=True),
                dict(ar="يَوْمَ الْقِيَامَةِ", en="on the Day of Resurrection", at=(2, 0.5))],
        tail=1.0),
   dict(scene="phone", mode="delete_send", label="POV", title="Keep it *covered*",
        lines=[dict(t="Keep it *covered*.", say="So keep it covered."),
               dict(t="And Allah will cover *you*.", say="And Allah will cover you.", pre=1.3)],
        tail=0.9),
   dict(scene="street_walk",
        lines=[dict(t="Send this to a friend who keeps your *secrets*.", say="Send this to a friend who keeps your secrets.")],
        tail=1.4),
  ]),
 "S03": dict(
  file="SHORT 03 - 4 free ways to give charity every day (v2).mp4", accent=T.GOLD, voice="am_onyx",
  scenes=[
   dict(scene="market", mode="hook", title="4 free ways to give *charity* every day", title_size=68,
        lines=[dict(t="4 free ways to give *charity*, every single day.", say="Four free ways to give charity, every single day.")],
        min=3.6),
   dict(scene="market", mode="word", label="01 / 04", title="A good *word*", arabic="وَالْكَلِمَةُ الطَّيِّبَةُ صَدَقَةٌ",
        source="Sahih al-Bukhari 2989 · Sahih Muslim 1009",
        lines=[dict(t="One: a good *word*.", say="One. A good word."),
               dict(t="The Prophet ﷺ told us a good word is *charity*.", say="The Prophet, peace be upon him, told us that a good word is charity.", pre=0.5)],
        tail=0.9),
   dict(scene="neighbors", mode="smile", label="02 / 04", title="A *smile*", arabic="تَبَسُّمُكَ فِي وَجْهِ أَخِيكَ لَكَ صَدَقَةٌ",
        source="Jami at-Tirmidhi 1956",
        lines=[dict(t="Two: a *smile*.", say="Two. A smile."),
               dict(t="Smiling in your brother's face is *charity* for you.", say="Smiling in your brother's face, is charity for you.", pre=0.6)],
        tail=1.0),
   dict(scene="park", label="03 / 04", title="Remove *harm*", arabic="وَيُمِيطُ الأَذَى عَنِ الطَّرِيقِ صَدَقَةٌ",
        source="Sahih al-Bukhari 2989 · Sahih Muslim 1009",
        lines=[dict(t="Three: remove *harm*.", say="Three. Remove harm."),
               dict(t="Moving something harmful off the road is *charity*.", say="Moving something harmful off the road, is charity.", pre=0.3)],
        min_after_last=4.3),
   dict(scene="sunset", label="04 / 04", title="Say *SubhanAllah*", arabic="فَكُلُّ تَسْبِيحَةٍ صَدَقَةٌ",
        source="Sahih Muslim 720",
        lines=[dict(t="Four: say *SubhanAllah*.", say="Four. Say, Subhaan Allah."),
               dict(t="Every SubhanAllah you say is *charity*.", say="Every Subhaan Allah you say, is charity.", pre=0.2)],
        tail=1.0),
   dict(scene="neighbors", mode="evening",
        lines=[dict(t="You don't need *money* to give.", say="You don't need money to give."),
               dict(t="Start with a *smile*.", say="Start with a smile."),
               dict(t="Send this to a friend who thinks he has *nothing* to give.", say="Send this to a friend who thinks he has nothing to give.")],
        tail=1.4),
  ]),
}


# ------------------------------------------------------------------ narration
_k = None


def _ensure_kokoro():
    global KOK
    if os.path.exists(os.path.join(KOK, "voices-v1.0.bin")):
        return
    import urllib.request
    KOK = os.path.join(HERE, "kokoro")
    os.makedirs(KOK, exist_ok=True)
    base = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
    for f in ("kokoro-v1.0.int8.onnx", "voices-v1.0.bin"):
        if not os.path.exists(os.path.join(KOK, f)):
            urllib.request.urlretrieve(base + f, os.path.join(KOK, f))


def tts(text, path, voice):
    global _k
    if os.path.exists(path):
        return
    if _k is None:
        from kokoro_onnx import Kokoro
        _ensure_kokoro()
        _k = Kokoro(os.path.join(KOK, "kokoro-v1.0.int8.onnx"), os.path.join(KOK, "voices-v1.0.bin"))
    a, sr = _k.create(text, voice=voice, speed=SPEED, lang="en-gb" if voice.startswith("b") else "en-us")
    a = np.asarray(a, np.float32)
    loud = np.where(np.abs(a) > 0.01)[0]
    if len(loud):
        a = a[max(0, loud[0] - 500): loud[-1] + 2400]
    raw = path + ".raw.wav"
    sf.write(raw, a, sr)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", WARM, "-ar", str(SR), "-ac", "1", path], check=True)
    os.remove(raw)


def timeline(tag):
    v = VIDEOS[tag]
    voice = voice_for(tag)
    d = os.path.join(OUT, "tts3", tag, voice)
    os.makedirs(d, exist_ok=True)
    t = 0.0
    out = []
    for si, s in enumerate(v["scenes"]):
        S = dict(s)
        S["start"] = t
        lt = 0.25 if si == 0 else 0.45
        lines, cues = [], []
        for li, ln in enumerate(s["lines"]):
            p = os.path.join(d, f"{si:02d}_{li:02d}.wav")
            tts(ln.get("say") or ln["t"].replace("*", ""), p, voice)
            dur = sf.info(p).duration
            lt += ln.get("pre", 0.0)
            lines.append(dict(text=ln["t"], wav=p, start=lt, dur=dur))
            cues.append(lt)
            lt += dur + 0.28
        end = lt + s.get("tail", 0.45)
        if "min" in s:
            end = max(end, s["min"])
        if "min_after_last" in s:
            end = max(end, cues[-1] + s["min_after_last"])
        S["lines"], S["cues"], S["dur"] = lines, cues, end
        if "reveal" in s:
            rv = []
            for r in s["reveal"]:
                li, frac = r["at"]
                rv.append(dict(r, t=lines[li]["start"] + lines[li]["dur"] * frac))
            S["reveal"] = rv
        S["voice"] = voice
        S["sfx"] = sfx_events(S)
        out.append(S)
        t += end
    return out, t


def sfx_events(S):
    """sound effects that follow the action (scene-relative times). No bells, chimes or music."""
    ev, c = [], S["cues"]
    sc, mode = S["scene"], S.get("mode")
    if sc == "phone" and mode == "chat":
        ev += [(c[0] + 0.15 + i * 0.75, "pop") for i in range(3)]
    if sc == "phone" and mode == "delete_send":
        ev += [(c[1] + 0.1, "send")]
    if sc == "living_room":
        ev += [(c[1] + 0.35, "pop")]
    if sc == "market" and mode == "word":
        ev += [(c[1] - 0.2, "pop")]
    return ev


# ------------------------------------------------------------------ frame
def draw_art(S, t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    cr = cairo.Context(surf)
    cr.set_source_rgb(0, 0, 0)
    cr.paint()
    # slow camera push-in toward the action
    u = A.clamp(t / max(S["dur"], 0.1))
    z = 1.0 + 0.055 * A.ease(u)
    fx, fy = S.get("focus", (540, 830))
    cr.save()
    cr.translate(fx, fy)
    cr.scale(z, z)
    cr.translate(-fx, -fy)
    SC.SCENES[S["scene"]](cr, max(0.0, t), S)
    cr.restore()
    # scrims under the title and caption zones (full-frame art stays visible)
    g = cairo.LinearGradient(0, 0, 0, 620)
    g.add_color_stop_rgba(0, 0, 0, 0, 0.55)
    g.add_color_stop_rgba(0.55, 0, 0, 0, 0.25)
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    cr.set_source(g)
    cr.rectangle(0, 0, W, 620)
    cr.fill()
    g = cairo.LinearGradient(0, 1090, 0, H)
    g.add_color_stop_rgba(0, 0, 0, 0, 0)
    g.add_color_stop_rgba(0.09, 0, 0, 0, 0.42)
    g.add_color_stop_rgba(0.42, 0, 0, 0, 0.55)
    g.add_color_stop_rgba(0.62, 0, 0, 0, 0.3)
    g.add_color_stop_rgba(1, 0, 0, 0, 0.2)
    cr.set_source(g)
    cr.rectangle(0, 1090, W, H - 1090)
    cr.fill()
    a = np.ndarray((H, W, 4), np.uint8, surf.get_data())
    return a[..., [2, 1, 0]].astype(np.float32)


def draw_frame(S, t, ov):
    f = draw_art(S, t)
    ov.title(f, S, t)
    ov.reveal(f, S, t)
    cur, nxt = None, None
    for i, ln in enumerate(S["lines"]):
        if t >= ln["start"] - 0.08:
            cur = ln
            nxt = S["lines"][i + 1]["start"] - 0.08 if i + 1 < len(S["lines"]) else S["dur"] + 0.3
    if cur:
        ov.caption(f, cur, t, nxt)
    ov.source(f, S, t)
    return f


def frame_at(scenes, T_, ov):
    for i, S in enumerate(scenes):
        if S["start"] <= T_ < S["start"] + S["dur"] or i == len(scenes) - 1:
            break
    t = T_ - S["start"]
    f = draw_frame(S, t, ov)
    # cross-fade into the next scene
    if i + 1 < len(scenes):
        rem = S["dur"] - t
        if rem < XFADE / 2:
            N = scenes[i + 1]
            k = A.ease((XFADE / 2 - rem) / XFADE)
            f = f * (1 - k) + draw_frame(N, -rem, ov) * k
    if i > 0 and t < XFADE / 2:
        Pv = scenes[i - 1]
        k = A.ease((XFADE / 2 + t) / XFADE)
        f = draw_frame(Pv, Pv["dur"] + t, ov) * (1 - k) + f * k
    return f


# ------------------------------------------------------------------ audio
def mix_audio(scenes, total, path):
    n = int((total + 1) * SR)
    voice = np.zeros(n, np.float32)
    for S in scenes:
        for ln in S["lines"]:
            a, _ = sf.read(ln["wav"], dtype="float32")
            i = int((S["start"] + ln["start"]) * SR)
            voice[i:i + len(a)] += a[:max(0, n - i)]
    rng = np.random.default_rng(3)
    bed = np.zeros(n, np.float32)     # no background: voice + sound effects only
    # soft whoosh at every scene change
    for S in scenes[1:]:
        c = int(S["start"] * SR)
        L = int(0.6 * SR)
        i0 = max(0, c - L // 2)
        env = np.sin(np.linspace(0, np.pi, L)) ** 2
        seg_ = np.convolve(rng.standard_normal(L).astype(np.float32), np.ones(25) / 25, "same") * env
        voice[i0:i0 + L] += 0.05 * seg_[: n - i0]
    # sound effects
    for S in scenes:
        for te, kind in S.get("sfx", []):
            i0 = int((S["start"] + te) * SR)
            if 0 <= i0 < n:
                fx = SFX(kind, rng)
                voice[i0:i0 + len(fx)] += fx[: n - i0]
    out = voice + bed
    fl = int(0.5 * SR)
    out[:fl] *= np.linspace(0, 1, fl)
    out[int(total * SR) - SR:int(total * SR)] *= np.linspace(1, 0, SR)
    sf.write(path, out[: int(total * SR)], SR)


def SFX(kind, rng):
    if kind == "pop":        # soft water-drop pop (message / speech bubble)
        L = int(0.12 * SR); tt = np.arange(L) / SR
        f = 900 * np.exp(-tt * 28) + 380
        return (0.22 * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-tt * 38)).astype(np.float32)
    if kind == "send":       # quick upward swoosh
        L = int(0.35 * SR); env = np.sin(np.linspace(0, np.pi, L)) ** 3
        nz = np.convolve(rng.standard_normal(L), np.ones(9) / 9, "same")
        return (0.16 * nz * env).astype(np.float32)
    if kind == "swell":      # airy noise swell under each hadith line
        L = int(1.1 * SR); env = np.sin(np.linspace(0, np.pi, L)) ** 2
        nz = np.convolve(rng.standard_normal(L), np.ones(41) / 41, "same")
        return (0.18 * nz / (np.abs(nz).max() + 1e-6) * env).astype(np.float32)
    return np.zeros(1, np.float32)


# ------------------------------------------------------------------ main
def render(tag, out_path=None):
    v = VIDEOS[tag]
    scenes, total = timeline(tag)
    ov = T.Overlay(v["accent"])
    wav = os.path.join(OUT, f"{tag}_mix.wav")
    mix_audio(scenes, total, wav)
    out = out_path or os.path.join(OUT, v["file"])
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
           "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
           "-af", "loudnorm=I=-12.5:TP=-1.2:LRA=9", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-shortest",
           "-movflags", "+faststart", out]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    nfr = int(total * FPS)
    for fi in range(nfr):
        f = frame_at(scenes, fi / FPS, ov)
        pr.stdin.write(np.clip(f, 0, 255).astype(np.uint8).tobytes())
        if fi % 150 == 0:
            print(tag, fi, "/", nfr, flush=True)
    pr.stdin.close()
    pr.wait()
    json.dump([dict(scene=S["scene"], start=round(S["start"], 2), dur=round(S["dur"], 2),
                    lines=[(round(S["start"] + l["start"], 2), l["text"]) for l in S["lines"]]) for S in scenes],
              open(os.path.join(OUT, f"{tag}_timeline.json"), "w"), indent=1, ensure_ascii=False)
    print("DONE", out, round(total, 2), "voice:", scenes[0]["voice"], flush=True)


def make(path, spec, index=None, day=None):
    """Render one explainer to `path` (used by job files). index = position among today's explainers."""
    global OUT
    import shutil
    tag = spec.get("tag") or os.path.splitext(os.path.basename(path))[0]
    v = dict(spec)
    v["file"] = os.path.basename(path)
    v.setdefault("accent", T.GOLD)
    if not v.get("voice"):
        VIDEOS.pop(tag, None)
        v["voice"] = VOICES[((day or __import__("datetime").date.today().toordinal()) * 8 + (index or 0)) % len(VOICES)]
    VIDEOS[tag] = v
    old = OUT
    OUT = os.path.join(os.path.dirname(os.path.abspath(path)), "_explainer2_work")
    os.makedirs(OUT, exist_ok=True)
    try:
        render(tag, out_path=path)
    finally:
        shutil.rmtree(OUT, ignore_errors=True)
        OUT = old
    return path


def stills(tag, times):
    from PIL import Image
    scenes, total = timeline(tag)
    ov = T.Overlay(VIDEOS[tag]["accent"])
    d = os.path.join(OUT, "stills")
    os.makedirs(d, exist_ok=True)
    paths = []
    for tt in times:
        f = frame_at(scenes, float(tt), ov)
        p = os.path.join(d, f"{tag}_{float(tt):05.2f}.png")
        Image.fromarray(np.clip(f, 0, 255).astype(np.uint8)).save(p)
        paths.append(p)
    print(json.dumps([(round(S["start"], 2), round(S["dur"], 2), S["scene"]) for S in scenes]), round(total, 2))
    return paths


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    if sys.argv[1] == "render":
        for tag in sys.argv[2:]:
            render(tag)
    elif sys.argv[1] == "stills":
        stills(sys.argv[2], sys.argv[3:])
