from auto_bounce2 import *
"""Inspo in-20261123-wdwa (Bounce Theory): '100 AIs learning to fly through a cave'.

A real tiny neuro-evolution: every agent is a 4-weight controller (offset from the cave's centre just ahead, further ahead,
its own vertical speed, bias) steering a cyan dot through a neon cave that narrows as it goes. Touching a wall = out
(yellow ring + pop). After each generation the furthest flyers are copied with mutations. All 20 generations are really
simulated; the video shows generations 1, 2, 4 and the last one, then the "100 of 100 make it through" card.

cave_swarm(path, seed=1, text=True, dry=False, **knobs) -> seconds (about 18-20 s).
"""

BG = (36, 31, 46); INSIDE = (17, 15, 24); WALL = (196, 160, 255); WALL_GLOW = (150, 80, 255)
AGENT = (110, 235, 255); RING = (255, 196, 60); GREEN = (140, 220, 110)
HUD_BOTTOM = 470
LOG = []   # (generation, still flying when its clip ends), for tuning


def _cave(rng, L, w0, w1, amp):
    p = rng.uniform(0, TAU, 3)
    def cy(x):
        x = np.asarray(x, float)
        ramp = np.clip(x / 500.0, 0, 1)                      # the entrance is straight, then the waves start
        return 1010 + ramp * (amp * np.sin(x / 300.0 + p[0]) + amp * 0.45 * np.sin(x / 131.0 + p[1]) + amp * 0.2 * np.sin(x / 71.0 + p[2]))
    def hw(x):
        return w0 + (w1 - w0) * np.clip(np.asarray(x, float) / L, 0, 1)
    return cy, hw


def _fly(G, cy, hw, L, V, rng, steps, dt, look, acc, jitter, r, rec=None):
    """Run one generation (n agents, genomes G [n,4]). Returns distance reached and (optionally) per-step positions."""
    n = len(G)
    x = rng.uniform(0, 170, n); y = cy(x) + rng.uniform(-0.7, 0.7, n) * hw(x); vy = rng.uniform(-160, 160, n)
    alive = np.ones(n, bool); dist = np.zeros(n); died = np.full(n, -1); clear = np.full(n, 1e9)
    noise = rng.standard_normal((steps, n)) * jitter
    for k in range(steps):
        xa = x + look; xb = x + 2.4 * look
        e1 = (y - cy(xa)) / hw(xa); e2 = (y - cy(xb)) / hw(xb)
        u = np.tanh(G[:, 0] * e1 + G[:, 1] * e2 + G[:, 2] * vy / V + G[:, 3] + noise[k])
        vy = np.where(alive, vy + u * acc * dt, 0.0); vy = np.clip(vy, -1.4 * V, 1.4 * V)
        x = np.where(alive, x + V * dt, x); y = np.where(alive, y + vy * dt, y)
        gap = hw(x) - r - np.abs(y - cy(x)); hit = alive & (gap < 0)
        clear = np.where(alive & (x > 200), np.minimum(clear, gap), clear)
        died[hit] = k; alive &= ~hit
        dist = np.where(alive, x, dist)
        if rec is not None: rec.append((x.copy(), y.copy(), alive.copy()))
        if not alive.any() or x[alive].min() > L: break
    return dist + 4.0 * np.clip(clear, 0, 200) * alive, died


def cave_swarm(path, seed=1, text=True, dry=False, n=100, gens=(1, 2, 4, 20), L=4600.0, V=760.0, w0=235.0, w1=100.0, amp=215.0,
               sigma0=0.35, sigma1=0.02, jitter=0.2, elite_n=3, l1="100 AIs learning to fly through a cave", l2="it gets narrower the deeper they go",
               end2="{last} generations of trial and error", end3="nobody told them what a wall is"):
    rng = np.random.default_rng(seed)
    cy, hw = _cave(rng, L, w0, w1, amp)
    r = 9.0; look = 140.0; acc = 7600.0; sub = 2; dt = 1 / (FPS * sub)
    steps = int((L + 120) / V / dt) + 2
    last = max(gens)
    # --- evolve (all generations really run; only the shown ones are recorded)
    G = rng.normal(0, 2.2, (n, 4))
    shown = {}
    for g in range(1, last + 1):
        rec = [] if g in gens else None
        dist, died = _fly(G, cy, hw, L, V, np.random.default_rng(seed * 1000 + g), steps, dt, look, acc, jitter * (1 - 0.9 * (g / last) ** 2), r, rec)
        if rec is not None: shown[g] = (rec, died)
        order = np.argsort(-dist); elite = G[order[:max(1, elite_n)]]
        sig = sigma0 * (sigma1 / sigma0) ** ((g - 1) / max(1, last - 2))
        kids = elite[rng.integers(len(elite), size=n - len(elite))] + rng.normal(0, sig, (n - len(elite), 4))
        G = np.r_[elite, kids]
    # --- timeline: each shown generation gets a slot; the last one flies to the exit
    slots = []
    for g in gens:
        rec, died = shown[g]
        k_end = len(rec) - 1
        if g != last:
            dead_all = int(died.max()) if (died >= 0).all() else k_end
            k_end = min(k_end, int(3.1 * FPS * sub), dead_all + int(0.5 * FPS * sub))
        slots.append((g, rec, died, max(k_end, int(1.2 * FPS * sub))))
        LOG.append((g, int(rec[min(slots[-1][3], len(rec) - 1)][2].sum())))
    card_t = 2.8
    total = sum(s[3] for s in slots) / (FPS * sub) + card_t
    A = Audio(); V_ = Writer(path, dry); fr = Frame()
    # upbeat synth bed: 120 bpm arpeggio over a 4-chord loop + soft kick
    prog = [(57, 60, 64), (53, 57, 60), (48, 52, 55), (55, 59, 62)]
    beat = 0.5; nb = int(total / beat * 2) + 2
    for j in range(nb):
        t0 = j * beat / 2; ch = prog[(j // 8) % 4]
        A.note(t0, ch[j % 3] + 12 + (12 if j % 4 == 3 else 0), 0.07, 0.25, "pluck")
        if j % 2 == 0: A.tone(t0, 55, 0.16, 0.25, "thud")
        if j % 8 == 0: A.note(t0, ch[0] - 12, 0.06, beat * 4, "pad")
    rings = []; t = 0.0; f = 0; last_pop = -1
    trail = 14
    for si, (g, rec, died, k_end) in enumerate(slots):
        cam = 0.0
        A.tone(t, 900, 0.18, 0.35, "whoosh")
        k = 0
        while k <= k_end:
            x, y, al = rec[min(k, len(rec) - 1)]
            # crashes in this frame
            for kk in range(k, min(k + sub, len(rec))):
                for i in np.where(died == kk)[0]:
                    xx, yy, _ = rec[kk]; rings.append([xx[i], yy[i], t])
                    if t - last_pop > 0.035:
                        A.tone(t, 0, 0.22, 0.12, "pop"); A.note(t, 76 + int(rng.integers(0, 8)), 0.05, 0.2, "chime"); last_pop = t
            if al.any():
                lead = np.percentile(x[al], 60)
            else:
                lead = cam + 330
            cam += (max(0.0, lead - 330) - cam) * 0.12
            alive_n = int(al.sum())
            if dry: V_.write(None)
            else:
                c = fr.c; fr.clear(BG)
                _draw_cave(c, cy, hw, cam, L)
                for rg in rings:
                    u = (t - rg[2]) / 0.55
                    if 0 <= u < 1:
                        sx = rg[0] - cam; a = int(230 * (1 - u))
                        draw_sprite(c, glow_dot(RING, a=90), sx, rg[1], 22 + 30 * u)
                        c.drawCircle(sx, rg[1], 10 + 30 * u, stroke_paint(RING, 3, a)); c.drawCircle(sx, rg[1], 6 + 14 * u, stroke_paint(RING, 2, a // 2))
                        c.drawCircle(sx, rg[1], 5, fill_paint(RING, a))
                k0 = max(0, k - trail * sub)
                idx = np.where(al)[0]
                if len(idx):
                    hist = [rec[q] for q in range(k0, min(k + 1, len(rec)), sub)]
                    for q in range(1, len(hist)):
                        a = int(140 * q / len(hist))
                        p = stroke_paint(AGENT, 2, a)
                        for i in idx:
                            c.drawLine(hist[q - 1][0][i] - cam, hist[q - 1][1][i], hist[q][0][i] - cam, hist[q][1][i], p)
                    cols = [mix(AGENT, (255, 255, 255), 0.35 if g == last else 0.1)] * len(idx)
                    for i in idx: draw_sprite(c, glow_dot(AGENT, a=120), x[i] - cam, y[i], 26)
                    draw_balls(c, [(x[i] - cam, y[i]) for i in idx], [tuple(int(v) for v in cols[0])] * len(idx), r)
                if text: _hud(c, l1, l2, g, alive_n, n)
                if g == last and k > k_end - int(0.9 * FPS * sub):
                    u = 1 - (k_end - k) / (0.9 * FPS * sub); _card(c, n, alive_n, end2.format(last=last), end3, min(1, u * 1.5))
                V_.write(fr)
            f += 1; t = f / FPS; k += sub
        rings = [rg for rg in rings if t - rg[2] < 0.6]
    # payoff
    A.chord(t - 0.8, 72, 0.22, "chime"); A.tone(t - 0.8, E.midi(84), 0.12, 1.5, "chime")
    x, y, al = slots[-1][1][-1]
    vy = np.zeros(len(x)); rest = int(card_t * FPS)
    for q in range(rest):
        x = x + V / FPS
        if dry: V_.write(None)
        else:
            c = fr.c; fr.clear(BG)
            cam += (np.median(x[al]) - 330 - cam) * 0.05 if al.any() else 0
            _draw_cave(c, cy, hw, cam, L)
            idx = np.where(al)[0]
            for i in idx: draw_sprite(c, glow_dot(AGENT, a=120), x[i] - cam, y[i], 26)
            draw_balls(c, [(x[i] - cam, y[i]) for i in idx], [(200, 245, 255)] * len(idx), r)
            if text: _hud(c, l1, l2, last, int(al.sum()), n); _card(c, n, int(al.sum()), end2.format(last=last), end3, 1.0)
            fade = max(0.0, (q - rest + 0.35 * FPS) / (0.35 * FPS))
            if fade > 0: c.drawRect(skia.Rect(0, 0, W, H), fill_paint(BG, int(255 * fade)))
            V_.write(fr)
        f += 1; t = f / FPS
    return V_.close(A)


def _wall_pts(cy, hw, cam, L, side):
    xs = np.arange(cam - 80, cam + W + 80, 12.0)
    ys = cy(xs) + side * hw(np.minimum(xs, L))
    return list(zip(xs - cam, ys))


def _draw_cave(c, cy, hw, cam, L):
    top = _wall_pts(cy, hw, cam, L, -1); bot = _wall_pts(cy, hw, cam, L, 1)
    inside = polyline(top + bot[::-1], True)
    c.drawPath(inside, fill_paint(INSIDE))
    c.drawPath(inside, fill_paint((0, 0, 0), 90, blur=28))
    for pts in (top, bot):
        pth = polyline(pts)
        c.drawPath(pth, stroke_paint(WALL_GLOW, 16, 110, blur=14))
        c.drawPath(pth, stroke_paint(WALL, 3.2))


def _hud(c, l1, l2, g, alive, n):
    c.drawRect(skia.Rect(0, 0, W, HUD_BOTTOM), fill_paint((8, 7, 12)))
    draw_text(c, l1, W / 2, 205, 56, (250, 250, 250), stroke=0, shadow=False)
    draw_text(c, l2, W / 2, 272, 40, (255, 214, 70), stroke=0, shadow=False, bold=False)
    draw_text(c, "GENERATION", 70, 352, 24, (170, 170, 180), stroke=0, shadow=False, align="left", bold=False)
    draw_text(c, str(g), 70, 425, 70, (250, 250, 250), stroke=0, shadow=False, align="left")
    lab = "STILL FLYING"; draw_text(c, lab, W - 70 - E.text_w(lab, 24, False), 352, 24, (170, 170, 180), stroke=0, shadow=False, align="left", bold=False)
    val = f"{alive}/{n}"; col = GREEN if alive >= 0.8 * n else (250, 250, 250)
    draw_text(c, val, W - 70 - E.text_w(val, 70), 425, 70, col, stroke=0, shadow=False, align="left")
    c.drawRect(skia.Rect(70, 448, W - 70, 454), fill_paint((50, 50, 58)))
    c.drawRect(skia.Rect(70, 448, 70 + (W - 140) * alive / n, 454), fill_paint(GREEN))


def _card(c, n, alive, l2, l3, a=1.0):
    al = int(255 * a)
    box = skia.Rect(80, 600, W - 80, 880)
    c.drawRoundRect(box, 18, 18, fill_paint((14, 13, 20), int(225 * a)))
    big = f"{alive}"; rest = f" of {n} make it through"
    w1, w2 = E.text_w(big, 84), E.text_w(rest, 52)
    x0 = W / 2 - (w1 + w2) / 2
    draw_text(c, big, x0, 712, 84, GREEN, stroke=0, shadow=False, align="left", a=al)
    draw_text(c, rest, x0 + w1, 712, 52, GREEN, stroke=0, shadow=False, align="left", a=al)
    draw_text(c, l2, W / 2, 782, 36, (240, 240, 240), stroke=0, shadow=False, bold=False, a=al)
    draw_text(c, l3, W / 2, 836, 34, (255, 214, 70), stroke=0, shadow=False, bold=False, a=al)


TEMPLATES = {"cave_swarm": {"fn": cave_swarm, "fit": None, "inspo": "in-20261123-wdwa", "engine": "engine2",
                            "desc": "100 AI dots really evolve (neuro-evolution) to fly a narrowing neon cave; shows gens 1, 2, 4, 20; crashes ring + pop; 100/100 card.",
                            "knobs": ["n", "gens", "L", "V", "w0", "w1", "amp", "sigma0", "sigma1", "jitter", "elite_n", "l1", "l2"],
                            "title": "100 AIs learning to fly through a cave 🤖 #shorts #ai #satisfying"}}
