"""scenes.py - full-frame illustrated scenes for the explainer renderer.
Every scene fills the whole 1080x1920 frame. The action stays inside the middle band
(y 450-1140); the top and bottom of the frame hold calm background (wall, sky, floor)
that sits under the text scrims.
scene(cr, t, S): t = seconds since the scene started, S = scene spec (cues = line start times).
"""
import math, random
import cairo
import numpy as np
import cv2
from art import *
import textkit as T

GROUND = 1128  # where standing feet rest


def cue(S, i, d=0.0):
    c = S.get("cues", [0.0])
    return (c[i] if i < len(c) else c[-1]) + d


# ------------------------------------------------------------------ speech bubble (art layer)
def bubble(cr, x, y, text, t_in, t, tail="left", size=30, bg=hexc("F4EEE3"), fg=(40, 36, 44)):
    if t < t_in:
        return
    k = ease_out((t - t_in) / 0.25)
    surf, w, h = T.text_surface(text, "Poppins-Medium.ttf", size, fg)
    pw, ph = w + 52, h + 34
    cr.save()
    cr.translate(x, y)
    cr.scale(0.6 + 0.4 * k, 0.6 + 0.4 * k)
    cr.push_group()
    src(cr, (0, 0, 0, 0.25))
    rrect(cr, -pw / 2 + 4, -ph + 8, pw, ph, 26)
    cr.fill()
    src(cr, bg)
    rrect(cr, -pw / 2, -ph, pw, ph, 26)
    cr.fill()
    tx = -pw * 0.22 if tail == "left" else pw * 0.22
    poly(cr, [(tx - 16, -4), (tx + 16, -4), (tx + (-22 if tail == "left" else 22), 26)])
    cr.fill()
    cr.set_source_surface(surf, -w / 2, -ph + 17)
    cr.paint()
    cr.pop_group_to_source()
    cr.paint_with_alpha(k)
    cr.restore()


def sparkle(cr, x, y, s, a, col=hexc("F2C46B")):
    if a <= 0:
        return
    cr.save()
    cr.translate(x, y)
    cr.scale(s, s)
    src(cr, (col[0], col[1], col[2], a))
    cr.move_to(0, -20)
    cr.curve_to(3, -3, 3, -3, 20, 0)
    cr.curve_to(3, 3, 3, 3, 0, 20)
    cr.curve_to(-3, 3, -3, 3, -20, 0)
    cr.curve_to(-3, -3, -3, -3, 0, -20)
    cr.fill()
    cr.restore()


def sparkle_burst(cr, x, y, t0, t, n=5, spread=90, seed=1):
    if t < t0 or t > t0 + 1.6:
        return
    rng = random.Random(seed)
    for i in range(n):
        d = rng.uniform(0.0, 0.35)
        u = clamp((t - t0 - d) / 1.2)
        if u <= 0 or u >= 1:
            continue
        ang = rng.uniform(-math.pi, 0)
        r = spread * ease_out(u)
        sparkle(cr, x + math.cos(ang) * r, y + math.sin(ang) * r - 30 * u, rng.uniform(0.5, 1.0), math.sin(u * math.pi))


# ================================================================== LIVING ROOM (night)
def room_bg(cr, t, lamp=1.0):
    vgrad(cr, 0, 1100, [(0, hexc("1E1C2E")), (1, hexc("2A2640"))], ya=0, yb=1100)
    # cove light along the ceiling
    vgrad(cr, 0, 90, [(0, hexc("2C2840")), (1, hexc("1E1C2E"))], ya=0, yb=90)
    # window (left)
    wx, wy, ww, wh = 70, 470, 300, 380
    src(cr, hexc("3A3552"))
    rrect(cr, wx - 18, wy - 18, ww + 36, wh + 36, 8)
    cr.fill()
    vgrad(cr, wy, wy + wh, [(0, hexc("141C36")), (1, hexc("2E3B63"))], x0=wx, x1=wx + ww, ya=wy, yb=wy + wh)
    cr.save()
    cr.rectangle(wx, wy, ww, wh)
    cr.clip()
    src(cr, hexc("F3E6C8"))
    cr.arc(wx + 220, wy + 80, 26, 0, 2 * math.pi)
    cr.fill()
    src(cr, hexc("1F2A4C"))
    cr.arc(wx + 232, wy + 72, 24, 0, 2 * math.pi)
    cr.fill()
    building_row(cr, random.Random(3), wy + wh + 4, 120, 260, hexc("0F152B"), hexc("F2C27A"), x0=wx - 20, x1=wx + ww + 20,
                 wmin=50, wmax=90, lit=0.35, tw=t)
    cr.restore()
    line(cr, [(wx + ww / 2, wy), (wx + ww / 2, wy + wh)], 10, hexc("3A3552"))
    line(cr, [(wx, wy + wh / 2), (wx + ww, wy + wh / 2)], 10, hexc("3A3552"))
    # curtains
    for cx, d in ((wx - 40, 1), (wx + ww + 40, -1)):
        src(cr, hexc("4A3F5E"))
        cr.move_to(cx - 34 * d, wy - 40)
        cr.line_to(cx + 34 * d, wy - 40)
        cr.curve_to(cx + 40 * d, wy + 200, cx + 10 * d, wy + 380, cx + 26 * d, wy + wh + 60)
        cr.line_to(cx - 34 * d, wy + wh + 60)
        cr.close_path()
        cr.fill()
    line(cr, [(wx - 90, wy - 40), (wx + ww + 90, wy - 40)], 8, hexc("15131C"))
    # picture frame
    src(cr, hexc("1A1724"))
    rrect(cr, 600, 560, 250, 170, 6)
    cr.fill()
    vgrad(cr, 574, 716, [(0, hexc("D99A6C")), (1, hexc("7C4B57"))], x0=614, x1=836, ya=574, yb=716)
    src(cr, hexc("4B2F44"))
    poly(cr, [(614, 716), (614, 660), (690, 620), (760, 670), (836, 640), (836, 716)])
    cr.fill()
    # floor
    vgrad(cr, 1100, H, [(0, hexc("2E2427")), (0.3, hexc("221B1E")), (1, hexc("120E10"))], ya=1100, yb=H)
    line(cr, [(0, 1100), (W, 1100)], 6, hexc("3A2D31"))
    for i in range(1, 14):
        yy = 1100 + i * i * 4.6
        line(cr, [(0, yy), (W, yy)], 2, (1, 1, 1, 0.035))
    # rug
    src(cr, hexc("40333C"))
    cr.save(); cr.translate(540, 1230); cr.scale(1, 0.2); cr.arc(0, 0, 500, 0, 2 * math.pi); cr.restore(); cr.fill()
    src(cr, hexc("4C3D47"))
    cr.save(); cr.translate(540, 1230); cr.scale(1, 0.2); cr.arc(0, 0, 420, 0, 2 * math.pi); cr.restore()
    cr.set_line_width(6); cr.stroke()
    # foreground coffee table (sits under the YouTube UI area, below the captions)
    src(cr, hexc("2A1E1E"))
    rrect(cr, 140, 1540, 800, 70, 14)
    cr.fill()
    src(cr, hexc("3A2A28"))
    rrect(cr, 120, 1505, 840, 50, 14)
    cr.fill()
    src(cr, hexc("D9CBB4"))
    rrect(cr, 300, 1440, 70, 70, 10)
    cr.fill()
    line(cr, [(370, 1455), (392, 1462), (392, 1486), (370, 1494)], 9, hexc("D9CBB4"))
    src(cr, hexc("6E8FA8"))
    rrect(cr, 600, 1478, 200, 30, 4)
    cr.fill()
    src(cr, hexc("B9775A"))
    rrect(cr, 620, 1452, 170, 28, 4)
    cr.fill()
    # lamp + plant
    floor_lamp(cr, 960, 1100, 560, on=lamp)
    plant(cr, 70, 1104, 1.1)


def scene_living_room(cr, t, S):
    room_bg(cr, t)
    sofa(cr, 170, 910, 986, hexc("4B4569"))
    c1 = cue(S, 1)
    # friend (left, faces right): talks, then leans in to whisper
    k = seg(t, c1 - 0.3, c1 + 0.35)
    base = pose_add(P["sit_talk"], nfe=10 * math.sin(t * 5.0) * (1 - k))
    fp = pose_mix(base, "sit_whisper", k)
    person(cr, 400 + 18 * k, 976, fp, facing=1, look="friend", anchor="hip")
    # you (right, faces left): listening, leans in a little
    yp = pose_mix("sit", "sit_listen", seg(t, 0.2, 0.9))
    yp = pose_add(yp, t=4 * k, n=-3 * k)
    person(cr, 690, 976, yp, facing=-1, look="you", anchor="hip")
    bubble(cr, 360, 690, S.get("bubble", "Don't tell anyone."), c1 + 0.35, t, tail="right", size=31)
    light(cr, 960, 650, 300, hexc("FFC37A"), 0.06 * (1 + 0.15 * math.sin(t * 3)))


# ================================================================== PHONE (group chat)
_BLUR = {}


def _blurred_room():
    if "room" not in _BLUR:
        s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        c = cairo.Context(s)
        room_bg(c, 0.0, lamp=1.0)
        sofa(c, 170, 910, 986, hexc("4B4569"))
        a = np.ndarray((H, W, 4), np.uint8, s.get_data()).copy()
        a = cv2.GaussianBlur(a, (0, 0), 22)
        a[..., :3] = (a[..., :3] * 0.62).astype(np.uint8)
        a[..., 3] = 255
        out = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        np.ndarray((H, W, 4), np.uint8, out.get_data())[:] = a
        out.mark_dirty()
        _BLUR["room"] = out
    return _BLUR["room"]


CHAT = [("Adam", "yo what's going on with Yusuf?", hexc("E0A35A")),
        ("Bilal", "he's been off all week", hexc("7FB3D5")),
        ("Adam", "anyone know??", hexc("E0A35A"))]


def scene_phone(cr, t, S):
    mode = S.get("mode", "chat")
    cr.set_source_surface(_blurred_room(), 0, 0)
    cr.paint()
    if mode == "type":
        light(cr, 540, 800, 700, hexc("C8483A"), 0.18 * (0.7 + 0.3 * math.sin(t * 4)))
    PX, PY, PW, PH = 310, 452, 460, 690
    bob = 4 * math.sin(t * 1.3)
    cr.save()
    cr.translate(0, bob)
    shadow_ellipse(cr, PX + PW / 2 + 10, PY + PH / 2 + 20, 300, 380, 0.45)
    # body
    src(cr, hexc("0E0F13"))
    rrect(cr, PX, PY, PW, PH, 52)
    cr.fill()
    src(cr, hexc("2A2C33"))
    cr.set_line_width(3)
    rrect(cr, PX + 2, PY + 2, PW - 4, PH - 4, 50)
    cr.stroke()
    sx, sy, sw, sh = PX + 14, PY + 14, PW - 28, PH - 28
    cr.save()
    rrect(cr, sx, sy, sw, sh, 40)
    cr.clip()
    src(cr, hexc("121419"))
    cr.paint()
    # status + header
    src(cr, hexc("1C1F26"))
    cr.rectangle(sx, sy, sw, 118)
    cr.fill()
    src(cr, hexc("0E0F13"))
    rrect(cr, sx + sw / 2 - 52, sy + 12, 104, 28, 14)
    cr.fill()
    src(cr, hexc("3E4452"))
    cr.arc(sx + 58, sy + 80, 24, 0, 2 * math.pi)
    cr.fill()
    for i, cc in enumerate((hexc("E0A35A"), hexc("7FB3D5"), hexc("9FC79A"))):
        src(cr, cc)
        cr.arc(sx + 48 + i * 10, sy + 76 + (i % 2) * 8, 7, 0, 2 * math.pi)
        cr.fill()
    T.paint_text(cr, S.get("chat_name", "the boys"), "Poppins-Medium.ttf", 25, (238, 236, 232), sx + 94, sy + 58)
    T.paint_text(cr, S.get("chat_members", "Adam, Bilal, Yusuf, You"), "Poppins-Regular.ttf", 17, (150, 156, 168), sx + 94, sy + 90)
    # messages
    y = sy + 140
    c0 = cue(S, 0)
    shown = [(w, m, hexc(c) if isinstance(c, str) else c) for w, m, c in S.get("chat", CHAT)]
    for i, (who, msg, col) in enumerate(shown):
        t_in = (c0 + 0.15 + i * 0.75) if mode == "chat" else -1
        if t < t_in:
            break
        k = ease_out((t - t_in) / 0.3) if t_in >= 0 else 1
        y = T.chat_bubble(cr, sx + 18, y, sw - 90, who, msg, col, incoming=True, alpha=k, rise=(1 - k) * 18)
    # typing dots while chat arrives
    if mode == "chat":
        tt = c0 + 0.15 + len(shown) * 0.75
        if t > tt:
            src(cr, hexc("2A2E37"))
            rrect(cr, sx + 18, y + 6, 92, 44, 22)
            cr.fill()
            for i in range(3):
                a = 0.4 + 0.6 * max(0, math.sin(t * 6 - i * 0.8))
                cr.set_source_rgba(0.8, 0.82, 0.86, a)
                cr.arc(sx + 44 + i * 20, y + 28, 6, 0, 2 * math.pi)
                cr.fill()
    # outgoing reply (payoff)
    if mode == "delete_send":
        t_send = cue(S, 1, 0.1)
        if t >= t_send:
            k = ease_out((t - t_send) / 0.3)
            T.chat_bubble(cr, sx + 70, y, sw - 90, None, S.get("reply", "he's good. just give him some space"), hexc("2F7D69"),
                          incoming=False, alpha=k, rise=(1 - k) * 18, right=sx + sw - 18)
    # input bar
    iy = sy + sh - 78
    src(cr, hexc("1C1F26"))
    cr.rectangle(sx, iy - 14, sw, 92)
    cr.fill()
    src(cr, hexc("262A33"))
    rrect(cr, sx + 16, iy, sw - 96, 52, 26)
    cr.fill()
    draft = ""
    full = S.get("draft", "bro he told me he's going through")
    if mode == "type":
        n = int(clamp((t - cue(S, 0, 0.2)) / 1.9) * len(full))
        draft = full[:n]
    elif mode == "delete_send":
        n = int((1 - clamp((t - cue(S, 0, 0.1)) / 1.0)) * len(full))
        draft = full[:n]
        if n == 0:
            t_type2 = cue(S, 0, 1.25)
            msg2 = S.get("reply", "he's good. just give him some space")
            if t < cue(S, 1, 0.1):
                draft = msg2[:int(clamp((t - t_type2) / 1.2) * len(msg2))]
    show = draft[-24:] if draft else "Message"
    col = (236, 236, 236) if draft else (120, 126, 138)
    T.paint_text(cr, show, "Poppins-Regular.ttf", 21, col, sx + 36, iy + 13)
    if draft and int(t * 2.4) % 2 == 0:
        surf, w_, h_ = T.text_surface(show, "Poppins-Regular.ttf", 21, col)
        src(cr, hexc("7FB3D5"))
        cr.rectangle(sx + 38 + w_, iy + 14, 3, 26)
        cr.fill()
    # send button
    red = mode == "type" and draft
    pulse = (0.5 + 0.5 * math.sin(t * 7)) if red else 0
    bc = mix(hexc("2F7D69"), hexc("D2493B"), 1.0 if red else 0.0)
    src(cr, bc)
    cr.arc(sx + sw - 46, iy + 26, 26 + 3 * pulse, 0, 2 * math.pi)
    cr.fill()
    cr.set_source_rgb(1, 1, 1)
    poly(cr, [(sx + sw - 56, iy + 14), (sx + sw - 32, iy + 26), (sx + sw - 56, iy + 38), (sx + sw - 52, iy + 26)])
    cr.fill()
    cr.restore()  # screen clip
    cr.restore()


# ================================================================== NIGHT SKY / MASJID (reveal)
def scene_reveal(cr, t, S):
    vgrad(cr, 0, 1140, [(0, hexc("0C1029")), (0.6, hexc("1B2250")), (1, hexc("3A3A6A"))], ya=0, yb=1140)
    stars(cr, 7, 160, 0, 1000, t, 0.85)
    light(cr, 760, 1080, 600, hexc("F2C27A"), 0.12)
    rng = random.Random(9)
    building_row(cr, rng, 1140, 40, 120, hexc("10142E"), hexc("F2C27A"), wmin=90, wmax=160, lit=0.25, tw=t)
    masjid(cr, 905, 1140, 0.38, hexc("131733"), win=hexc("F2C27A"), glow=1.0)
    # rooftop in the foreground with a man making du'a
    src(cr, hexc("0A0C1C"))
    cr.rectangle(-10, 1100, 460, 60)
    cr.fill()
    person(cr, 200, 1102, pose_add(P["dua"], n=-4 * math.sin(t * 0.8)), facing=1, look="man", scale=0.6)
    vgrad(cr, 1140, H, [(0, hexc("0E1126")), (1, hexc("07080F"))], ya=1140, yb=H)
    rng = random.Random(31)
    building_row(cr, rng, H + 10, 260, 420, hexc("0B0D1E"), hexc("E8B86A"), wmin=160, wmax=260, lit=0.18, tw=t)


# ================================================================== NIGHT STREET (two friends walking)
def street_bg(cr, t, minaret=True):
    vgrad(cr, 0, 1100, [(0, hexc("10142C")), (1, hexc("2E3158"))], ya=0, yb=1100)
    stars(cr, 21, 90, 0, 700, t, 0.7)
    src(cr, hexc("F3E6C8"))
    cr.arc(820, 300, 40, 0, 2 * math.pi)
    cr.fill()
    src(cr, hexc("10142C"))
    cr.arc(836, 290, 36, 0, 2 * math.pi)
    cr.fill()
    light(cr, 820, 300, 200, hexc("F3E6C8"), 0.1)
    rng = random.Random(5)
    building_row(cr, rng, 1000, 300, 560, hexc("1B1E3C"), hexc("F2C27A"), lit=0.25, tw=t)
    if minaret:
        masjid(cr, 300, 1000, 0.55, hexc("1B1E3C"))
    rng = random.Random(11)
    building_row(cr, rng, 1060, 220, 420, hexc("24264A"), hexc("F7CF86"), wmin=150, wmax=240, lit=0.4, tw=t)
    # sidewalk + road
    src(cr, hexc("3A3650"))
    cr.rectangle(0, 1060, W, 76)
    cr.fill()
    line(cr, [(0, 1062), (W, 1062)], 4, hexc("4A4562"))
    vgrad(cr, 1136, H, [(0, hexc("232233")), (1, hexc("12111C"))], ya=1136, yb=H)
    line(cr, [(0, 1138), (W, 1138)], 6, hexc("4E4866"))
    for i in range(6):
        x = (i * 230 - (t * 40) % 230) - 60
        src(cr, (0.85, 0.82, 0.7, 0.35))
        cr.rectangle(x, 1590, 120, 12)
        cr.fill()
    for lx in (180, 900):
        light(cr, lx, 1500, 160, hexc("FFC37A"), 0.12, sy=0.3)
    for lx in (140, 940):
        line(cr, [(lx, 1132), (lx, 640)], 10, hexc("14131F"))
        line(cr, [(lx, 640), (lx + (40 if lx < 500 else -40), 620)], 8, hexc("14131F"))
        src(cr, hexc("F7D9A0"))
        cr.arc(lx + (40 if lx < 500 else -40), 632, 14, 0, 2 * math.pi)
        cr.fill()
        light(cr, lx + (40 if lx < 500 else -40), 640, 330, hexc("FFC37A"), 0.22)
        light(cr, lx, 1110, 220, hexc("FFC37A"), 0.18, sy=0.22)


def scene_street_walk(cr, t, S):
    street_bg(cr, t)
    d = S["dur"]
    x = 300 + 260 * (t / max(d, 0.1))
    ph = t * 5.2
    person(cr, x - 120, GROUND, walk_pose(ph + 1.6), facing=1, look="friend", scale=0.95)
    J = person(cr, x + 40, GROUND, walk_pose(ph), facing=1, look="you", scale=0.95)


# ================================================================== MARKET (dusk)
def market_bg(cr, t):
    vgrad(cr, 0, 900, [(0, hexc("221A2C")), (0.7, hexc("5A3A3E")), (1, hexc("8A5A47"))], ya=0, yb=900)
    rng = random.Random(4)
    building_row(cr, rng, 900, 260, 520, hexc("3A2A30"), hexc("F2C27A"), wmin=140, wmax=230, lit=0.3, tw=t)
    vgrad(cr, 880, 1140, [(0, hexc("4A3433")), (1, hexc("3C2B2B"))], ya=880, yb=1140)
    # string lights
    for row, yb in ((0, 470), (1, 560)):
        cr.set_line_width(3)
        src(cr, hexc("1A1418"))
        cr.move_to(-20, yb - 60)
        cr.curve_to(300, yb + 60, 780, yb + 60, W + 20, yb - 60)
        cr.stroke()
        for i in range(13):
            u = i / 12
            bx = -20 + u * (W + 40)
            by = (1 - u) ** 3 * (yb - 60) + 3 * (1 - u) ** 2 * u * (yb + 60) + 3 * (1 - u) * u ** 2 * (yb + 60) + u ** 3 * (yb - 60)
            k = 0.7 + 0.3 * math.sin(t * 2 + i * 1.3 + row)
            cr.set_source_rgba(1, 0.82, 0.5, 0.9 * k)
            cr.arc(bx, by + 10, 7, 0, 2 * math.pi)
            cr.fill()
            light(cr, bx, by + 10, 40, hexc("FFC37A"), 0.25 * k)
    # ground
    vgrad(cr, 1130, H, [(0, hexc("3E2F2C")), (1, hexc("1A1314"))], ya=1130, yb=H)
    line(cr, [(0, 1132), (W, 1132)], 5, hexc("4E3B37"))
    rng = random.Random(12)
    for r_ in range(9):
        yy = 1160 + r_ * r_ * 9 + r_ * 20
        hh = 16 + r_ * 5
        x = -rng.uniform(0, 60)
        while x < W:
            ww = 60 + r_ * 12 + rng.uniform(-10, 10)
            src(cr, (1, 0.9, 0.8, 0.045 + 0.01 * (r_ % 2)))
            rrect(cr, x, yy, ww - 8, hh, hh / 2)
            cr.fill()
            x += ww


def stall(cr, x0, x1, top, counter_y, t):
    # posts
    for px in (x0 + 10, x1 - 26):
        src(cr, hexc("2A1E1C"))
        cr.rectangle(px, top, 16, 1132 - top)
        cr.fill()
    # back wall
    src(cr, hexc("3A2926"))
    cr.rectangle(x0 + 26, top + 70, x1 - x0 - 52, counter_y - top - 70)
    cr.fill()
    # shelves with jars
    for sy in (top + 180, top + 270):
        line(cr, [(x0 + 40, sy), (x1 - 40, sy)], 8, hexc("5A3E33"))
        for i in range(int((x1 - x0 - 100) / 46)):
            jx = x0 + 60 + i * 46
            src(cr, mix(hexc("C98B4A"), hexc("8DA35B"), (i % 3) / 2))
            rrect(cr, jx, sy - 44, 30, 40, 6)
            cr.fill()
    # lantern
    lx = (x0 + x1) / 2
    line(cr, [(lx, top + 70), (lx, top + 110)], 3, hexc("1A1418"))
    src(cr, hexc("F6C77E"))
    rrect(cr, lx - 16, top + 110, 32, 44, 8)
    cr.fill()
    light(cr, lx, top + 140, 260, hexc("FFC37A"), 0.28 * (0.9 + 0.1 * math.sin(t * 3)))
    # awning with scallops
    n = 7
    w = (x1 - x0 + 40) / n
    for i in range(n):
        src(cr, hexc("B5523F") if i % 2 == 0 else hexc("EADCC2"))
        ax = x0 - 20 + i * w
        cr.move_to(ax, top)
        cr.line_to(ax + w, top)
        cr.line_to(ax + w, top + 60)
        cr.arc(ax + w / 2, top + 60, w / 2, 0, math.pi)
        cr.close_path()
        cr.fill()
    src(cr, (0, 0, 0, 0.18))
    cr.rectangle(x0 - 20, top, x1 - x0 + 40, 14)
    cr.fill()


def counter(cr, x0, x1, y):
    src(cr, hexc("6A4A39"))
    cr.rectangle(x0, y, x1 - x0, 1132 - y)
    cr.fill()
    src(cr, hexc("7E5A45"))
    cr.rectangle(x0 - 10, y - 14, x1 - x0 + 20, 18)
    cr.fill()
    for i in range(4):
        line(cr, [(x0 + 30 + i * (x1 - x0 - 60) / 3, y + 20), (x0 + 30 + i * (x1 - x0 - 60) / 3, 1120)], 4, hexc("5A3E30"))
    # fruit crates on the counter
    for j, (cx, col) in enumerate(((x0 + 80, hexc("E39A3B")), (x0 + 200, hexc("8DA35B")), (x1 - 110, hexc("B8473A")))):
        src(cr, hexc("4A3326"))
        cr.rectangle(cx - 52, y - 54, 104, 44)
        cr.fill()
        for k in range(5):
            src(cr, shade(col, 0.9 + 0.1 * (k % 2)))
            cr.arc(cx - 36 + k * 18, y - 58 - (k % 2) * 8, 14, 0, 2 * math.pi)
            cr.fill()


def scene_market(cr, t, S):
    mode = S.get("mode", "hook")
    market_bg(cr, t)
    if mode == "hook":
        stall(cr, 560, 1060, 560, 900, t)
        counter(cr, 580, 1040, 930)
        person(cr, 860, 930 + 150, pose_add(P["talk"], nfe=8 * math.sin(t * 3)), facing=-1, look="seller", scale=0.9)
        counter(cr, 580, 1040, 930)
        # customer walks in and looks at empty hands
        tw = cue(S, 0, 1.4)
        if t < tw:
            x = -80 + (380 + 80) * ease(t / tw)
            person(cr, x, GROUND, walk_pose(t * 6.0), facing=1, look="you")
        else:
            k = seg(t, tw, tw + 0.5)
            person(cr, 380, GROUND, pose_mix("stand", "palms", k), facing=1, look="you")
    else:  # "word": buy, hand over, kind word
        stall(cr, 420, 1060, 560, 900, t)
        c1 = cue(S, 1)
        # seller behind counter
        sp = pose_mix("stand", "give", seg(t, 0.4, 0.9) - seg(t, c1 - 0.1, c1 + 0.3))
        person(cr, 780, 1080, sp, facing=-1, look="seller", scale=0.92)
        counter(cr, 440, 1040, 930)
        # bag handed over
        kb = seg(t, 0.6, 1.1)
        bx = 700 - 150 * kb
        src(cr, hexc("D9C3A0"))
        rrect(cr, bx - 30, 860 - 70 * (1 - kb) + 40 * kb, 60, 70, 8)
        cr.fill()
        cp = pose_mix("stand", "give", seg(t, 0.3, 0.8))
        cp = pose_mix(cp, pose_add(P["talk"], nfe=10 * math.sin(t * 5)), seg(t, c1 - 0.4, c1))
        person(cr, 380, GROUND, cp, facing=1, look="you")
        bubble(cr, 360, 650, S.get("bubble", "JazakAllahu khayran!"), c1 - 0.2, t, tail="left", size=30)
        sparkle_burst(cr, 760, 720, c1 + 0.6, t, n=6, spread=110, seed=2)


# ================================================================== NEIGHBOURHOOD
def street_day_bg(cr, t, evening=False):
    if evening:
        vgrad(cr, 0, 1000, [(0, hexc("232849")), (0.6, hexc("6B4E66")), (1, hexc("C7805F"))], ya=0, yb=1000)
    else:
        vgrad(cr, 0, 1000, [(0, hexc("6E93B8")), (0.65, hexc("C9C2C0")), (1, hexc("F1CDA6"))], ya=0, yb=1000)
        light(cr, 160, 640, 520, hexc("FFE2B0"), 0.35)
    rng = random.Random(8)
    for i, (x0, w, h, col) in enumerate(((-30, 330, 560, "C98F6B"), (300, 300, 480, "D9B48A"), (600, 300, 600, "9FB0A0"),
                                          (900, 260, 520, "C9A07E"))):
        c = hexc(col)
        if evening:
            c = shade(c, 0.55)
        top = 1060 - h
        src(cr, c)
        cr.rectangle(x0, top, w, h)
        cr.fill()
        src(cr, shade(c, 0.85))
        cr.rectangle(x0 - 8, top - 18, w + 16, 26)
        cr.fill()
        # windows
        for r_ in range(2):
            for c_ in range(2):
                wx = x0 + 50 + c_ * (w - 160)
                wy = top + 60 + r_ * 150
                lit = evening and rng.random() < 0.8
                src(cr, hexc("F7CF86") if lit else shade(hexc("3E4E5E"), 1.0))
                rrect(cr, wx, wy, 60, 84, 6)
                cr.fill()
                if lit:
                    light(cr, wx + 30, wy + 42, 90, hexc("FFC37A"), 0.25)
        # door
        dx = x0 + w / 2 - 40
        src(cr, shade(c, 0.6))
        cr.move_to(dx, 1060)
        cr.line_to(dx, 1060 - 150)
        cr.arc(dx + 40, 1060 - 150, 40, math.pi, 0)
        cr.line_to(dx + 80, 1060)
        cr.close_path()
        cr.fill()
        if evening:
            src(cr, hexc("F7D9A0"))
            cr.arc(dx + 100, 1060 - 190, 9, 0, 2 * math.pi)
            cr.fill()
            light(cr, dx + 100, 1060 - 190, 160, hexc("FFC37A"), 0.3)
    tree(cr, 1010, 1070, 0.9, hexc("4E3B30"), hexc("5F7E58") if not evening else hexc("2F3F33"), random.Random(2))
    src(cr, hexc("CDBFAE") if not evening else hexc("4A4152"))
    cr.rectangle(0, 1060, W, 76)
    cr.fill()
    vgrad(cr, 1136, H, [(0, hexc("6F665E") if not evening else hexc("231F2B")), (1, hexc("2A2622") if not evening else hexc("0E0C12"))],
          ya=1136, yb=H)
    line(cr, [(0, 1138), (W, 1138)], 6, hexc("9A8E80") if not evening else hexc("3A3446"))
    for i in range(5):
        src(cr, (1, 1, 1, 0.18) if not evening else (0.9, 0.85, 0.7, 0.18))
        cr.rectangle(i * 240 + 40, 1600, 130, 12)
        cr.fill()


def scene_neighbors(cr, t, S):
    mode = S.get("mode", "smile")
    evening = mode == "evening"
    street_day_bg(cr, t, evening)
    if mode == "smile":
        c1 = cue(S, 1)
        # neighbour walks in from the right; you wave, then shake hands
        tw = c1 - 0.2
        nx = 1160 - (1160 - 640) * ease(t / tw) if t < tw else 640
        npz = walk_pose(t * 6.0) if t < tw else pose_mix("stand", "handshake", seg(t, c1 + 0.3, c1 + 0.8))
        person(cr, nx, GROUND, npz, facing=-1, look="neighbor")
        yp = pose_mix("stand", pose_add(P["wave"], nfe=18 * math.sin(t * 8)), seg(t, 0.6, 1.0) - seg(t, c1 + 0.1, c1 + 0.5))
        yp = pose_mix(yp, "handshake", seg(t, c1 + 0.3, c1 + 0.8))
        person(cr, 450, GROUND, yp, facing=1, look="you")
        sparkle_burst(cr, 545, 760, c1 + 0.9, t, n=6, spread=120, seed=5)
    else:  # evening CTA: you wave goodnight to a neighbour at his door
        person(cr, 750, GROUND, pose_add(P["wave"], nfe=16 * math.sin(t * 7)), facing=-1, look="neighbor")
        x = 200 + 170 * ease(t / max(S["dur"] * 0.6, 0.1))
        moving = t < S["dur"] * 0.6
        person(cr, x, GROUND, walk_pose(t * 6) if moving else pose_mix("stand", "wave", seg(t, S["dur"] * 0.6, S["dur"] * 0.6 + 0.4)),
               facing=1, look="you")


# ================================================================== PARK PATH (remove harm)
def scene_park(cr, t, S):
    vgrad(cr, 0, 1000, [(0, hexc("7FA2BF")), (1, hexc("E7D8BD"))], ya=0, yb=1000)
    light(cr, 860, 520, 480, hexc("FFE2B0"), 0.3)
    src(cr, hexc("93A98C"))
    cr.move_to(0, 960)
    cr.curve_to(300, 860, 600, 900, W, 880)
    cr.line_to(W, 1100)
    cr.line_to(0, 1100)
    cr.close_path()
    cr.fill()
    rng = random.Random(6)
    for x in (80, 330, 980):
        tree(cr, x, 1050, 1.0, hexc("5A4636"), hexc("5E7F5A"), rng)
    # bench
    src(cr, hexc("6B4F3B"))
    rrect(cr, 600, 960, 240, 22, 6)
    cr.fill()
    rrect(cr, 600, 920, 240, 18, 6)
    cr.fill()
    for bx in (620, 810):
        cr.rectangle(bx, 980, 12, 70)
        cr.fill()
    vgrad(cr, 1040, 1140, [(0, hexc("D8C7A6")), (1, hexc("C9B592"))], ya=1040, yb=1140)
    vgrad(cr, 1140, H, [(0, hexc("5F7A52")), (1, hexc("2A3A25"))], ya=1140, yb=H)
    rngf = random.Random(19)
    for i in range(70):
        fx, fy = rngf.uniform(0, W), rngf.uniform(1200, H)
        k = (fy - 1200) / (H - 1200)
        src(cr, shade(hexc("7E9C67"), 0.8 + 0.3 * rngf.random()))
        line(cr, [(fx, fy), (fx + 6, fy - 26 - 30 * k)], 4 + 3 * k, shade(hexc("7E9C67"), 0.9))
        if rngf.random() < 0.3:
            src(cr, rngf.choice([hexc("F2D06B"), hexc("F4EEE3"), hexc("E39A8A")]))
            cr.arc(fx + 6, fy - 28 - 30 * k, 6 + 5 * k, 0, 2 * math.pi)
            cr.fill()
    vgrad(cr, 960, 1040, [(0, hexc("6E8B5E")), (1, hexc("5F7A52"))], ya=960, yb=1040)
    d = S["dur"]
    c1 = cue(S, 1)
    t_walk1, t_bend, t_lift = c1 - 0.6, c1, c1 + 0.7
    t_carry_end = t_lift + 1.4
    # branch position
    bx0, by0 = 620, 1112
    if t < t_lift:
        bx, by, ba = bx0, by0, 0.0
        carried = False
    else:
        carried = True
    # walker
    if t < t_walk1:
        x = 120 + (470 - 120) * ease(t / t_walk1)
        J = person(cr, x, GROUND, walk_pose(t * 6.0), facing=1, look="you")
    elif t < t_lift:
        k = seg(t, t_bend - 0.4, t_bend + 0.2)
        J = person(cr, 470, GROUND, pose_mix("stand", "bend", k), facing=1, look="you")
    else:
        k = seg(t, t_lift, t_lift + 0.5)
        u = clamp((t - t_lift - 0.5) / 1.2)
        x = 470 + 330 * ease(u)
        pz = pose_mix("bend", "carry", k)
        if 0 < u < 1:
            wp = walk_pose(t * 6.0, 0.7)
            pz = {kk: pz[kk] if kk in ("fua", "ffe", "nua", "nfe", "t") else wp[kk] for kk in pz}
        put = seg(t, t_carry_end + 0.2, t_carry_end + 0.8)
        pz = pose_mix(pz, "bend", put) if put > 0 else pz
        J = person(cr, x, GROUND, pz, facing=1, look="you")
    # branch drawn after (in hands / on the path / on the grass)
    if not carried:
        hx, hy, ang = bx0, by0, 0.08
    else:
        u = clamp((t - t_lift - 0.5) / 1.2)
        put = seg(t, t_carry_end + 0.2, t_carry_end + 0.8)
        x = 470 + 330 * ease(u)
        lift = ease_out(clamp((t - t_lift) / 0.5))
        hx = x + 70
        hy = by0 - 200 * lift + 160 * put
        ang = 0.08 - 0.1 * lift
        if t > t_carry_end + 0.8:
            hx, hy, ang = 870, 1150, 0.25
    cr.save()
    cr.translate(hx, hy)
    cr.rotate(ang)
    line(cr, [(-130, 0), (-40, -6), (40, 4), (130, -2)], 18, hexc("5B3F2C"))
    line(cr, [(-40, -6), (-70, -50)], 9, hexc("5B3F2C"))
    line(cr, [(40, 4), (80, -40)], 9, hexc("5B3F2C"))
    for lx, ly in ((-74, -56), (84, -46), (120, -20), (-120, -18)):
        src(cr, hexc("6B8F4E"))
        cr.save(); cr.translate(lx, ly); cr.rotate(0.6); cr.scale(1, 0.5); cr.arc(0, 0, 18, 0, 2 * math.pi); cr.restore(); cr.fill()
    cr.restore()
    if t > t_carry_end + 0.8:
        sparkle_burst(cr, 640, 900, t_carry_end + 0.8, t, n=6, spread=110, seed=8)


# ================================================================== SUNSET + MASJID (tasbih)
def scene_sunset(cr, t, S):
    vgrad(cr, 0, 1060, [(0, hexc("2B2347")), (0.45, hexc("7B4058")), (0.8, hexc("D36E4E")), (1, hexc("F2A65E"))], ya=0, yb=1060)
    src(cr, hexc("FFD58E"))
    cr.arc(540, 960, 110, 0, 2 * math.pi)
    cr.fill()
    light(cr, 540, 960, 520, hexc("FFC37A"), 0.3)
    rng = random.Random(14)
    building_row(cr, rng, 1060, 80, 240, hexc("4A2638"), None, wmin=100, wmax=180)
    masjid(cr, 720, 1060, 0.58, hexc("3A1D2E"), win=hexc("F7C27A"), glow=0.6)
    # birds
    for i in range(7):
        bx = (-100 + (t * 70 + i * 160) % 1300)
        by = 520 + 40 * math.sin(i * 1.7) + 10 * math.sin(t + i)
        bird(cr, bx, by, 1.1 - 0.06 * i, t * 9 + i, hexc("3A1D2E"))
    # rooftop ledge in front
    src(cr, hexc("2A1622"))
    cr.rectangle(0, 1060, W, 80)
    cr.fill()
    line(cr, [(0, 1062), (W, 1062)], 6, hexc("4A2638"))
    vgrad(cr, 1140, H, [(0, hexc("2A1622")), (1, hexc("12080E"))], ya=1140, yb=H)
    for r_ in range(8):
        yy = 1170 + r_ * (34 + r_ * 6)
        line(cr, [(0, yy), (W, yy)], 3, (1, 0.7, 0.5, 0.06))
    # man sitting on the ledge with tasbih
    nod = 4 * math.sin(t * 3.0)
    pz = pose_add(P["sit_dhikr"], n=nod, nfe=4 * math.sin(t * 3.0))

    def tasbih(cr_, w, J):
        cr_.save()
        cr_.translate(w[0], w[1])
        n = 15
        for i in range(n):
            a = math.pi * 0.15 + i * (math.pi * 1.6 / n) + t * 1.2
            r = 26
            src(cr_, hexc("E6C38A") if i != int(t * 3) % n else hexc("FFF0C8"))
            cr_.arc(math.cos(a) * r * 0.6, 26 + math.sin(a) * r, 5.5, 0, 2 * math.pi)
            cr_.fill()
        cr_.restore()

    person(cr, 330, 1052, pz, facing=1, look="man", anchor="hip", hold=tasbih)
    # each tasbeeh: a soft spark rises
    for k in range(6):
        t0 = cue(S, 1) + k * 0.5
        u = clamp((t - t0) / 1.4)
        if 0 < u < 1:
            sparkle(cr, 450 + 20 * math.sin(k), 820 - 160 * ease_out(u), 0.7, math.sin(u * math.pi))


SCENES = {
    "living_room": scene_living_room,
    "phone": scene_phone,
    "reveal": scene_reveal,
    "street_walk": scene_street_walk,
    "market": scene_market,
    "neighbors": scene_neighbors,
    "park": scene_park,
    "sunset": scene_sunset,
}
