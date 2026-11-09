"""art.py - flat-illustration drawing kit for Ambient Escape explainers (pycairo).

Everything is vector, drawn at 1080x1920. Characters are faceless flat figures with a real
skeleton (head, neck, torso, two-part arms and legs, shoes) posed by joint angles, so they
can move smoothly between poses. No glow blow-outs: lights are soft screen-blended pools.
"""
import math, random
import cairo
import numpy as np

W, H = 1080, 1920


# ------------------------------------------------------------------ helpers
def hexc(h, a=1.0):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255, a)


def mix(c1, c2, t):
    return tuple(a + (b - a) * t for a, b in zip(c1, c2))


def shade(c, k):
    """k<1 darker, k>1 lighter (towards white)."""
    if k <= 1:
        return (c[0] * k, c[1] * k, c[2] * k) + tuple(c[3:])
    t = k - 1
    return (c[0] + (1 - c[0]) * t, c[1] + (1 - c[1]) * t, c[2] + (1 - c[2]) * t) + tuple(c[3:])


def src(cr, c):
    if len(c) == 4:
        cr.set_source_rgba(*c)
    else:
        cr.set_source_rgb(*c)


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def seg(t, a, b):
    """0..1 progress of t through [a,b], eased."""
    if b <= a:
        return 1.0 if t >= b else 0.0
    return ease((t - a) / (b - a))


def rrect(cr, x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def poly(cr, pts):
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.close_path()


def vgrad(cr, y0, y1, stops, x0=0, x1=W, ya=None, yb=None):
    g = cairo.LinearGradient(0, y0, 0, y1)
    for o, c in stops:
        g.add_color_stop_rgba(o, *(c if len(c) == 4 else c + (1,)))
    cr.set_source(g)
    cr.rectangle(x0, ya if ya is not None else y0, x1 - x0, (yb if yb is not None else y1) - (ya if ya is not None else y0))
    cr.fill()


def light(cr, x, y, r, c, a=0.3, sy=1.0):
    """soft light pool, screen-blended, never blown out."""
    cr.save()
    cr.translate(x, y)
    cr.scale(1, sy)
    g = cairo.RadialGradient(0, 0, 0, 0, 0, r)
    g.add_color_stop_rgba(0, c[0], c[1], c[2], a)
    g.add_color_stop_rgba(0.45, c[0], c[1], c[2], a * 0.45)
    g.add_color_stop_rgba(1, c[0], c[1], c[2], 0)
    cr.set_operator(cairo.OPERATOR_SCREEN)
    cr.set_source(g)
    cr.arc(0, 0, r, 0, 2 * math.pi)
    cr.fill()
    cr.restore()


def shadow_ellipse(cr, x, y, rx, ry, a=0.35):
    cr.save()
    cr.translate(x, y)
    cr.scale(1, ry / rx)
    g = cairo.RadialGradient(0, 0, 0, 0, 0, rx)
    g.add_color_stop_rgba(0, 0, 0, 0, a)
    g.add_color_stop_rgba(1, 0, 0, 0, 0)
    cr.set_source(g)
    cr.arc(0, 0, rx, 0, 2 * math.pi)
    cr.fill()
    cr.restore()


def line(cr, pts, w, c, cap=cairo.LINE_CAP_ROUND):
    src(cr, c)
    cr.set_line_width(w)
    cr.set_line_cap(cap)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.stroke()


# ------------------------------------------------------------------ characters
LEN = dict(torso=150, neck=12, head=33, ua=80, fa=74, th=96, sh=92)

SKIN = [hexc("D7AD86"), hexc("C38F68"), hexc("E3C09C"), hexc("A87554")]
HAIR = hexc("231B17")

LOOKS = {
    "you":      dict(top=hexc("E6D8BE"), pants=hexc("2E3344"), shoe=hexc("17181F"), skin=SKIN[0], hair="short", beard=False),
    "friend":   dict(top=hexc("6E8FA8"), pants=hexc("2B2F3D"), shoe=hexc("17181F"), skin=SKIN[1], hair="short", beard=True),
    "seller":   dict(top=hexc("6F8B6A"), pants=hexc("33302E"), shoe=hexc("1B1917"), skin=SKIN[3], hair="kufi", beard=True),
    "neighbor": dict(top=hexc("B9775A"), pants=hexc("2E2B33"), shoe=hexc("17181F"), skin=SKIN[2], hair="kufi", beard=True),
    "man":      dict(top=hexc("E6D8BE"), pants=hexc("2E3344"), shoe=hexc("17181F"), skin=SKIN[1], hair="kufi", beard=True),
}

# joint angles (degrees). Limbs: 0 = straight down, 90 = forward, 180 = up.
# fe = elbow bend (forearm relative to upper arm, + = forward/up); kn = knee bend (- = shin back)
P = {
    "stand":     dict(t=2, n=0, fua=-5, ffe=10, nua=6, nfe=12, fth=-3, fkn=-2, nth=4, nkn=-3),
    "talk":      dict(t=4, n=2, fua=-5, ffe=10, nua=38, nfe=62, fth=-3, fkn=-2, nth=4, nkn=-3),
    "wave":      dict(t=0, n=-4, fua=-5, ffe=8, nua=150, nfe=22, fth=-3, fkn=-2, nth=4, nkn=-3),
    "handshake": dict(t=6, n=0, fua=-5, ffe=8, nua=52, nfe=28, fth=-3, fkn=-2, nth=5, nkn=-3),
    "give":      dict(t=6, n=2, fua=-5, ffe=8, nua=72, nfe=6, fth=-3, fkn=-2, nth=5, nkn=-3),
    "palms":     dict(t=8, n=22, fua=34, ffe=58, nua=40, nfe=56, fth=-3, fkn=-2, nth=4, nkn=-3),
    "dua":       dict(t=0, n=-6, fua=32, ffe=92, nua=40, nfe=86, fth=-2, fkn=-2, nth=3, nkn=-3),
    "bend":      dict(t=72, n=-14, fua=-8, ffe=6, nua=6, nfe=4, fth=34, fkn=-46, nth=52, nkn=-64),
    "carry":     dict(t=6, n=0, fua=62, ffe=14, nua=70, nfe=10, fth=-3, fkn=-2, nth=4, nkn=-3),
    "sit":       dict(t=-6, n=0, fua=18, ffe=48, nua=22, nfe=52, fth=86, fkn=-84, nth=90, nkn=-88),
    "sit_talk":  dict(t=0, n=2, fua=18, ffe=48, nua=40, nfe=70, fth=86, fkn=-84, nth=90, nkn=-88),
    "sit_whisper": dict(t=24, n=16, fua=22, ffe=50, nua=56, nfe=118, fth=86, fkn=-84, nth=90, nkn=-88),
    "sit_listen": dict(t=6, n=12, fua=18, ffe=48, nua=24, nfe=56, fth=86, fkn=-84, nth=90, nkn=-88),
    "sit_tasbih": dict(t=4, n=8, fua=20, ffe=58, nua=34, nfe=66, fth=84, fkn=-80, nth=88, nkn=-84),
    "sit_dhikr": dict(t=2, n=14, fua=20, ffe=58, nua=36, nfe=74, fth=84, fkn=-80, nth=88, nkn=-84),
}


def pose_mix(a, b, t):
    a = P[a] if isinstance(a, str) else a
    b = P[b] if isinstance(b, str) else b
    t = ease(t)
    return {k: a[k] + (b[k] - a[k]) * t for k in a}


def pose_add(p, **d):
    q = dict(p)
    for k, v in d.items():
        q[k] = q.get(k, 0) + v
    return q


def walk_pose(phase, amp=1.0):
    s = math.sin(phase)
    c = math.cos(phase)
    return dict(t=5, n=0,
                fua=22 * s * amp, ffe=14 + 6 * max(0, s), nua=-22 * s * amp, nfe=14 + 6 * max(0, -s),
                fth=-24 * s * amp, fkn=-(6 + 34 * max(0, c)) * amp, nth=24 * s * amp, nkn=-(6 + 34 * max(0, -c)) * amp)


def _v(a, f):
    r = math.radians(a)
    return (math.sin(r) * f, math.cos(r))


def _add(a, b, k=1.0):
    return (a[0] + b[0] * k, a[1] + b[1] * k)


def fk(p, f):
    up = (math.sin(math.radians(p["t"])) * f, -math.cos(math.radians(p["t"])))
    Hp = (0.0, 0.0)
    N = _add(Hp, up, LEN["torso"])
    S = _add(N, up, -18)
    hn = p["t"] + p["n"]
    hu = (math.sin(math.radians(hn)) * f, -math.cos(math.radians(hn)))
    Hd = _add(N, hu, LEN["neck"] + LEN["head"])
    J = dict(H=Hp, N=N, S=S, head=Hd, hn=hn, up=up)
    for s in ("f", "n"):
        E = _add(S, _v(p[s + "ua"], f), LEN["ua"])
        Hn = _add(E, _v(p[s + "ua"] + p[s + "fe"], f), LEN["fa"])
        K = _add(Hp, _v(p[s + "th"], f), LEN["th"])
        A = _add(K, _v(p[s + "th"] + p[s + "kn"], f), LEN["sh"])
        J[s + "E"], J[s + "W"], J[s + "K"], J[s + "A"] = E, Hn, K, A
    return J


def person(cr, x, y, pose, facing=1, scale=1.0, look="you", anchor="ground", hold=None, alpha=1.0):
    """Draw a figure. anchor='ground': lowest foot rests on y.  anchor='hip': hip joint at (x,y).
    hold: callable(cr, hand_xy, J) drawn after the near hand (phone, tasbih, branch...)."""
    L = LOOKS[look] if isinstance(look, str) else look
    p = P[pose] if isinstance(pose, str) else pose
    f = facing
    J = fk(p, f)
    if anchor == "ground":
        low = max(J["fA"][1], J["nA"][1]) + 13
        oy = -low
    else:
        oy = 0
    cr.save()
    cr.translate(x, y)
    cr.scale(scale, scale)
    cr.translate(0, oy)
    if alpha < 1:
        cr.push_group()
    top, pants, shoe, skin = L["top"], L["pants"], L["shoe"], L["skin"]
    far = 0.78

    def leg(s, k):
        line(cr, [J["H"], J[s + "K"], J[s + "A"]], 38, shade(pants, k))
        a = J[s + "A"]
        line(cr, [(a[0] - 10 * f, a[1] + 6), (a[0] + 30 * f, a[1] + 8)], 22, shade(shoe, k))

    def arm(s, k):
        line(cr, [J["S"], J[s + "E"], J[s + "W"]], 30, shade(top, k))
        src(cr, shade(skin, k))
        cr.arc(J[s + "W"][0], J[s + "W"][1], 13, 0, 2 * math.pi)
        cr.fill()

    # far side
    arm("f", far)
    leg("f", far)
    leg("n", 1.0)
    # pelvis
    src(cr, pants)
    cr.arc(0, 0, 27, 0, 2 * math.pi)
    cr.fill()
    # torso (jacket): hem, waist, chest, shoulders - smooth tapered body
    up = J["up"]
    pr = (-up[1], up[0])
    b0 = _add(J["H"], up, -8)
    wa = _add(J["H"], up, 46)
    ch = _add(J["N"], up, -46)
    n0 = _add(J["N"], up, -6)
    right = [_add(b0, pr, 31), _add(wa, pr, 28), _add(ch, pr, 32), _add(n0, pr, 26)]
    left = [_add(n0, pr, -26), _add(ch, pr, -32), _add(wa, pr, -28), _add(b0, pr, -31)]
    src(cr, top)
    cr.move_to(*right[0])
    cr.curve_to(*right[1], *right[1], *right[2])
    cr.curve_to(*right[3], *right[3], *left[0])
    cr.curve_to(*left[0], *left[1], *left[1])
    cr.curve_to(*left[2], *left[2], *left[3])
    cr.close_path()
    cr.fill_preserve()
    cr.set_line_width(12)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.stroke()
    # hem band + collar
    line(cr, [_add(b0, pr, 30), _add(b0, pr, -30)], 9, shade(top, 0.86))
    # neck + head
    line(cr, [n0, _add(J["N"], (math.sin(math.radians(J["hn"])) * f, -math.cos(math.radians(J["hn"]))), 14)], 24, shade(skin, 0.92))
    hx, hy = J["head"]
    cr.save()
    cr.translate(hx, hy)
    cr.rotate(math.radians(J["hn"]) * f)
    cr.scale(f, 1)
    R = LEN["head"]
    src(cr, skin)
    cr.arc(0, 0, R, 0, 2 * math.pi)
    cr.fill()
    cr.save()
    cr.arc(0, 0, R + 0.5, 0, 2 * math.pi)
    cr.clip()
    if L["hair"] == "kufi":
        src(cr, HAIR)
        poly(cr, [(-R - 2, -R * 0.1), (-4, -R * 0.1), (-10, 8), (-R - 2, 14)])
        cr.fill()
    else:
        src(cr, HAIR)
        poly(cr, [(-R - 2, -R - 2), (R + 2, -R - 2), (R + 2, -R * 0.42), (R * 0.42, -R * 0.56),
                  (-2, -R * 0.36), (-8, 4), (-R - 2, 16)])
        cr.fill()
    if L.get("beard"):
        src(cr, hexc("2E231D"))
        cr.move_to(-8, 12)
        cr.curve_to(-6, R * 0.9, R * 0.5, R * 1.05, R * 0.9, R * 0.62)
        cr.line_to(R * 0.95, R * 0.42)
        cr.curve_to(R * 0.5, R * 0.55, R * 0.1, R * 0.45, -2, 10)
        cr.close_path()
        cr.fill()
    cr.restore()
    if L["hair"] == "kufi":
        src(cr, hexc("EFE8DC"))
        cr.move_to(-R - 3, -R * 0.18)
        cr.curve_to(-R - 3, -R * 1.35, R + 3, -R * 1.35, R + 3, -R * 0.18)
        cr.close_path()
        cr.fill()
        line(cr, [(-R - 3, -R * 0.2), (R + 3, -R * 0.2)], 5, hexc("D6CCBB"))
    # ear
    src(cr, shade(skin, 0.86))
    cr.arc(-4, 2, 7, 0, 2 * math.pi)
    cr.fill()
    cr.restore()
    # near arm (+ held prop)
    arm("n", 1.0)
    if hold:
        hold(cr, J["nW"], J)
    if alpha < 1:
        cr.pop_group_to_source()
        cr.paint_with_alpha(alpha)
    cr.restore()
    return J


# ------------------------------------------------------------------ props
def sofa(cr, x0, x1, seat_y, col):
    back_top = seat_y - 190
    src(cr, shade(col, 0.82))
    rrect(cr, x0 + 20, back_top, x1 - x0 - 40, 210, 36)
    cr.fill()
    # back cushions
    n = 2
    cw = (x1 - x0 - 120) / n
    for i in range(n):
        src(cr, shade(col, 0.92))
        rrect(cr, x0 + 60 + i * cw + 6, back_top + 26, cw - 12, 150, 28)
        cr.fill()
    # seat
    src(cr, col)
    rrect(cr, x0 + 30, seat_y - 14, x1 - x0 - 60, 64, 20)
    cr.fill()
    src(cr, shade(col, 0.75))
    rrect(cr, x0 + 30, seat_y + 40, x1 - x0 - 60, 54, 14)
    cr.fill()
    # arms
    for ax in (x0, x1 - 74):
        src(cr, shade(col, 0.88))
        rrect(cr, ax, seat_y - 80, 74, 175, 30)
        cr.fill()
    # legs
    src(cr, hexc("1C1712"))
    for lx in (x0 + 40, x1 - 56):
        cr.rectangle(lx, seat_y + 92, 16, 22)
        cr.fill()


def floor_lamp(cr, x, floor_y, top_y, on=1.0):
    line(cr, [(x, floor_y - 6), (x, top_y + 50)], 8, hexc("15131A"))
    src(cr, hexc("15131A"))
    cr.save(); cr.translate(x, floor_y - 6); cr.scale(1, 0.25); cr.arc(0, 0, 46, 0, 2 * math.pi); cr.restore(); cr.fill()
    shade_c = mix(hexc("8A6A48"), hexc("F0C383"), on)
    src(cr, shade_c)
    poly(cr, [(x - 50, top_y + 64), (x + 50, top_y + 64), (x + 34, top_y), (x - 34, top_y)])
    cr.fill()
    if on > 0:
        light(cr, x, top_y + 90, 520, hexc("FFC37A"), 0.30 * on)
        light(cr, x, floor_y, 300, hexc("FFC37A"), 0.16 * on, sy=0.25)


def plant(cr, x, floor_y, s=1.0, leaf=hexc("4F6B4C")):
    src(cr, hexc("6B4A3A"))
    poly(cr, [(x - 34 * s, floor_y - 80 * s), (x + 34 * s, floor_y - 80 * s), (x + 26 * s, floor_y), (x - 26 * s, floor_y)])
    cr.fill()
    rng = random.Random(int(x))
    for i in range(9):
        a = -math.pi / 2 + (i - 4) * 0.28
        L_ = (120 + rng.random() * 70) * s
        tip = (x + math.cos(a) * L_, floor_y - 80 * s + math.sin(a) * L_)
        src(cr, shade(leaf, 0.8 + 0.25 * rng.random()))
        cr.move_to(x, floor_y - 80 * s)
        mid = (x + math.cos(a) * L_ * 0.5, floor_y - 80 * s + math.sin(a) * L_ * 0.5)
        pa = (-math.sin(a) * 22 * s, math.cos(a) * 22 * s)
        cr.curve_to(mid[0] + pa[0], mid[1] + pa[1], tip[0], tip[1], tip[0], tip[1])
        cr.curve_to(tip[0], tip[1], mid[0] - pa[0], mid[1] - pa[1], x, floor_y - 80 * s)
        cr.fill()


def building_row(cr, rng, base_y, hmin, hmax, col, win, x0=-40, x1=W + 40, wmin=110, wmax=210, lit=0.35, tw=0.0):
    x = x0
    while x < x1:
        w = rng.uniform(wmin, wmax)
        h = rng.uniform(hmin, hmax)
        src(cr, col)
        cr.rectangle(x, base_y - h, w + 1, h + 2)
        cr.fill()
        # roof detail
        if rng.random() < 0.3:
            cr.rectangle(x + w * 0.2, base_y - h - 18, w * 0.25, 18)
            cr.fill()
        if win:
            cols = max(2, int(w // 44))
            rows = max(2, int(h // 70))
            for r_ in range(rows):
                for c_ in range(cols):
                    if rng.random() < lit:
                        k = 0.75 + 0.25 * math.sin(tw * 1.3 + x * 0.1 + r_ * 1.7 + c_)
                        src(cr, (win[0], win[1], win[2], 0.55 + 0.35 * k))
                        cr.rectangle(x + 16 + c_ * (w - 32) / cols, base_y - h + 30 + r_ * 68, 16, 24)
                        cr.fill()
        x += w + rng.uniform(4, 30)


def masjid(cr, cx, base_y, s, col, win=None, glow=0.0):
    cr.save()
    cr.translate(cx, base_y)
    cr.scale(s, s)
    src(cr, col)
    # main hall
    cr.rectangle(-230, -170, 460, 170)
    cr.fill()
    # drum + dome
    cr.rectangle(-120, -250, 240, 90)
    cr.fill()
    cr.move_to(-130, -248)
    cr.curve_to(-130, -390, -20, -420, 0, -455)
    cr.curve_to(20, -420, 130, -390, 130, -248)
    cr.close_path()
    cr.fill()
    line(cr, [(0, -455), (0, -490)], 6, col)
    cr.arc(0, -500, 9, 0, 2 * math.pi)
    cr.fill()
    # small domes
    for sx in (-170, 170):
        cr.arc(sx, -170, 48, math.pi, 0)
        cr.fill()
    # minarets
    for mx in (-300, 300):
        cr.rectangle(mx - 22, -560, 44, 560)
        cr.fill()
        cr.rectangle(mx - 34, -430, 68, 16)
        cr.fill()
        cr.rectangle(mx - 32, -600, 64, 14)
        cr.fill()
        cr.move_to(mx - 22, -600)
        cr.line_to(mx, -680)
        cr.line_to(mx + 22, -600)
        cr.close_path()
        cr.fill()
    # arch windows
    if win:
        for i in range(-3, 4):
            ax = i * 58
            src(cr, (win[0], win[1], win[2], 0.85))
            cr.move_to(ax - 16, -30)
            cr.line_to(ax - 16, -100)
            cr.arc(ax, -100, 16, math.pi, 0)
            cr.line_to(ax + 16, -30)
            cr.close_path()
            cr.fill()
        if glow > 0:
            light(cr, 0, -70, 380, win, 0.18 * glow)
    cr.restore()


def bird(cr, x, y, s, phase, col):
    flap = math.sin(phase) * 0.8
    src(cr, col)
    cr.set_line_width(5 * s)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.move_to(x - 22 * s, y - 10 * s * flap)
    cr.curve_to(x - 12 * s, y - 14 * s * flap, x - 6 * s, y - 4 * s, x, y)
    cr.curve_to(x + 6 * s, y - 4 * s, x + 12 * s, y - 14 * s * flap, x + 22 * s, y - 10 * s * flap)
    cr.stroke()


def stars(cr, rng_seed, n, y0, y1, t, a=0.8):
    rng = random.Random(rng_seed)
    for i in range(n):
        x = rng.uniform(0, W)
        y = rng.uniform(y0, y1)
        r = rng.uniform(1.2, 3.0)
        k = 0.55 + 0.45 * math.sin(t * rng.uniform(0.8, 2.2) + i)
        cr.set_source_rgba(1, 0.97, 0.9, a * k)
        cr.arc(x, y, r, 0, 2 * math.pi)
        cr.fill()


def tree(cr, x, ground_y, s, trunk, leaf, rng):
    line(cr, [(x, ground_y), (x, ground_y - 170 * s)], 26 * s, trunk, cap=cairo.LINE_CAP_BUTT)
    for i in range(6):
        dx = rng.uniform(-90, 90) * s
        dy = rng.uniform(-330, -190) * s
        r = rng.uniform(70, 110) * s
        src(cr, shade(leaf, rng.uniform(0.85, 1.1)))
        cr.arc(x + dx, ground_y + dy, r, 0, 2 * math.pi)
        cr.fill()
