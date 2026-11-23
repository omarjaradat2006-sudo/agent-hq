"""auto_bounce2: Bounce Theory templates on Engine 2 (Skia + pymunk), rebuilt from the Bounce Inspo videos (2026-11-19).

  jelly_drop        (Video-26144)  a 1,000-ball jelly sheet drops on a trampoline plate; every kick sends real
                                   impact waves through it (dome, bowl, funnel, ring, tilt); leaves the top -> loops.
  claw_flood        (Video-17387)  a gear wanders round the circle swinging 2 claws on their own; every claw hit
                                   adds a ball (zero gravity, elastic); colour changes each doubling; circle breaks.
  overflow_pendulum (Video-18009)  real pendulum (pin joint) in a bowl; every hit splits a ball; bouncy balls spray;
                                   bowl shatters when it overflows; empty bowl fades back in -> loops.
  fact_laser        (Video-10954)  narrated science "what if" with a free local AI voice (Kokoro) and word-by-word
                                   captions: 8 billion lasers at a planet, real light-speed maths.

fn(path, seed=..., text=True, dry=False, **knobs) -> seconds. TEMPLATES (bottom) = menu entries.
"""
import math, numpy as np, skia, pymunk
from scipy.spatial import Delaunay
from scipy import sparse
import json
import engine2 as E
from engine2 import text as draw_text
from engine2 import (W, H, FPS, TAU, Frame, Writer, Audio, rgb, mix, hsv, sphere, glow_dot, draw_sprite, draw_balls,
                     stroke_paint, fill_paint, polyline, title, word_caption, WHITE, YELLOW, GREY)

PREV = None   # seconds, for quick previews
LOG = []      # (t, balls) once a second, for tuning


def _smooth(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


# ====================================================================== 1. JELLY DROP
KICKS = ["center", "rim", "ring", "tilt", "center2", "rim2", "wave", "flat"]


def jelly_drop(path, seed=1, text=True, dry=False, n=1000, kicks=None, every=2.3, Rp=420.0, k=450.0, e=0.45, g=2400.0,
               hue0=0.33, hue_span=-0.62, elev=24.0, l1="1,000 BALLS ON A TRAMPOLINE", l2="WAIT FOR THE LAST BOUNCE", bg=(12, 13, 20)):
    rng = np.random.default_rng(seed)
    if kicks is None:
        pool = ["center", "rim", "ring", "tilt", "center2", "rim2", "wave"]
        kicks = list(rng.choice(pool, 7, replace=False)) + ["launch"]
    i = np.arange(n); r = np.sqrt((i + 0.5) / n); th = i * math.pi * (3 - math.sqrt(5)) + rng.uniform(0, TAU)
    x = Rp * r * np.cos(th); y = Rp * r * np.sin(th)
    tri = Delaunay(np.c_[x, y]).simplices
    ed = np.unique(np.sort(np.r_[tri[:, [0, 1]], tri[:, [1, 2]], tri[:, [0, 2]]], 1), axis=0)
    ln = np.hypot(x[ed[:, 0]] - x[ed[:, 1]], y[ed[:, 0]] - y[ed[:, 1]]); ed = ed[ln < 2.2 * np.median(ln)]
    Adj = sparse.coo_matrix((np.ones(len(ed) * 2), (np.r_[ed[:, 0], ed[:, 1]], np.r_[ed[:, 1], ed[:, 0]])), shape=(n, n)).tocsr()
    deg = np.asarray(Adj.sum(1)).ravel()
    z = np.full(n, 1500.0) + 25 * np.cos(th) * r; vz = np.zeros(n)          # starts above the frame, slight tilt
    cols_q = [tuple(int(c) for c in hsv(hue0 + hue_span * q / 63, 0.88, 1.0)) for q in range(64)]
    ci = np.clip((r * 63).astype(int), 0, 63)
    A = Audio(); V = Writer(path, dry); sub = 6; dt = 1 / (FPS * sub)
    total = 1.4 + len(kicks) * every + 0.6
    if PREV: total = min(total, PREV)
    A.tone(0, E.midi(43), 0.16, total, "pad"); A.tone(0, E.midi(50), 0.10, total, "pad")
    ev_t = [1.4 + j * every for j in range(len(kicks))]; done = set(); last_thud = -1; bounce_no = 0
    e_ = math.radians(elev); cx, cy0, F = W / 2, 1180.0, 2400.0
    fr = Frame(); nf = int(total * FPS)
    for f in range(nf):
        t = f / FPS
        for j, te in enumerate(ev_t):
            if j not in done and t >= te:
                done.add(j); kind = kicks[j]; bounce_no = j + 1; Aamp = 1500 * rng.uniform(0.85, 1.15)
                if kind == "center":  prof = np.exp(-(r / 0.28) ** 2) * 1.5
                elif kind == "center2": prof = np.exp(-(r / 0.45) ** 2) * 1.2
                elif kind == "rim":   prof = _smooth((r - 0.45) / 0.5) * 1.4
                elif kind == "rim2":  prof = _smooth((r - 0.2) / 0.8) * 1.2
                elif kind == "ring":  prof = np.exp(-((r - 0.55) / 0.16) ** 2) * 1.5
                elif kind == "tilt":  prof = 0.5 + 0.7 * np.cos(th - rng.uniform(0, TAU)) * r
                elif kind == "wave":  prof = 0.6 + 0.6 * np.sin(r * 9)
                elif kind == "launch": prof = np.ones(n) * 1.9
                else: prof = np.ones(n) * 0.9
                vz += Aamp * prof
                A.tone(te, E.midi(rng.choice([45, 47, 50, 52])), 0.45, 0.7, "boing")
                for q, m in enumerate((72, 76, 79, 84)): A.note(te + 0.04 * q, m + (j % 3) * 2, 0.07, 1.2, "chime")
        for s_ in range(sub):
            lap = Adj @ z - deg * z
            vz += (k * lap / 6.0 - g - 1.6 * vz * 0.0) * dt
            vz *= 0.9993
            z += vz * dt
            hit = z < 0
            if hit.any():
                imp = -vz[hit].clip(max=0)
                z[hit] = 0; vz[hit] = -vz[hit] * e
                ts = t + s_ * dt; en = imp.sum() / n
                if en > 60 and ts - last_thud > 0.12:
                    A.tone(ts, 62, min(0.7, en / 900), 0.5, "thud"); last_thud = ts
        if dry: V.write(None); continue
        c = fr.c; fr.clear(bg, (6, 6, 10))
        # plate
        ry = 1.06 * Rp * math.sin(e_)
        plate = skia.Rect(cx - Rp * 1.06, cy0 - ry, cx + Rp * 1.06, cy0 + ry)
        c.drawOval(plate.makeOffset(0, 14), fill_paint((0, 0, 0), 120, blur=18))
        sh = skia.GradientShader.MakeRadial((cx, cy0 - ry * 0.4), Rp * 1.2, [rgb((62, 62, 72)), rgb((34, 34, 42))])
        c.drawOval(plate, fill_paint((50, 50, 60), shader=sh)); c.drawOval(plate, stroke_paint((95, 95, 110), 2, 160))
        # contact shadow: darker when the sheet is low
        hmean = float(np.clip(z.mean(), 0, 800)); sa = int(130 * math.exp(-hmean / 260))
        if sa > 5: c.drawOval(skia.Rect(cx - Rp * 0.95, cy0 - ry * 0.9, cx + Rp * 0.95, cy0 + ry * 0.9), fill_paint((0, 0, 0), sa, blur=26))
        X = x; Y = y; Z = z
        depth = Y * math.cos(e_) - Z * math.sin(e_); kk = F / (F + depth)
        sx = cx + X * kk; sy = cy0 - (Y * math.sin(e_) + Z * math.cos(e_)) * kk
        rad = 11.5 * kk
        order = np.argsort(-depth)
        for q in order:
            draw_sprite(c, sphere(cols_q[ci[q]]), sx[q], sy[q], rad[q])
        if text:
            title(c, l1, l2, 210, 74)
            if bounce_no: draw_text(c, f"BOUNCE {bounce_no} / {len(kicks)}", W / 2, 1440, 64, YELLOW if bounce_no == len(kicks) else WHITE)
        V.write(fr)
    return V.close(A)


# ====================================================================== 2. CLAW FLOOD (pymunk)
CLAW_PAL = [(255, 214, 40), (175, 60, 235), (60, 230, 140), (255, 70, 90), (40, 200, 255), (255, 140, 30), (240, 70, 210),
            (120, 120, 255), (190, 255, 60), (0, 230, 230), (255, 255, 255)]


def claw_flood(path, seed=1, text=True, dry=False, cap_balls=1100, r=10.0, R=430.0, ra=118.0, sweep=250.0, pace=24.0,
               cd=0.18, wander=165.0, palette=None, l1="EVERY CLAW HIT ADDS A BALL", l2="WILL THE CIRCLE BREAK?", max_secs=33):
    rng = np.random.default_rng(seed); pal = palette or CLAW_PAL; off = int(rng.integers(len(pal)))
    cx, cy = W / 2, 880.0
    sp = pymunk.Space(); sp.gravity = (0, 0); sp.iterations = 12
    arena = []
    for a0 in np.linspace(0, TAU, 97)[:-1]:
        a1 = a0 + TAU / 96
        s = pymunk.Segment(sp.static_body, (cx + (R + 6) * math.cos(a0), cy + (R + 6) * math.sin(a0)),
                           (cx + (R + 6) * math.cos(a1), cy + (R + 6) * math.sin(a1)), 6)
        s.elasticity = 1.0; s.friction = 0; arena.append(s)
    sp.add(*arena)
    # claw local shape: arc that starts at the gear (origin) and curls round sweep degrees
    ss = np.radians(np.linspace(8, sweep, 30)); arc = np.c_[ra + ra * np.cos(math.pi + ss), ra * np.sin(math.pi + ss)]
    claws = []
    ph = rng.uniform(0, TAU, 6); dirs = rng.choice([-1, 1], 2)
    def gear_at(t): return np.array([cx + wander * math.sin(0.41 * t + ph[0]) * math.cos(0.13 * t), cy + wander * math.sin(0.57 * t + ph[1])])
    def claw_ang(k, t):
        return ph[2 + k] + dirs[k] * (1.1 + 0.25 * k) * t + 1.3 * math.sin((0.8 + 0.35 * k) * t + ph[4 + k])
    for k in range(2):
        b = pymunk.Body(body_type=pymunk.Body.KINEMATIC); b.position = tuple(gear_at(0)); b.angle = claw_ang(k, 0)
        segs = [pymunk.Segment(b, tuple(arc[j]), tuple(arc[j + 1]), 9) for j in range(len(arc) - 1)]
        for s in segs: s.elasticity = 1.0; s.friction = 0; s.collision_type = 2
        sp.add(b, *segs); claws.append(b)
    gb = pymunk.Body(body_type=pymunk.Body.KINEMATIC); gs = pymunk.Circle(gb, 30); gs.elasticity = 1.0; gs.collision_type = 3
    gb.position = tuple(gear_at(0)); sp.add(gb, gs)
    balls = []   # (body, shape, colour index)
    def add_ball(p, v, lv):
        b = pymunk.Body(1, pymunk.moment_for_circle(1, 0, r)); b.position = tuple(p); b.velocity = tuple(v)
        s = pymunk.Circle(b, r); s.elasticity = 0.98; s.friction = 0; s.collision_type = 1
        sp.add(b, s); balls.append([b, s, lv, 0.0])
    a = rng.uniform(0, TAU); add_ball((cx + 250 * math.cos(a), cy + 250 * math.sin(a)), (520 * math.cos(a + 2), 520 * math.sin(a + 2)), 0)
    hits = []
    def on_hit(arb, space, data):
        sh = arb.shapes; hits.append(sh[0] if sh[0].collision_type == 1 else sh[1])
    sp.on_collision(1, 2, begin=on_hit)
    by_shape = {}
    A = Audio(); V = Writer(path, dry); sub = 3; dt = 1 / (FPS * sub)
    fr = Frame(); f = 0; broke = None; level = 0; last_note = -1; flashes = []; shards = []; last_hit = 0
    A.tone(0, E.midi(38), 0.12, max_secs + 4, "pad")
    while True:
        t = f / FPS
        if PREV and t > PREV: break
        for s_ in range(sub):
            ts = t + s_ * dt
            gp, gp2 = gear_at(ts), gear_at(ts + dt)
            gb.position = tuple(gp); gb.velocity = tuple((gp2 - gp) / dt); gb.angular_velocity = 3.0
            for k, b in enumerate(claws):
                a0, a1 = claw_ang(k, ts), claw_ang(k, ts + dt)
                b.position = tuple(gp); b.angle = a0; b.velocity = tuple((gp2 - gp) / dt); b.angular_velocity = (a1 - a0) / dt
            hits.clear(); sp.step(dt)
            if broke is None and hits:
                last_hit = ts
                lookup = {id(bb[1]): bb for bb in balls}
                target = 2 ** (min(1.0, ts / pace) * math.log2(cap_balls))
                room = min(cap_balls, int(target * 1.25) + 1) - len(balls)
                for shp in hits:
                    bb = lookup.get(id(shp))
                    if bb is None or room <= 0 or ts - bb[3] < cd: continue
                    bb[3] = ts; room -= 1
                    lv = int(math.log2(len(balls) + 1))
                    v = bb[0].velocity; ang = rng.uniform(0, TAU)
                    p = bb[0].position + (2.2 * r * math.cos(ang), 2.2 * r * math.sin(ang))
                    if math.hypot(p[0] - cx, p[1] - cy) < R - r - 2:
                        add_ball(p, (v[0] * 0.8 + 300 * math.cos(ang), v[1] * 0.8 + 300 * math.sin(ang)), lv)
                        flashes.append([p[0], p[1], ts])
                        if ts - last_note > 0.045:
                            A.note(ts, 60 + [0, 2, 4, 7, 9, 12, 14, 16, 19, 21, 24, 26][min(lv, 11)], 0.12, 0.35)
                            A.impact(ts, math.hypot(*v), 880, "chime", 0.1, unit=60, d=0.4); last_note = ts
                        if lv > level:
                            level = lv; A.chord(ts, 60 + 2 * (lv % 6), 0.12)
                if len(balls) >= cap_balls: broke = ts
            if broke is None and ts - last_hit > 1.2:   # nobody near a claw: aim one ball at the gear
                bb = balls[int(rng.integers(len(balls)))][0]; d = gp - np.array(bb.position); d /= np.linalg.norm(d) + 1e-6
                bb.velocity = tuple(d * 700); last_hit = ts
            if broke is not None and not shards:
                sp.remove(*arena); A.tone(ts, 0, 0.75, 2.4, "crash"); A.chord(ts + 0.2, 55, 0.3)
                for a0 in np.linspace(0, TAU, 28, endpoint=False):
                    shards.append([cx + R * math.cos(a0), cy + R * math.sin(a0), math.cos(a0) * rng.uniform(300, 800), math.sin(a0) * rng.uniform(300, 800) - 200, a0, rng.uniform(-6, 6)])
                for bb in balls:
                    p = np.array(bb[0].position) - (cx, cy); bb[0].velocity = tuple(np.array(bb[0].velocity) + p * 2.2)
        if broke is None and f % 6 == 0:  # keep it lively: zero-g energy top-up
            for bb in balls:
                v = bb[0].velocity; s = math.hypot(*v)
                if s < 280: bb[0].velocity = (v[0] * 1.15 + 1, v[1] * 1.15 + 1)
                elif s > 1100: bb[0].velocity = (v[0] * 0.9, v[1] * 0.9)
        if broke is not None:
            for sh in shards: sh[0] += sh[2] / FPS; sh[1] += sh[3] / FPS; sh[3] += 1200 / FPS; sh[4] += sh[5] / FPS
            sp.gravity = (0, 900)
        if dry: V.write(None)
        else:
            c = fr.c; fr.clear((0, 0, 0))
            if broke is None: c.drawCircle(cx, cy, R + 6, stroke_paint((235, 235, 240), 4))
            for sx_, sy_, _, _, a0, _ in shards:
                dx, dy = -math.sin(a0) * 48, math.cos(a0) * 48; c.drawLine(sx_ - dx, sy_ - dy, sx_ + dx, sy_ + dy, stroke_paint((235, 235, 240), 4))
            xy = [bb[0].position for bb in balls]; cl = [pal[(bb[2] + off) % len(pal)] for bb in balls]
            draw_balls(c, xy, cl, r, glow=0.5 if len(balls) < 300 else 0.0)
            for fl in flashes:
                u = t - fl[2]
                if 0 <= u < 0.25: draw_sprite(c, glow_dot((255, 255, 255), a=200), fl[0], fl[1], 40 * (1 - u / 0.25) + 10)
            flashes[:] = [fl for fl in flashes if t - fl[2] < 0.25]
            for b in claws:
                pts = [tuple(b.local_to_world(tuple(q))) for q in arc]
                c.drawPath(polyline(pts), stroke_paint((60, 60, 66), 24))
                c.drawPath(polyline(pts), stroke_paint((168, 168, 176), 18))
                c.drawPath(polyline(pts), stroke_paint((215, 215, 222), 6))
            _gear(c, gb.position[0], gb.position[1], t * 3.0)
            if text:
                if broke is None:
                    title(c, l1, l2, 200, 72); draw_text(c, f"{len(balls):,} BALLS", W / 2, 1440, 76, pal[(level + off) % len(pal)])
                else:
                    title(c, "IT BROKE!", f"{len(balls):,} BALLS", 220, 96)
            V.write(fr)
        f += 1
        if broke is not None and t - broke > 2.6: break
        if broke is None and t > max_secs: broke = t
    return V.close(A)


def _gear(c, x, y, a, R=34, teeth=10):
    path = skia.Path()
    for j in range(teeth * 2):
        r_ = R if j % 2 == 0 else R * 0.74
        for s in (-0.5, 0.5):
            ang = a + (j + s * 0.85) * math.pi / teeth
            (path.moveTo if (j == 0 and s == -0.5) else path.lineTo)(x + r_ * math.cos(ang), y + r_ * math.sin(ang))
    path.close()
    sh = skia.GradientShader.MakeLinear([(x - R, y - R), (x + R, y + R)], [rgb((250, 250, 255)), rgb((140, 140, 150))])
    c.drawPath(path, fill_paint((200, 200, 210), shader=sh)); c.drawPath(path, stroke_paint((90, 90, 100), 2))
    c.drawCircle(x, y, R * 0.32, fill_paint((70, 70, 80))); c.drawCircle(x, y, R * 0.16, fill_paint((190, 190, 200)))


def fit_claw(start=1, lo=24, hi=36, **kw):
    for s in range(start, start + 30):
        d = claw_flood(None, s, dry=True, **kw)
        if lo <= d <= hi: return s, d
    return start, d


# ====================================================================== 3. OVERFLOW PENDULUM (pymunk)
OV_PAL = [(255, 120, 120), (255, 200, 110), (140, 240, 160), (120, 200, 255), (220, 140, 255), (255, 150, 210), (250, 250, 160)]


def _bowl_geom(cx, cy, RI, piv, Rb, half=40.0):
    floor = [(piv[0] + Rb * math.sin(a), piv[1] + Rb * math.cos(a)) for a in np.radians(np.linspace(half, -half, 40))]
    def ring(deg): return (cx + RI * math.cos(math.radians(deg)), cy + RI * math.sin(math.radians(deg)))
    flapL = [ring(200), (cx - 240, cy - 210), ring(222)]
    flapR = [ring(-20), (cx + 240, cy - 210), ring(-42)]
    tipy = cy - 210
    return floor, flapL, flapR, tipy


def overflow_pendulum(path, seed=1, text=True, dry=False, r=9.0, bob=80.0, g=1300.0, cd=0.3, cap_balls=1500, pace=20.0,
                      amp=0.66, spill_n=90, palette=None, l1="WILL IT OVERFLOW?", l2="EVERY HIT SPLITS A BALL", max_secs=33):
    rng = np.random.default_rng(seed); pal = palette or OV_PAL
    cx, cy, RI = W / 2, 900.0, 430.0
    piv = (cx, cy - RI + 30); L = 520.0
    floor, flapL, flapR, tipy = _bowl_geom(cx, cy, RI, piv, L + bob + 22)
    sp = pymunk.Space(); sp.gravity = (0, g); sp.iterations = 14
    statics = []
    def segs(pts):
        for a_, b_ in zip(pts[:-1], pts[1:]):
            s = pymunk.Segment(sp.static_body, a_, b_, 12); s.elasticity = 0.75; s.friction = 0.35; statics.append(s)
    segs(floor); segs(flapL); segs(flapR)
    segs([(cx + RI * math.cos(a), cy + RI * math.sin(a)) for a in np.linspace(0, TAU, 97)])
    sp.add(*statics)
    # the wrecking ball follows an exact pendulum swing (kinematic), so a pile of balls can never jam it
    bb_ = pymunk.Body(body_type=pymunk.Body.KINEMATIC); om = math.sqrt(g / L) * 1.15; ph0 = rng.uniform(0, TAU)
    def bob_at(t_):
        a_ = amp * math.sin(om * t_ + ph0); return np.array([piv[0] + L * math.sin(a_), piv[1] + L * math.cos(a_)])
    bb_.position = tuple(bob_at(0))
    bs = pymunk.Circle(bb_, bob); bs.elasticity = 0.95; bs.friction = 0.2; bs.collision_type = 2
    sp.add(bb_, bs)
    balls = []
    def add_ball(p, v):
        b = pymunk.Body(1, pymunk.moment_for_circle(1, 0, r)); b.position = tuple(p); b.velocity = tuple(v)
        s = pymunk.Circle(b, r); s.elasticity = 0.8; s.friction = 0.25; s.collision_type = 1
        sp.add(b, s); balls.append([b, s, pal[int(rng.integers(len(pal)))], -9.0])
    add_ball((cx + rng.uniform(-150, 150), cy - 120), (rng.uniform(-200, 200), 0))
    hits = []
    sp.on_collision(1, 2, begin=lambda arb, s, d: hits.append(arb.shapes[0] if arb.shapes[0].collision_type == 1 else arb.shapes[1]))
    A = Audio(); V = Writer(path, dry); sub = 6; dt = 1 / (FPS * sub); fr = Frame()
    f = 0; broke = None; shards = []; last_clack = -1; last_note = -1
    A.tone(0, E.midi(36), 0.12, max_secs + 4, "pad")
    while True:
        t = f / FPS
        if PREV and t > PREV: break
        for s_ in range(sub):
            ts = t + s_ * dt
            # keep the swing going (a hidden motor that only tops up lost energy)
            h = bb_.position[1] - piv[1]; ke = 0.5 * 400 * (bb_.velocity[0] ** 2 + bb_.velocity[1] ** 2); pe = 400 * g * (L - h)
            p0, p1 = bob_at(ts), bob_at(ts + dt); bb_.position = tuple(p0); bb_.velocity = tuple((p1 - p0) / dt)
            hits.clear(); sp.step(dt)
            if broke is None and hits:
                if ts - last_clack > 0.09:
                    A.tone(ts, 900, 0.12, 0.10, "clack"); A.impact(ts, math.hypot(*bb_.velocity), 660, "chime", 0.2, unit=50); last_clack = ts
                lookup = {id(b[1]): b for b in balls}
                target = 2 ** (min(1.0, ts / pace) * math.log2(cap_balls)); room = min(cap_balls, int(target * 1.3) + 1) - len(balls)
                for shp in hits:
                    b = lookup.get(id(shp))
                    if b is None or room <= 0 or ts - b[3] < cd or math.hypot(*bb_.velocity) < 40: continue
                    b[3] = ts; room -= 1
                    ang = rng.uniform(0, TAU); p = b[0].position + (2.1 * r * math.cos(ang), 2.1 * r * math.sin(ang))
                    v = b[0].velocity; add_ball(p, (v[0] + 220 * math.cos(ang), v[1] - abs(250 * math.sin(ang))))
                    balls[-1][3] = ts
                    if ts - last_note > 0.05: A.note(ts, 64 + min(int(math.log2(len(balls))), 12) * 2, 0.14, 0.3); last_note = ts
            if broke is None:
                above = sum(1 for b in balls if b[0].position[1] < tipy - 10)
                if above >= spill_n or len(balls) >= cap_balls: broke = ts
            if broke is not None and not shards:
                sp.remove(*statics); A.tone(ts, 0, 0.8, 2.4, "crash"); A.chord(ts + 0.15, 53, 0.3)
                for a0 in np.linspace(0, TAU, 30, endpoint=False):
                    shards.append([cx + RI * math.cos(a0), cy + RI * math.sin(a0), math.cos(a0) * rng.uniform(250, 700), math.sin(a0) * rng.uniform(250, 700) - 300, a0, rng.uniform(-5, 5)])
                for b in balls: b[0].velocity = tuple(np.array(b[0].velocity) + rng.normal(0, 250, 2) + (0, -200))
        if broke is not None:
            for sh in shards: sh[0] += sh[2] / FPS; sh[1] += sh[3] / FPS; sh[3] += 1300 / FPS; sh[4] += sh[5] / FPS
        if f % FPS == 0: LOG.append((round(t), len(balls), sum(1 for b in balls if b[0].position[1] < tipy - 10)))
        if dry: V.write(None)
        else:
            c = fr.c; fr.clear((22, 22, 34), (12, 12, 20))
            u = (t - broke) if broke is not None else -1
            ghost = 1.0 if broke is None else (0.0 if u < 1.8 else min(1, (u - 1.8) / 0.7) * 0.85)
            if ghost > 0: _draw_bowl(c, cx, cy, RI, floor, flapL, flapR, ghost)
            for sx_, sy_, _, _, a0, _ in shards:
                c.save(); c.translate(sx_, sy_); c.rotate(math.degrees(a0) + 90)
                c.drawRoundRect(skia.Rect(-46, -20, 46, 20), 6, 6, fill_paint((120, 116, 150))); c.restore()
            draw_balls(c, [b[0].position for b in balls], [b[2] for b in balls], r)
            bp = bb_.position
            for j in range(1, 16):                                            # chain
                q = (piv[0] + (bp[0] - piv[0]) * j / 16, piv[1] + (bp[1] - piv[1]) * j / 16)
                ang = math.degrees(math.atan2(bp[1] - piv[1], bp[0] - piv[0]))
                c.save(); c.translate(*q); c.rotate(ang + (0 if j % 2 else 90) * 0)
                if j % 2: c.drawOval(skia.Rect(-15, -7, 15, 7), stroke_paint((190, 190, 205), 4))
                else: c.drawLine(-14, 0, 14, 0, stroke_paint((160, 160, 175), 4))
                c.restore()
            c.drawCircle(piv[0], piv[1], 18, fill_paint((200, 200, 215))); c.drawCircle(piv[0], piv[1], 7, fill_paint((60, 60, 70)))
            c.drawCircle(bp[0] + 8, bp[1] + 14, bob, fill_paint((0, 0, 0), 110, blur=14))
            draw_sprite(c, sphere((205, 205, 218), 192, 0.9, 0.55), bp[0], bp[1], bob)
            if text:
                if broke is None:
                    title(c, l1, l2, 200, 76); draw_text(c, f"{len(balls):,} BALLS", W / 2, 1460, 76, YELLOW)
                else:
                    title(c, "IT OVERFLOWED!", f"{len(balls):,} BALLS", 220, 92)
            V.write(fr)
        f += 1
        if broke is not None and t - broke > 2.8: break
        if broke is None and t > max_secs: broke = t
    return V.close(A)


def _draw_bowl(c, cx, cy, RI, floor, flapL, flapR, a=1.0):
    al = int(255 * a)
    sh = skia.GradientShader.MakeLinear([(cx, cy - RI), (cx, cy + RI)], [rgb((158, 154, 190), al), rgb((96, 92, 124), al)])
    body = skia.Path(); body.moveTo(*floor[0])
    for q in floor[1:]: body.lineTo(*q)
    a_end = math.degrees(math.atan2(floor[-1][1] - cy, floor[-1][0] - cx)); a_st = math.degrees(math.atan2(floor[0][1] - cy, floor[0][0] - cx))
    body.arcTo(skia.Rect(cx - RI, cy - RI, cx + RI, cy + RI), a_end, -((a_end - a_st) % 360), False); body.close()
    for p_ in (body, polyline(flapL, True), polyline(flapR, True)):
        c.drawPath(p_, fill_paint((130, 126, 160), al, shader=sh)); c.drawPath(p_, stroke_paint((205, 200, 235), 4, al))
    for j in range(1, 8):                                    # tile seams in the floor
        q = floor[j * 5]; d = (q[0] - cx, q[1] - cy); n_ = math.hypot(*d)
        c.drawLine(q[0], q[1], cx + d[0] / n_ * RI, cy + d[1] / n_ * RI, stroke_paint((84, 80, 108), 3, al))
    c.drawCircle(cx, cy, RI + 14, stroke_paint((72, 70, 96), 30, al))
    c.drawCircle(cx, cy, RI + 29, stroke_paint((120, 116, 150), 3, al))


def fit_overflow(start=1, lo=24, hi=36, **kw):
    for s in range(start, start + 30):
        d = overflow_pendulum(None, s, dry=True, **kw)
        if lo <= d <= hi: return s, d
    return start, d


# ====================================================================== 4. FACT WHAT-IF (voice) helpers
def _stars(rng, n=260):
    return np.c_[rng.uniform(-200, W + 200, n), rng.uniform(-200, H + 200, n), rng.uniform(0.3, 1.0, n), rng.uniform(0, TAU, n)]


def _draw_stars(c, S, t, dx=0, dy=0, zoom=1.0):
    for x, y, b, p in S:
        a = int(255 * b * (0.7 + 0.3 * math.sin(t * 3 + p)))
        X = W / 2 + (x - W / 2) * zoom + dx * b; Y = H / 2 + (y - H / 2) * zoom + dy * b
        c.drawCircle(X, Y, 1.6 * b, fill_paint((255, 255, 255), a))


def _planet(c, x, y, R, col, kind=None, atm=True):
    if atm: draw_sprite(c, glow_dot(tuple(int(v) for v in col), a=110), x, y, R * 1.5)
    hi = mix(col, (255, 255, 255), 0.35); lo = mix(col, (0, 0, 0), 0.75)
    c.drawCircle(x, y, R, fill_paint(col, shader=skia.GradientShader.MakeRadial((x - R * 0.35, y - R * 0.35), R * 1.6, [rgb(hi), rgb(col), rgb(lo)], [0, 0.4, 1])))
    if kind == "earth":
        c.save(); p = skia.Path(); p.addCircle(x, y, R); c.clipPath(p, doAntiAlias=True)
        for ox, oy, a_, b_ in ((-0.3, -0.2, 0.45, 0.3), (0.35, 0.25, 0.35, 0.45), (-0.1, 0.55, 0.5, 0.18), (0.2, -0.6, 0.3, 0.15)):
            c.drawOval(skia.Rect(x + (ox - a_) * R, y + (oy - b_) * R, x + (ox + a_) * R, y + (oy + b_) * R), fill_paint((70, 160, 90), 230))
        c.drawCircle(x + R * 0.3, y + R * 0.3, R * 1.05, fill_paint((0, 0, 20), 120, blur=R * 0.25))
        c.restore()
    if kind == "gas":
        c.save(); p = skia.Path(); p.addCircle(x, y, R); c.clipPath(p, doAntiAlias=True)
        for j in range(-4, 5): c.drawRect(skia.Rect(x - R, y + j * R * 0.22 - R * 0.05, x + R, y + j * R * 0.22 + R * 0.05), fill_paint(mix(col, (255, 255, 255), 0.15), 50))
        c.restore()


def _person(c, x, y, s, skin, shirt, arm=0.0):
    c.drawRoundRect(skia.Rect(x - 22 * s, y, x + 22 * s, y + 70 * s), 14 * s, 14 * s, fill_paint(shirt))
    c.drawCircle(x, y - 16 * s, 17 * s, fill_paint(skin))
    c.drawCircle(x, y - 22 * s, 17 * s, fill_paint((40, 30, 25)) if False else fill_paint(skin))
    if arm > 0:
        ax, ay = x + 18 * s, y + 6 * s; hx, hy = ax + 6 * s, ay - 62 * s * arm
        c.drawLine(ax, ay, hx, hy, stroke_paint(skin, 11 * s))
        return hx, hy
    return None


def fact_what_if(path, seed=1, text=True, dry=False, idea="laser_planet", target="uranus", spec_json=""):
    """Narrated physics/space 'what if' Short, free local AI voice + word-by-word captions.
    idea: laser_planet | car_to_sun | drop_no_air (ready, numbers computed), or leave idea and give spec_json.
    spec_json: a NEW fact as JSON {"title":..., "lines":[{"say":..., "scene":...}, ...]}; scenes: crowd streak travel scale
    spread counter fall orbit card (fields in facts.SPEC_GUIDE). 7-10 lines, 25-38 s, real textbook numbers only."""
    import facts
    if spec_json:
        spec = json.loads(spec_json) if isinstance(spec_json, str) else spec_json
    elif idea == "laser_planet":
        spec = facts.fact_laser_spec(str(target).lower())
    else:
        spec = facts.EXAMPLES[idea]()
    return facts.fact_short(path, spec, seed, text, dry)


# ====================================================================== menu entries
TEMPLATES = {
    "jelly_drop": {"fn": jelly_drop, "fit": None, "inspo": "Video-26144", "engine": "engine2",
                   "desc": "1,000-ball jelly sheet drops on a trampoline plate; kicks send real impact waves (dome/bowl/funnel/ring/tilt); flies off the top to loop.",
                   "knobs": ["kicks", "every", "n", "k (stiffness)", "e (bounce)", "hue0", "hue_span", "elev", "l1", "l2"],
                   "title": "1,000 balls on a trampoline… wait for the last bounce 🤯 #shorts #satisfying"},
    "claw_flood": {"fn": claw_flood, "fit": fit_claw, "inspo": "Video-17387", "engine": "engine2",
                   "desc": "Wandering gear swings 2 independent claws; every claw hit adds a ball (zero-g, elastic); colour per doubling; circle breaks.",
                   "knobs": ["cap_balls", "r", "ra", "sweep", "pace", "cd", "wander", "palette", "l1", "l2"],
                   "title": "Every claw hit adds a ball… will the circle break? ⚙️ #shorts #satisfying"},
    "overflow_pendulum": {"fn": overflow_pendulum, "fit": fit_overflow, "inspo": "Video-18009", "engine": "engine2",
                          "desc": "Real pendulum in a bowl; every hit splits a ball; bouncy spray; bowl shatters on overflow; empty bowl fades back (loop).",
                          "knobs": ["r", "bob", "g", "cd", "cap_balls", "pace", "amp", "spill_n", "palette", "l1", "l2"],
                          "title": "Will it overflow? Every hit splits a ball 😳 #shorts #satisfying"},
    "fact_what_if": {"fn": fact_what_if, "fit": None, "inspo": "Video-10954", "engine": "engine2 + Kokoro voice",
                     "desc": "Narrated physics/space 'what if' Short. Use a ready idea or write a NEW fact as spec_json (facts.SPEC_GUIDE).",
                     "knobs": ["idea", "target", "spec_json"], "title": "<from spec>"},
}
