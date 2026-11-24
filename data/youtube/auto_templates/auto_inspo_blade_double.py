from auto_bounce2 import *
"""Inspo in-20261123-njem (Bounce Theory): 'EVERY CUT DOUBLES A TOMATO'.

One cute tomato bounces (gravity) inside a white ring while a katana spins round a pivot near the centre. Every time the
blade slices a tomato it becomes two, pushed apart from the blade line. Slow start, then the pile at the bottom gets swept
every turn and the count explodes; the tomatoes ripen green -> yellow -> red as the count grows. When the ring is full it
breaks, everything spills out, and an empty ring with the sword fades back in (loops to the start).

blade_double(path, seed=1, text=True, dry=False, **knobs) -> seconds (about 30-36 s).
"""

STAGES = [(98, 196, 70), (150, 205, 60), (245, 200, 50), (250, 150, 40), (240, 90, 40), (222, 52, 38)]
LOG = []


def _stage_col(count, cap):
    k = min(1.0, math.log2(max(1, count)) / math.log2(max(2, cap)) * 1.6)
    i = k * (len(STAGES) - 1); a = int(i); b = min(a + 1, len(STAGES) - 1)
    return tuple(int(v) for v in mix(STAGES[a], STAGES[b], i - a))


_TOM = {}


def _tomato(col, size=72):
    """Tomato sprite: shaded body, leafy top, two eyes. Cached per colour."""
    key = (col, size)
    if key in _TOM: return _TOM[key]
    s = skia.Surface(size, size); c = s.getCanvas(); c.clear(skia.Color(0, 0, 0, 0)); r = size / 2
    body = sphere(col, size, 0.6, 0.5)
    c.drawImageRect(body, skia.Rect(1, 3, size - 1, size - 1), skia.SamplingOptions(skia.FilterMode.kLinear))
    leaf = skia.Path(); cx_, cy_ = r, size * 0.16
    for j in range(10):
        a = -math.pi / 2 + j * math.pi / 5; rr = size * (0.2 if j % 2 == 0 else 0.07)
        (leaf.moveTo if j == 0 else leaf.lineTo)(cx_ + rr * math.cos(a) * 1.3, cy_ + rr * math.sin(a) * 0.8 + size * 0.03)
    leaf.close(); c.drawPath(leaf, fill_paint((60, 150, 50))); c.drawPath(leaf, stroke_paint((30, 90, 30), 1.2))
    for ex in (-0.17, 0.17):
        c.drawCircle(r + ex * size, size * 0.55, size * 0.11, fill_paint((255, 255, 255)))
        c.drawCircle(r + ex * size + size * 0.02, size * 0.57, size * 0.06, fill_paint((20, 20, 20)))
    img = s.makeImageSnapshot(); _TOM[key] = img
    return img


def _sword(c, px, py, ang, hl, bl):
    """Katana from the pivot: gold-wrapped handle (hl), small guard, silver blade (bl) with a pointed tip."""
    c.save(); c.translate(px, py); c.rotate(math.degrees(ang))
    c.drawRoundRect(skia.Rect(-6, -9, hl + 4, 9), 4, 4, fill_paint((0, 0, 0), 120, blur=5))
    c.drawRoundRect(skia.Rect(0, -8, hl, 8), 3, 3, fill_paint((205, 160, 60)))
    for j in range(0, int(hl), 11):
        c.drawLine(j, -8, j + 8, 8, stroke_paint((95, 65, 25), 3, cap=False))
    c.drawRoundRect(skia.Rect(hl, -12, hl + 9, 12), 2, 2, fill_paint((60, 55, 50)))
    blade = skia.Path(); x0 = hl + 9
    blade.moveTo(x0, -6); blade.lineTo(x0 + bl - 26, -5); blade.lineTo(x0 + bl, 2); blade.lineTo(x0 + bl - 30, 6); blade.lineTo(x0, 6); blade.close()
    sh = skia.GradientShader.MakeLinear([(0, -6), (0, 6)], [rgb((250, 250, 255)), rgb((190, 195, 210)), rgb((120, 125, 140))], [0, 0.45, 1])
    c.drawPath(blade, fill_paint((200, 200, 210), shader=sh)); c.drawPath(blade, stroke_paint((90, 95, 110), 1.2))
    c.drawLine(x0 + 4, 1, x0 + bl - 34, 2, stroke_paint((255, 255, 255), 1.4, 180))
    c.restore()


def blade_double(path, seed=1, text=True, dry=False, R=440.0, r=14.5, cap=820, pace=27.0, g=500.0, spin=2.3, blade=None,
                 cd=0.15, first_cut=3.0, l1="EVERY CUT DOUBLES A TOMATO", noun="TOMATOES", max_secs=33):
    rng = np.random.default_rng(seed)
    cx, cy = W / 2, 960.0
    sp = pymunk.Space(); sp.gravity = (0, g); sp.iterations = 10
    arena = []
    for a0 in np.linspace(0, TAU, 121)[:-1]:
        a1 = a0 + TAU / 120
        s = pymunk.Segment(sp.static_body, (cx + (R + 8) * math.cos(a0), cy + (R + 8) * math.sin(a0)),
                           (cx + (R + 8) * math.cos(a1), cy + (R + 8) * math.sin(a1)), 8)
        s.elasticity = 0.92; s.friction = 0.2; arena.append(s)
    sp.add(*arena)
    hl = 80.0; piv = (cx, cy)
    if blade is None: blade = R - hl - 9 - 6          # the tip skims the ring, so nothing can hide from it
    sw = pymunk.Body(body_type=pymunk.Body.KINEMATIC); sw.position = piv
    cut_seg = pymunk.Segment(sw, (hl + 9, 0), (hl + 9 + blade, 0), 6); cut_seg.collision_type = 2; cut_seg.sensor = True   # the blade slices through (it does not shove the pile)
    grip = pymunk.Segment(sw, (0, 0), (hl + 9, 0), 9); grip.elasticity = 0.6
    sp.add(sw, cut_seg, grip)
    a_ph = rng.uniform(0, TAU); dirn = rng.choice([-1, 1])
    def ang_at(t): return a_ph + dirn * (spin * t + 0.35 * math.sin(0.6 * t))
    toms = []
    def add(p, v, born):
        b = pymunk.Body(1, pymunk.moment_for_circle(1, 0, r)); b.position = tuple(p); b.velocity = tuple(v)
        s = pymunk.Circle(b, r); s.elasticity = 0.82; s.friction = 0.3; s.collision_type = 1
        sp.add(b, s); toms.append([b, s, born])
    a = rng.uniform(0, TAU); add((cx + 260 * math.cos(a), cy - 200), (rng.uniform(-260, 260), -100), -9)
    hits = []
    sp.on_collision(1, 2, begin=lambda arb, s_, d: hits.append(arb.shapes[0] if arb.shapes[0].collision_type == 1 else arb.shapes[1]))
    A = Audio(); V = Writer(path, dry); sub = 3; dt = 1 / (FPS * sub); fr = Frame()
    # sound: ONLY the split sound (Omar, 2026-11-24: no bed, no swoosh, no crash)
    f = 0; broke = None; shards = []; last_snd = -1; last_sw = -1; flashes = []; reset_t = None
    while True:
        t = f / FPS
        if PREV and t > PREV: break
        for s_ in range(sub):
            ts = t + s_ * dt
            a0, a1 = ang_at(ts), ang_at(ts + dt)
            sw.angle = a0; sw.angular_velocity = (a1 - a0) / dt; sw.position = piv; sw.velocity = (0, 0)
            hits.clear(); sp.step(dt)
            if broke is None and hits and ts >= first_cut:
                look = {id(x[1]): x for x in toms}
                target = 2 ** (min(1.0, max(0.0, ts - first_cut) / (pace - first_cut)) * math.log2(cap))
                room = min(cap, int(target * 1.35) + 1) - len(toms)
                d = (math.cos(a0), math.sin(a0)); nrm = np.array((-d[1], d[0]))
                for shp in hits:
                    tm = look.get(id(shp))
                    if tm is None or room <= 0 or ts - tm[2] < cd: continue
                    p = np.array(tm[0].position); side = 1 if np.dot(p - piv, nrm) >= 0 else -1
                    q = p + nrm * side * 2.1 * r
                    dq = math.hypot(q[0] - cx, q[1] - cy)
                    if dq > R - r - 3: q = np.array((cx, cy)) + (q - (cx, cy)) * (R - r - 3) / dq   # keep the new half inside the ring
                    room -= 1; tm[2] = ts
                    v = np.array(tm[0].velocity); kick = 380 + rng.uniform(0, 120)
                    tm[0].velocity = tuple(v - nrm * side * kick)
                    add(q, v + nrm * side * kick, ts)
                    flashes.append([q[0], q[1], ts])
                    if ts - last_snd > 0.045:
                        lv = math.log2(len(toms))
                        A.note(ts, 62 + min(int(lv * 2.2), 30), 0.13, 0.22, "pluck"); A.tone(ts, 0, 0.10, 0.08, "pop"); last_snd = ts
            if broke is None and len(toms) >= cap: broke = ts
            if broke is not None and not shards:
                sp.remove(*arena)
                for a_ in np.linspace(0, TAU, 36, endpoint=False):
                    shards.append([cx + R * math.cos(a_), cy + R * math.sin(a_), math.cos(a_) * rng.uniform(300, 800), math.sin(a_) * rng.uniform(300, 800) - 250, a_, rng.uniform(-6, 6)])
                for tm in toms:
                    p = np.array(tm[0].position) - (cx, cy); tm[0].velocity = tuple(np.array(tm[0].velocity) + p * 2.4 + rng.normal(0, 120, 2))
                sp.gravity = (0, 1400)
        if broke is not None:
            for sh in shards: sh[0] += sh[2] / FPS; sh[1] += sh[3] / FPS; sh[3] += 1400 / FPS; sh[4] += sh[5] / FPS
            if reset_t is None and t - broke > 2.6:
                reset_t = t
                for tm in toms: sp.remove(tm[0], tm[1])
                toms.clear()
        if f % FPS == 0: LOG.append((round(t), len(toms)))
        if dry: V.write(None)
        else:
            c = fr.c; fr.clear((0, 0, 0))
            ring_a = 255 if broke is None else (0 if reset_t is None else int(255 * min(1, (t - reset_t) / 0.6)))
            if ring_a: c.drawCircle(cx, cy, R + 8, stroke_paint((245, 245, 245), 16, ring_a))
            for sx_, sy_, _, _, a_, rot in shards:
                if reset_t is not None: break
                c.save(); c.translate(sx_, sy_); c.rotate(math.degrees(a_) + 90)
                c.drawRoundRect(skia.Rect(-38, -8, 38, 8), 4, 4, fill_paint((245, 245, 245))); c.restore()
            col = _stage_col(len(toms) if broke is None else cap, cap); img = _tomato(col)
            for tm in toms:
                x, y = tm[0].position
                if -40 < y < H + 40: draw_sprite(c, img, x, y, r * 1.12)
            for fl in flashes:
                u = t - fl[2]
                if 0 <= u < 0.2: draw_sprite(c, glow_dot((255, 255, 255), a=160), fl[0], fl[1], 26 * (1 - u / 0.2) + 8)
            flashes[:] = [fl for fl in flashes if t - fl[2] < 0.2]
            _sword(c, piv[0], piv[1], ang_at(t), hl, blade)
            c.drawCircle(piv[0], piv[1], 7, fill_paint((40, 40, 40)))
            if text:
                n_show = 0 if reset_t is not None else len(toms)
                ic = _tomato(STAGES[-1]); tw = E.text_w(l1, 60); x0 = W / 2 - (tw + 66) / 2
                draw_sprite(c, ic, x0 + 24, 352, 24); draw_text(c, l1, x0 + 66, 372, 60, WHITE, stroke=0, shadow=False, align="left", maxw=960)
                num = f"{n_show:,}"; w1 = E.text_w(num, 66); w2 = E.text_w(noun, 30); tot = 52 + w1 + 14 + w2; x0 = W / 2 - tot / 2
                draw_sprite(c, _tomato(col), x0 + 20, 448, 20)
                draw_text(c, num, x0 + 52, 470, 66, (255, 170, 40), stroke=0, shadow=False, align="left")
                draw_text(c, noun, x0 + 52 + w1 + 14, 466, 30, WHITE, stroke=0, shadow=False, align="left")
            V.write(fr)
        f += 1
        if reset_t is not None and t - reset_t > 1.0: break
        if broke is None and t > max_secs: broke = t
    return V.close(A)


def fit_blade(start=1, lo=26, hi=38, **kw):
    for s in range(start, start + 30):
        d = blade_double(None, s, dry=True, **kw)
        if lo <= d <= hi: return s, d
    return start, d


TEMPLATES = {"blade_double": {"fn": blade_double, "fit": fit_blade, "inspo": "in-20261123-njem", "engine": "engine2",
                              "desc": "Katana spins inside a ring; every slice splits a bouncing cartoon tomato in two; ripens green->red; ring breaks when full, resets (loop).",
                              "knobs": ["R", "r", "cap", "pace", "g", "spin", "blade", "cd", "first_cut", "l1", "noun"],
                              "title": "Every cut doubles a tomato… 🍅🗡️ #shorts #satisfying"}}
