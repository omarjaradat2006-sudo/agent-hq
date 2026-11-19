"""Physics/space fact Shorts from a JSON spec, so the YouTube team (Gemini on the server) can invent NEW facts
instead of copying one video. Engine 2 + Kokoro voice + word-by-word captions.

    fact_short(path, spec)         renders any spec (see SPEC_GUIDE)
    fact_laser_spec(target)        the "8 billion lasers at <planet>" spec (test 4)
    EXAMPLES                       ready specs to copy the style from

Every number in a spec must be computed (python) from real constants, never guessed. PRONOUNCE in engine2 /
pronounce.json fixes names the voice says wrong; run engine2.check_words(all the 'say' lines) before rendering.
"""
import math, json, numpy as np, skia
import engine2 as E
from engine2 import W, H, FPS, TAU, Frame, Writer, Audio, rgb, mix, glow_dot, draw_sprite, sphere, stroke_paint, fill_paint, polyline, word_caption, WHITE, YELLOW, GREY
from engine2 import text as draw_text
from auto_bounce2 import _smooth, _stars, _draw_stars, _planet, _person

C_KM_S = 299_792.458
BODIES = {  # name: (colour RGB, look, relative size for drawing)
    "earth": ((60, 120, 220), "earth", 1.0), "moon": ((205, 205, 210), None, 0.45), "mars": ((225, 95, 60), None, 0.6),
    "jupiter": ((215, 175, 130), "gas", 1.6), "saturn": ((230, 200, 140), "ring", 1.4), "uranus": ((160, 225, 215), "gas", 1.15),
    "neptune": ((70, 120, 230), "gas", 1.1), "sun": ((255, 190, 60), "sun", 2.2), "venus": ((235, 205, 150), None, 0.95),
    "mercury": ((170, 160, 150), None, 0.5), "pluto": ((200, 170, 150), None, 0.35), "star": ((255, 245, 220), "sun", 0.8),
    "blackhole": ((10, 10, 10), "hole", 1.2), "ball": ((255, 90, 90), "ball", 0.5),
}

SPEC_GUIDE = """FACT SHORT SPEC (JSON). 25-45 s, 7-11 lines. Hook line first ("What if...?"), surprising number in the middle,
a twist near the end, a final big-number card. Plain words, short sentences, numbers written as words in "say"
(the screen shows digits). Every number computed from real constants. No copyrighted characters or brands.
{
  "title": "<YouTube title under 70 chars>", "voice": "am_michael", "speed": 1.1,
  "lines": [ {"say": "<spoken sentence>", "scene": "<scene>", ...scene fields}, ... ]
}
Scenes (bodies: earth moon mars venus mercury jupiter saturn uranus neptune pluto sun star blackhole ball):
  crowd    {"b": body}                                  - a crowd raises lasers/arms at body b
  streak   {"big": "300,000 km", "sub": "EVERY SECOND"} - a glowing streak flies past a huge number
  travel   {"a": body, "b": body, "from": 0, "to": 9573, "fmt": "hms"|"{:,.0f} km"|"{:.1f} YEARS"...,
            "back": false}                              - a beam/object goes a->b (or b->a), counter runs from->to
  scale    {"a": body, "b": body, "ratio": 109, "big": "109x WIDER"}  - b grows next to a until ratio is shown
  spread   {"a": body, "b": body, "big": "1,435,000 km wide", "shrink": false} - a beam widens into a cone at b
  counter  {"value": 8000000000, "fmt": "{:,.0f}", "sub": "PEOPLE"}    - a number rolls up
  fall     {"height_m": 1000, "g": 9.81, "b": body}     - a ball drops with a real-physics timer t = sqrt(2h/g)
  orbit    {"a": body, "b": body, "period": "365 DAYS"} - b circles a, label shows the period
  card     {"big": "5h 19m", "sub": "ROUND TRIP"}       - final pop-up card
"""


def _fmt(v, f):
    if f == "hms":
        h, m, s = int(v // 3600), int(v % 3600 // 60), int(v % 60)
        return f"{h}h {m:02d}m" if h else (f"{m}m {s:02d}s" if m else f"{v:.1f} s")
    return f.format(v)


def _body(c, name, x, y, R, t=0.0):
    col, look, _ = BODIES.get(name, BODIES["ball"])
    if look == "sun":
        draw_sprite(c, glow_dot(col, a=200), x, y, min(R * 2.2, R + 220)); _planet(c, x, y, R, col, None, False)
        return
    if look == "hole":
        draw_sprite(c, glow_dot((255, 150, 60), a=200), x, y, R * 1.9)
        c.drawCircle(x, y, R * 1.25, stroke_paint((255, 190, 90), R * 0.18, 230, blur=R * 0.06)); c.drawCircle(x, y, R, fill_paint((0, 0, 0)))
        return
    if look == "ball":
        draw_sprite(c, sphere(col), x, y, R); return
    if look == "ring":
        c.drawOval(skia.Rect(x - R * 2.1, y - R * 0.55, x + R * 2.1, y + R * 0.55), stroke_paint(mix(col, (255, 255, 255), 0.2), R * 0.18, 200))
    _planet(c, x, y, R, col, "earth" if look == "earth" else ("gas" if look in ("gas", "ring") else None))
    if look == "ring":
        c.save(); c.clipRect(skia.Rect(x - R * 2.3, y, x + R * 2.3, y + R)); c.drawOval(skia.Rect(x - R * 2.1, y - R * 0.55, x + R * 2.1, y + R * 0.55), stroke_paint(mix(col, (255, 255, 255), 0.2), R * 0.18, 230)); c.restore()


def _beam(c, x0, y0, x1, y1, col=(80, 255, 110), w=3):
    c.drawLine(x0, y0, x1, y1, stroke_paint(col, w * 4, 70, blur=8)); c.drawLine(x0, y0, x1, y1, stroke_paint(col, w))


def fact_short(path, spec, seed=1, text=True, dry=False, beam=(80, 255, 110)):
    show_text = text
    if isinstance(spec, str): spec = json.load(open(spec, encoding="utf-8"))
    rng = np.random.default_rng(seed); voice = spec.get("voice", "am_michael"); speed = spec.get("speed", 1.1)
    A = Audio(); lines = []; t = 0.25
    for ln in spec["lines"]:
        a, sr = E.say(ln["say"], voice, speed); d = len(a) / sr; A.clip(t, a, sr, 1.0)
        words = ln["say"].split(); lines.append((ln, t, d, words, t + E.word_times(words, d))); t += d + 0.22
    total = t + 1.0
    A.tone(0, E.midi(38), 0.10, total, "pad"); A.tone(0, E.midi(45), 0.07, total, "pad")
    for k in range(int(total / 0.5)): A.tone(k * 0.5, 55, 0.10 if k % 2 == 0 else 0.05, 0.25, "thud")
    for ln, t0, d, _, _ in lines:
        A.tone(max(0, t0 - 0.15), 600, 0.10, 0.5, "whoosh")
        if ln["scene"] == "card": A.chord(t0 + 0.1, 60, 0.18)
        if ln["scene"] in ("travel", "counter", "fall"):
            for q in range(int(d / 0.12)): A.tone(t0 + q * 0.12, 2200, 0.035, 0.05, "tick")
    if dry: return total
    S = _stars(rng); V = Writer(path, dry); fr = Frame(); nf = int(total * FPS)
    crowd = [(rng.uniform(-40, W + 40), 1080 + row * 95 + rng.uniform(-15, 15), 0.7 + row * 0.25, rng.integers(0, 4), rng.integers(0, 5), rng.uniform(0, 1.5))
             for row in range(5) for _ in range(9 + row * 2)]
    skins = [(255, 214, 180), (230, 180, 140), (190, 135, 95), (140, 95, 65)]; shirts = [(90, 150, 220), (220, 90, 90), (240, 200, 80), (120, 200, 140), (180, 120, 220)]
    for f in range(nf):
        t = f / FPS; cur = 0
        for j, L in enumerate(lines):
            if t >= L[1] - 0.2: cur = j
        ln, t0, d, words, wt = lines[cur]; u = max(0.0, t - t0); sc = ln["scene"]; q = _smooth(u / max(0.6, d * 0.9))
        c = fr.c; fr.clear((8, 10, 24), (2, 2, 8)); _draw_stars(c, S, t, zoom=1 + 0.02 * u)
        ax, ay, bx, by = 230, 1130, 840, 560
        if sc == "crowd":
            b = ln.get("b", "moon"); _body(c, b, 820, 360, 50)
            c.drawRect(skia.Rect(0, 1050, W, H), fill_paint((10, 14, 20), shader=skia.GradientShader.MakeLinear([(0, 1050), (0, H)], [rgb((16, 30, 30)), rgb((4, 6, 8))])))
            for (x, y, s, sk, sh, dl) in sorted(crowd, key=lambda z: z[1]):
                rz = _smooth((u - 0.2 - dl * 0.8) / 0.4); hand = _person(c, x, y, s, skins[sk], shirts[sh], rz)
                L = min(1.0, (u - 0.6 - dl * 0.8) / 0.35)
                if hand and rz >= 1 and L > 0: _beam(c, hand[0], hand[1], hand[0] + (820 - hand[0]) * L, hand[1] + (360 - hand[1]) * L, beam, 2)
        elif sc == "streak":
            x = -100 + u * 1500; y = 760
            for k in range(30): c.drawCircle(x - k * 28, y, 9 - k * 0.25, fill_paint(beam, 230 - k * 7))
            draw_sprite(c, glow_dot((220, 255, 220), a=220), x, y, 60)
            draw_text(c, ln.get("big", ""), W / 2, 1060, 104, YELLOW); draw_text(c, ln.get("sub", ""), W / 2, 1160, 64, WHITE)
        elif sc == "travel":
            a_, b_ = ln.get("a", "earth"), ln.get("b", "moon"); back = ln.get("back", False)
            _body(c, a_, ax, ay, 105 * min(1.4, BODIES.get(a_, BODIES["ball"])[2])); _body(c, b_, bx, by, 80 * min(1.5, BODIES.get(b_, BODIES["ball"])[2]))
            sx, sy, ex, ey = (bx, by, ax, ay) if back else (ax, ay, bx, by)
            hx, hy = sx + (ex - sx) * q, sy + (ey - sy) * q
            _beam(c, sx, sy, hx, hy, (255, 255, 255) if back else beam); draw_sprite(c, glow_dot((230, 255, 230), a=230), hx, hy, 40)
            v = ln.get("from", 0) + (ln.get("to", 0) - ln.get("from", 0)) * q
            draw_text(c, _fmt(v, ln.get("fmt", "{:,.0f}")), W / 2, 330, 116, YELLOW)
        elif sc == "scale":
            a_, b_ = ln.get("a", "earth"), ln.get("b", "sun"); ratio = float(ln.get("ratio", 10))
            ra = 60 if ratio > 6 else 120; rb = ra * (1 + (min(ratio, 9) - 1) * q)
            _body(c, b_, W / 2 + 120, 820, rb); _body(c, a_, 200, 820 + rb * 0.6 + 40, ra * (0.5 if ratio > 6 else 1))
            draw_text(c, ln.get("big", f"{ratio:,.0f}x"), W / 2, 330, 116, YELLOW)
        elif sc == "spread":
            a_, b_ = ln.get("a", "earth"), ln.get("b", "uranus"); wd = 40 + 300 * q
            _body(c, a_, ax, ay, 105)
            nx, ny = -(by - ay), bx - ax; nl = math.hypot(nx, ny); nx, ny = nx / nl, ny / nl
            cone = polyline([(ax, ay), (bx + nx * wd, by + ny * wd), (bx - nx * wd, by - ny * wd)], True)
            c.drawPath(cone, fill_paint(beam, 70, blur=10)); c.drawPath(cone, stroke_paint(beam, 2, 160))
            _body(c, b_, bx, by, max(14, 80 - (66 * q if ln.get("shrink") else 0)))
            if ln.get("shrink"): c.drawCircle(bx, by, wd, stroke_paint(beam, 4, 200))
            draw_text(c, ln.get("big", ""), W / 2, 330, 96, YELLOW)
        elif sc == "counter":
            v = float(ln.get("value", 0)) * q
            c.save(); c.translate(W / 2, 800); p = 1 + 0.06 * math.sin(u * 8) * (1 - q); c.scale(p, p)
            draw_text(c, _fmt(v, ln.get("fmt", "{:,.0f}")), 0, 0, 120, YELLOW); draw_text(c, ln.get("sub", ""), 0, 110, 66, WHITE); c.restore()
        elif sc == "fall":
            h_m, g = float(ln.get("height_m", 100)), float(ln.get("g", 9.81)); T = math.sqrt(2 * h_m / g)
            tt = min(T, u * max(1.0, T / max(1.0, d - 0.4)))            # time-lapse when the fall is longer than the line
            y = 420 + 820 * (0.5 * g * tt * tt / h_m)
            c.drawLine(W / 2 - 300, 1260, W / 2 + 300, 1260, stroke_paint((120, 120, 140), 6))
            for k in range(6):
                yy = 420 + 840 * k / 5; c.drawLine(180, yy, 220, yy, stroke_paint((120, 120, 140), 3))
                draw_text(c, f"{h_m * (1 - k / 5):,.0f} m", 120, yy + 12, 30, GREY, stroke=0, shadow=False)
            draw_sprite(c, sphere(BODIES.get(ln.get("b", "ball"), BODIES["ball"])[0]), W / 2, min(y, 1230), 30)
            draw_text(c, f"{tt:.1f} s", W / 2 + 260, 330, 110, YELLOW); draw_text(c, f"{g * tt:,.0f} m/s", W / 2 - 230, 330, 70, WHITE)
        elif sc == "orbit":
            a_, b_ = ln.get("a", "sun"), ln.get("b", "earth")
            c.drawOval(skia.Rect(W / 2 - 400, 800 - 170, W / 2 + 400, 800 + 170), stroke_paint((255, 255, 255), 2, 70))
            ang = u * 1.6; _body(c, a_, W / 2, 800, 90); _body(c, b_, W / 2 + 400 * math.cos(ang), 800 + 170 * math.sin(ang), 34)
            draw_text(c, ln.get("period", ""), W / 2, 330, 104, YELLOW)
        elif sc == "card":
            pop = 1 + 0.25 * math.exp(-u * 6); c.save(); c.translate(W / 2, 780); c.scale(pop, pop)
            draw_text(c, ln.get("big", ""), 0, 0, 150, YELLOW); draw_text(c, ln.get("sub", ""), 0, 120, 72, WHITE); c.restore()
        if show_text:
            k = int(np.searchsorted(wt, t, side="right") - 1)
            if 0 <= k < len(words) and t - t0 < d + 0.15:
                cs = (k // 3) * 3; word_caption(c, [w.upper() for w in words[cs:cs + 3]], k - cs, 1400, 82, YELLOW, 0.10 * math.exp(-(t - wt[k]) * 14))
        V.write(fr)
    return V.close(A)


# ------------------------------------------------------------------ number words for the voice
_N = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split()
_T = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()


def words(n):
    n = int(round(n))
    if n < 20: return _N[n]
    if n < 100: return _T[n // 10] + ("-" + _N[n % 10] if n % 10 else "")
    if n < 1000: return _N[n // 100] + " hundred" + (" " + words(n % 100) if n % 100 else "")
    for v, w in ((10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= v: return words(n // v) + " " + w + (" " + words(n % v) if n % v else "")


def say_num(n):
    """Natural spoken size: 2,870,000,000 -> 'two point nine billion', 1595 -> 'one thousand six hundred'."""
    for v, w in ((1e9, "billion"), (1e6, "million")):
        if n >= v:
            x = round(n / v, 1) if n / v < 10 else round(n / v)
            if x == int(x): return f"{words(x)} {w}"
            a, b = str(x).split("."); return f"{words(int(a))} point {words(int(b))} {w}"
    p = 10 ** max(0, len(str(int(n))) - 2); return words(round(n / p) * p)


def hm_words(s):
    h, m = int(s // 3600), int(round(s % 3600 / 60))
    out = ([f"{words(h)} hour" + ("s" if h > 1 else "")] if h else []) + ([f"{words(m)} minute" + ("s" if m > 1 else "")] if m else [])
    return " and ".join(out) or "less than a minute"


# ------------------------------------------------------------------ example specs (numbers computed, not typed)
DIST = {"moon": 384_400, "mars": 225_000_000, "jupiter": 778_000_000, "saturn": 1_430_000_000, "uranus": 2_870_000_000, "neptune": 4_500_000_000, "sun": 149_600_000}
DIAM = {"moon": 3_474, "mars": 6_779, "jupiter": 139_820, "saturn": 116_460, "uranus": 51_118, "neptune": 49_528, "sun": 1_392_700, "earth": 12_742}


def fact_laser_spec(target="uranus", mrad=0.5):
    d = DIST[target]; s = d / C_KM_S; wid = d * mrad / 1000; ratio = wid / DIAM[target]; T = target.capitalize()
    return {"title": f"What if 8 billion people aimed lasers at {T}? 🔦 #shorts #science", "lines": [
        {"say": f"What if eight billion people aimed lasers at {T}?", "scene": "crowd", "b": target},
        {"say": "Light is the fastest thing in the universe.", "scene": "streak", "big": "300,000 km", "sub": "EVERY SECOND"},
        {"say": "It hits the Moon in about one second.", "scene": "travel", "a": "earth", "b": "moon", "from": 0, "to": DIST["moon"] / C_KM_S, "fmt": "{:.2f} s"},
        {"say": f"But {T} is about {say_num(d)} kilometers away.", "scene": "counter", "value": d, "fmt": "{:,.0f} km", "sub": f"TO {T.upper()}"},
        {"say": f"So your laser needs {hm_words(s)}, just to get there.", "scene": "travel", "a": "earth", "b": target, "from": 0, "to": s, "fmt": "hms"},
        {"say": f"And by then, the beam has spread out over {words(round(wid / 1e6))} million kilometers wide." if wid >= 1e6 else f"And by then, the beam has spread out to {words(round(wid / 1000))} thousand kilometers wide.",
         "scene": "spread", "a": "earth", "b": target, "big": f"{wid:,.0f} km wide"},
        {"say": f"That's {words(ratio)} times wider than {T} itself.", "scene": "spread", "a": "earth", "b": target, "big": f"{ratio:.0f}x WIDER", "shrink": True},
        {"say": "So almost all of that light just misses.", "scene": "spread", "a": "earth", "b": target, "big": "IT MISSES", "shrink": True},
        {"say": f"And the tiny bit that bounces back? Another {hm_words(s)}.", "scene": "travel", "a": "earth", "b": target, "from": s, "to": 2 * s, "fmt": "hms", "back": True},
        {"say": f"{hm_words(2 * s).capitalize()}. For one round trip.", "scene": "card", "big": _fmt(2 * s, "hms"), "sub": "ROUND TRIP"},
    ]}


def car_to_sun_spec(kmh=100):
    hrs = DIST["sun"] / kmh; yrs = hrs / 24 / 365.25; light = DIST["sun"] / C_KM_S
    return {"title": "What if you drove a car to the Sun? ☀️ #shorts #science", "lines": [
        {"say": f"What if you drove to the Sun at {words(kmh)} kilometers an hour?", "scene": "travel", "a": "earth", "b": "sun", "from": 0, "to": kmh, "fmt": "{:.0f} km/h"},
        {"say": "No stops, no traffic, no sleep.", "scene": "streak", "big": f"{kmh} km/h", "sub": "NON-STOP"},
        {"say": f"It's about {say_num(DIST['sun'])} kilometers away.", "scene": "counter", "value": DIST["sun"], "fmt": "{:,.0f} km", "sub": "TO THE SUN"},
        {"say": f"You'd arrive in about {say_num(yrs)} years.", "scene": "travel", "a": "earth", "b": "sun", "from": 0, "to": yrs, "fmt": "{:.0f} YEARS"},
        {"say": f"Sunlight makes the same trip in {hm_words(light) if light >= 60 else 'seconds'}.", "scene": "travel", "a": "sun", "b": "earth", "from": 0, "to": light, "fmt": "hms"},
        {"say": f"And when you get there, the Sun is {words(DIAM['sun'] / DIAM['earth'])} times wider than Earth.", "scene": "scale", "a": "earth", "b": "sun", "ratio": DIAM["sun"] / DIAM["earth"], "big": f"{DIAM['sun'] / DIAM['earth']:.0f}x WIDER"},
        {"say": "A million Earths could fit inside it.", "scene": "counter", "value": 1_300_000, "fmt": "{:,.0f}", "sub": "EARTHS INSIDE"},
        {"say": f"{words(round(yrs)).capitalize()} years of driving. Just to get burned.", "scene": "card", "big": f"{yrs:.0f} YEARS", "sub": "ONE WAY"},
    ]}


def drop_spec(h_m=10_000, g=9.81):
    import math as m
    t_vac = m.sqrt(2 * h_m / g); v_vac = g * t_vac
    return {"title": "What if you dropped a ball from a plane with no air? ✈️ #shorts #physics", "lines": [
        {"say": f"What if you dropped a ball from {words(h_m)} meters, with no air at all?", "scene": "fall", "height_m": h_m, "g": g},
        {"say": f"Gravity speeds it up by about {words(g)} meters per second, every second.", "scene": "counter", "value": g, "fmt": "{:.1f} m/s", "sub": "FASTER EVERY SECOND"},
        {"say": f"It hits the ground after just {words(t_vac)} seconds.", "scene": "fall", "height_m": h_m, "g": g},
        {"say": f"Going about {say_num(v_vac * 3.6)} kilometers an hour.", "scene": "counter", "value": v_vac * 3.6, "fmt": "{:,.0f} km/h", "sub": "AT THE GROUND"},
        {"say": "That's faster than most passenger jets.", "scene": "streak", "big": f"{v_vac * 3.6:,.0f} km/h", "sub": "NO AIR"},
        {"say": f"{words(t_vac).capitalize()} seconds. From the sky to the ground.", "scene": "card", "big": f"{t_vac:.0f} s", "sub": f"FROM {h_m:,} m"},
    ]}


EXAMPLES = {"laser_uranus": lambda: fact_laser_spec("uranus"), "car_to_sun": car_to_sun_spec, "drop_no_air": drop_spec}
