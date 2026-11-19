"""Bounce Engine 2: Skia renderer + pymunk physics helpers + richer synth audio + voiceover mixing.

engine.py is untouched. New templates import this instead. Needs: skia-python, pymunk, numpy, scipy,
(voice) kokoro-onnx + soundfile + the model files in KOKORO_DIR.

Frames are drawn on a 1080x1920 Skia canvas (anti-aliased, gradients, blur glow) wrapped around a numpy
RGBA buffer and piped to ffmpeg. No 80% shrink: layouts keep text/action between y=120 and y=1450 themselves.
"""
import os, math, subprocess, wave, functools, glob
import numpy as np, skia

W, H, FPS, SR = 1080, 1920, 60, 44100
TAU = 2 * math.pi
_HERE = os.path.dirname(os.path.abspath(__file__))


def _find_font(name):
    for d in (os.environ.get("BOUNCE_FONTS", ""), os.path.join(_HERE, "fonts"), os.path.join(_HERE, "..", "Local Render", "fonts"),
              "/usr/share/fonts/truetype/google-fonts", "/usr/share/fonts/truetype", "/usr/share/fonts"):
        if not d: continue
        hits = glob.glob(os.path.join(d, "**", name), recursive=True)
        if hits: return hits[0]
    return None


FONT_B = _find_font("Poppins-Bold.ttf")
FONT_M = _find_font("Poppins-Medium.ttf") or FONT_B
KOKORO_DIR = os.environ.get("KOKORO_DIR") or next((d for d in (os.path.join(_HERE, "kokoro"), os.path.join(_HERE, "..", "assets", "kokoro"),
                                                               os.path.expanduser("~/kokoro")) if os.path.exists(os.path.join(d, "voices-v1.0.bin"))),
                                                   os.path.join(_HERE, "kokoro"))

WHITE = (245, 245, 245); YELLOW = (255, 205, 60); GREY = (170, 170, 185)   # RGB in this engine


def rgb(c, a=255): return skia.Color(int(c[0]), int(c[1]), int(c[2]), int(a))
def mix(a, b, t): return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def hsv(h, s=0.85, v=1.0):
    import colorsys
    r, g, b = colorsys.hsv_to_rgb(h % 1, s, v); return (r * 255, g * 255, b * 255)


# ------------------------------------------------------------------ canvas / writer
class Frame:
    def __init__(self):
        self.buf = np.zeros((H, W, 4), np.uint8); self.surf = skia.Surface(self.buf); self.c = self.surf.getCanvas()

    def clear(self, col, col2=None):
        if col2 is None: self.c.clear(rgb(col)); return
        p = skia.Paint(Shader=skia.GradientShader.MakeLinear([(0, 0), (0, H)], [rgb(col), rgb(col2)]))
        self.c.drawRect(skia.Rect(0, 0, W, H), p)


class Writer:
    def __init__(self, path, dry=False):
        self.path, self.dry, self.n = path, dry, 0
        if dry: return
        self.tmp = path + ".v.mp4"
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{W}x{H}", "-r", str(FPS),
                                   "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", self.tmp],
                                  stdin=subprocess.PIPE)

    def write(self, fr):
        self.n += 1
        if not self.dry: self.p.stdin.write(fr.buf.tobytes())

    def close(self, audio):
        dur = self.n / FPS
        if self.dry: return dur
        self.p.stdin.close(); self.p.wait()
        wav = self.path + ".wav"; audio.render(dur, wav)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", self.tmp, "-i", wav, "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-shortest", "-movflags", "+faststart", self.path], check=True)
        os.remove(self.tmp); os.remove(wav)
        return dur


# ------------------------------------------------------------------ sprites
@functools.lru_cache(maxsize=512)
def sphere(col, size=96, gloss=0.75, rim=0.45):
    """Shaded 3D ball sprite (skia.Image), colour as an RGB tuple of ints."""
    s = skia.Surface(size, size); c = s.getCanvas(); c.clear(skia.Color(0, 0, 0, 0)); r = size / 2
    hi = mix(col, (255, 255, 255), 0.55); lo = mix(col, (0, 0, 0), rim)
    sh = skia.GradientShader.MakeRadial((r * 0.72, r * 0.62), r * 1.45, [rgb(hi), rgb(col), rgb(lo)], [0.0, 0.45, 1.0])
    c.drawCircle(r, r, r - 1, skia.Paint(AntiAlias=True, Shader=sh))
    spec = skia.GradientShader.MakeRadial((r * 0.66, r * 0.55), r * 0.36, [skia.Color(255, 255, 255, int(235 * gloss)), skia.Color(255, 255, 255, 0)])
    c.drawCircle(r * 0.66, r * 0.55, r * 0.36, skia.Paint(AntiAlias=True, Shader=spec))
    return s.makeImageSnapshot()


@functools.lru_cache(maxsize=64)
def glow_dot(col, size=128, a=150):
    s = skia.Surface(size, size); c = s.getCanvas(); c.clear(skia.Color(0, 0, 0, 0)); r = size / 2
    c.drawCircle(r, r, r, skia.Paint(AntiAlias=True, Shader=skia.GradientShader.MakeRadial((r, r), r, [rgb(col, a), rgb(col, 0)])))
    return s.makeImageSnapshot()


_SAMP = skia.SamplingOptions(skia.FilterMode.kLinear)


def draw_sprite(c, img, x, y, r, paint=None):
    c.drawImageRect(img, skia.Rect(x - r, y - r, x + r, y + r), _SAMP, paint)


def draw_balls(c, xy, cols, r, glow=0.0):
    if glow > 0:
        for (x, y), col in zip(xy, cols): draw_sprite(c, glow_dot(col), x, y, r * (1 + 2 * glow))
    for (x, y), col in zip(xy, cols): draw_sprite(c, sphere(col), x, y, r)


def stroke_paint(col, w, a=255, cap=True, blur=0):
    p = skia.Paint(AntiAlias=True, Color=rgb(col, a), Style=skia.Paint.kStroke_Style, StrokeWidth=w)
    if cap: p.setStrokeCap(skia.Paint.kRound_Cap); p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    return p


def fill_paint(col, a=255, blur=0, shader=None):
    p = skia.Paint(AntiAlias=True, Color=rgb(col, a))
    if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if shader is not None: p.setShader(shader)
    return p


def polyline(pts, close=False):
    path = skia.Path(); path.moveTo(*pts[0])
    for q in pts[1:]: path.lineTo(*q)
    if close: path.close()
    return path


# ------------------------------------------------------------------ text
@functools.lru_cache(maxsize=16)
def _font(size, bold=True):
    return skia.Font(skia.Typeface.MakeFromFile(FONT_B if bold else FONT_M), size)


def text_w(t, size, bold=True): return _font(size, bold).measureText(t)


def text(c, t, x, y, size, col=WHITE, stroke=8, align="center", bold=True, shadow=True, a=255, maxw=1000):
    while text_w(t, size, bold) > maxw and size > 24: size -= 2
    f = _font(size, bold); w = f.measureText(t)
    x0 = x - w / 2 if align == "center" else x
    if shadow:
        c.drawString(t, x0 + 4, y + 6, f, fill_paint((0, 0, 0), int(140 * a / 255), blur=6))
    if stroke:
        c.drawString(t, x0, y, f, skia.Paint(AntiAlias=True, Color=rgb((0, 0, 0), a), Style=skia.Paint.kStroke_Style, StrokeWidth=stroke,
                                             StrokeJoin=skia.Paint.kRound_Join))
    c.drawString(t, x0, y, f, fill_paint(col, a))
    return w


def title(c, l1, l2=None, y=200, size=78):
    text(c, l1, W / 2, y, size, WHITE)
    if l2: text(c, l2, W / 2, y + size * 1.15, size, YELLOW)


def word_caption(c, words, active, y=1330, size=74, hi=YELLOW, pop=0.0):
    """Line of words; `active` index gets the highlight colour and a small pop scale."""
    f = _font(size); sp = f.measureText(" ") * 1.5
    ws = [f.measureText(w) for w in words]; tot = sum(ws) + sp * (len(words) - 1)
    if tot > 980:
        return word_caption(c, words, active, y, int(size * 980 / tot), hi, pop)
    x = W / 2 - tot / 2
    for i, (w_, wd) in enumerate(zip(words, ws)):
        col = hi if i == active else WHITE
        if i == active and pop > 0:
            c.save(); c.translate(x + wd / 2, y - size * 0.35); c.scale(1 + pop, 1 + pop); c.translate(-(x + wd / 2), -(y - size * 0.35))
            text(c, w_, x, y, size, col, align="left"); c.restore()
        else:
            text(c, w_, x, y, size, col, align="left")
        x += wd + sp


# ------------------------------------------------------------------ audio
def midi(m): return 440.0 * 2 ** ((m - 69) / 12)


class Audio:
    """Synth events + sample clips. kinds: pluck, chime, pad, thud, crash, tick, whoosh, pop, boing, clack."""
    def __init__(self): self.ev = []; self.clips = []

    def tone(self, t, f, v=0.3, d=0.4, kind="pluck"): self.ev.append((t, f, v, d, kind))
    def note(self, t, m, v=0.3, d=0.5, kind="pluck"): self.tone(t, midi(m), v, d, kind)
    def chord(self, t, root=60, v=0.25, kind="chime"):
        for k, iv in enumerate((0, 4, 7, 12)): self.note(t + k * 0.05, root + iv, v, 1.6, kind)

    def clip(self, t, samples, sr, v=1.0):
        x = np.asarray(samples, np.float32)
        if sr != SR: x = np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x).astype(np.float32)
        self.clips.append((t, x, v))

    def render(self, dur, path):
        n = int(dur * SR) + SR; buf = np.zeros(n, np.float32); rng = np.random.default_rng(3)
        for t, f, v, d, kind in self.ev:
            i0 = int(t * SR); m = min(int(d * SR), n - i0)
            if i0 < 0 or m <= 0: continue
            tt = np.arange(m) / SR
            if kind == "pop":
                s = rng.standard_normal(m) * np.exp(-tt * 45) * 0.5 + np.sin(TAU * 220 * tt) * np.exp(-tt * 30)
            elif kind == "chime":
                env = np.exp(-tt * (4.0 / d)) * np.minimum(1, tt * 800)
                s = (np.sin(TAU * f * tt) + 0.35 * np.sin(TAU * f * 2.76 * tt) * np.exp(-tt * 6) + 0.15 * np.sin(TAU * f * 5.4 * tt) * np.exp(-tt * 14)) * env
            elif kind == "pad":
                env = np.minimum(1, tt / (d * 0.25 + 1e-3)) * np.minimum(1, (d - tt) / (d * 0.3 + 1e-3))
                s = (np.sin(TAU * f * tt) + 0.6 * np.sin(TAU * f * 1.004 * tt + 1) + 0.3 * np.sin(TAU * f * 2.002 * tt)) * env * 0.5
            elif kind == "thud":
                ph = np.cumsum(f * (1 + 2.0 * np.exp(-tt * 35))) / SR
                s = np.sin(TAU * ph) * np.exp(-tt * 10) + rng.standard_normal(m) * np.exp(-tt * 80) * 0.3
            elif kind == "boing":
                ph = np.cumsum(f * (1 + 0.9 * np.exp(-tt * 9)) * (1 + 0.04 * np.sin(TAU * 18 * tt))) / SR
                s = np.sin(TAU * ph) * np.exp(-tt * (5 / d)) * np.minimum(1, tt * 500)
            elif kind == "clack":
                s = (np.sin(TAU * f * tt) + 0.6 * np.sin(TAU * f * 2.3 * tt)) * np.exp(-tt * 70) + rng.standard_normal(m) * np.exp(-tt * 200) * 0.4
            elif kind == "crash":
                nz = np.convolve(rng.standard_normal(m), np.ones(4) / 4, "same")
                s = nz * np.exp(-tt * (3.0 / d)) + np.sin(TAU * 55 * tt) * np.exp(-tt * 4)
            elif kind == "tick":
                s = np.sin(TAU * f * tt) * np.exp(-tt * 300) + rng.standard_normal(m) * np.exp(-tt * 500) * 0.3
            elif kind == "whoosh":
                k = max(3, int(SR / max(f, 50)))
                s = np.convolve(rng.standard_normal(m), np.ones(k) / k, "same") * 4 * np.sin(np.pi * np.clip(tt / d, 0, 1)) ** 2
            else:
                env = np.exp(-tt * (6.0 / d)) * np.minimum(1, tt * 500)
                s = (np.sin(TAU * f * tt) + 0.35 * np.sin(2 * TAU * f * tt) + 0.12 * np.sin(3 * TAU * f * tt)) * env
            buf[i0:i0 + m] += (s * v).astype(np.float32)
        for t, x, v in self.clips:
            i0 = int(t * SR); m = min(len(x), n - i0)
            if m > 0: buf[i0:i0 + m] += x[:m] * v
        buf = np.tanh(buf[:int(dur * SR)] * 1.05) * 0.9
        st = (np.stack([buf, buf], 1) * 32767).astype(np.int16)
        with wave.open(path, "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())


# ------------------------------------------------------------------ voice (Kokoro, free, offline)
_KOK = None


# Words the voice gets wrong -> the sounds (IPA) it should say. Add to pronounce.json next to this file;
# entries there override these. Check any script with: python -c "import engine2; engine2.check_words('...')"
PRONOUNCE = {
    "uranus": "jˈʊɹənəs",          # YUR-uh-nus (Kokoro's default sounds like "your-ANNE-us")
}


def _pron_table():
    p = os.path.join(_HERE, "pronounce.json"); tab = dict(PRONOUNCE)
    if os.path.exists(p):
        import json
        tab.update({k.lower(): v for k, v in json.load(open(p, encoding="utf-8")).items()})
    return tab


def _kok():
    global _KOK
    if _KOK is None:
        from kokoro_onnx import Kokoro
        _KOK = Kokoro(os.path.join(KOKORO_DIR, "kokoro-v1.0.int8.onnx"), os.path.join(KOKORO_DIR, "voices-v1.0.bin"))
    return _KOK


def phonemes(sentence):
    """Sentence -> phoneme string with every PRONOUNCE word swapped for its fixed sounds."""
    import re
    k = _kok(); ph = k.tokenizer.phonemize(sentence, "en-us")
    for word, ipa in _pron_table().items():
        if not re.search(r"\b" + re.escape(word) + r"\b", sentence, re.I): continue
        for form in {word, word.capitalize(), word.upper()}:
            dflt = k.tokenizer.phonemize(form, "en-us").strip(" .?!,")
            if dflt and dflt in ph: ph = ph.replace(dflt, ipa)
    return ph


def check_words(text_):
    """Print how the voice will say each capitalised / long word, to spot bad names before rendering."""
    k = _kok()
    for w in sorted({w.strip(".,?!'\"") for w in text_.split() if w[:1].isupper() or len(w) > 9}):
        print(f"{w:16s} {phonemes(w)}")


def say(sentence, voice="am_michael", speed=1.12):
    """-> (samples float32, sr). Kokoro TTS, runs locally on CPU, with the pronunciation fixes applied."""
    k = _kok()
    a, sr = k.create(phonemes(sentence), voice=voice, speed=speed, lang="en-us", is_phonemes=True)
    a = np.asarray(a, np.float32)
    nz = np.where(np.abs(a) > 0.01)[0]                     # trim silence
    if len(nz): a = a[max(0, nz[0] - int(0.02 * sr)): nz[-1] + int(0.08 * sr)]
    return a, sr


def word_times(words, dur):
    """Rough per-word start times inside one spoken line (by syllable-ish weight)."""
    wts = np.array([max(1.0, len(w.strip(".,?!")) ** 0.8 + (2.5 if w[-1:] in ".,?!" else 0)) for w in words])
    st = np.concatenate([[0], np.cumsum(wts)[:-1]]) / wts.sum() * dur
    return st
