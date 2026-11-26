"""Auto-built Bounce Theory template (2026-11-26), no Claude: written by Gemini from the YouTube board idea
youtube-2026-11-17-1: 'Bounce Theory: Dual Hexagon Pendulum Alignment #shorts'. Passed autobuild.py safety + test render (24.0 s). """
from sims import *

def _draw_hexagon(img, cx, cy, radius, angle, col, th=3):
    pts = []
    for i in range(6):
        a = angle + i * TAU / 6.0
        pts.append((cx + radius * math.cos(a), cy + radius * math.sin(a)))
    for i in range(6):
        line(img, pts[i], pts[(i + 1) % 6], col, th)

def auto_dual_hexagon_pendulum_alignm(
    path,
    seed=1,
    text=True,
    dry=False,
    n=12,
    r_out=420.0,
    r_in=180.0,
    t_align=21.5,
    c0=(50, 205, 255),
    c1=(245, 160, 50),
    c2=(110, 220, 70),
    l1="DUAL HEXAGON PENDULUM ALIGNMENT",
    l2="HARMONIC WAVE SYNC",
    sub="Watch the pendulums align..."
):
    rng = np.random.default_rng(seed)
    A = Audio()
    V = None if dry else Video(path)
    cv_ = Canvas(0.85)
    E = Ender(40)

    p = np.array([CX + rng.uniform(-30, 30), CY - 90.0])
    v = np.array([rng.uniform(-280, 280), rng.uniform(-140, 140)])
    r_ball = 15.0
    g = 750.0

    parts = []
    aligned = False
    last_bounce = -1.0
    f = 0

    while not E.done(f):
        t = f / FPS

        for s in range(SUB):
            ts = t + s * DT

            bob_pts = []
            bob_vels = []
            r_mid = (r_out + r_in) / 2.0
            r_amp = (r_out - r_in) / 2.0

            for k in range(n):
                ak = k * TAU / n + 0.04 * ts
                fk = (8.0 + k) / t_align
                rk = r_mid - r_amp * math.cos(TAU * fk * ts)
                drk = r_amp * TAU * fk * math.sin(TAU * fk * ts)
                dak = 0.04

                bx = CX + rk * math.cos(ak)
                by = CY + rk * math.sin(ak)
                vx_b = drk * math.cos(ak) - rk * dak * math.sin(ak)
                vy_b = drk * math.sin(ak) + rk * dak * math.cos(ak)

                bob_pts.append((bx, by))
                bob_vels.append((vx_b, vy_b))

            v[1] += g * DT
            p += v * DT

            for k in range(n):
                bx, by = bob_pts[k]
                dx = p[0] - bx
                dy = p[1] - by
                dist = math.hypot(dx, dy)
                min_d = r_ball + 16.0
                if dist < min_d and dist > 1e-4:
                    nx, ny = dx / dist, dy / dist
                    p[0] = bx + nx * min_d
                    p[1] = by + ny * min_d
                    vx_b, vy_b = bob_vels[k]
                    rel_vx = v[0] - vx_b
                    rel_vy = v[1] - vy_b
                    vn = rel_vx * nx + rel_vy * ny
                    if vn < 0:
                        rel_vx -= 1.9 * vn * nx
                        rel_vy -= 1.9 * vn * ny
                        v[0] = rel_vx + vx_b
                        v[1] = rel_vy + vy_b
                        sp = math.hypot(v[0], v[1])
                        if sp < 350.0:
                            v *= 350.0 / sp
                        if sp > 1100.0:
                            v *= 1100.0 / sp
                        if ts - last_bounce > 0.07:
                            A.note(ts, k % 12, 0.35)
                            last_bounce = ts
                        if not dry:
                            burst(parts, p[0], p[1], c0, 8, 180, rng)

            d_center = math.hypot(p[0] - CX, p[1] - CY)
            max_r = r_out + 25.0
            if d_center + r_ball > max_r and d_center > 1e-4:
                nx = (CX - p[0]) / d_center
                ny = (CY - p[1]) / d_center
                p[0] = CX - nx * (max_r - r_ball)
                p[1] = CY - ny * (max_r - r_ball)
                vn = v[0] * nx + v[1] * ny
                if vn < 0:
                    v[0] -= 1.85 * vn * nx
                    v[1] -= 1.85 * vn * ny
                    if ts - last_bounce > 0.07:
                        A.pop(ts, 0.25)
                        last_bounce = ts

            r_core = 35.0
            if d_center - r_ball < r_core and d_center > 1e-4:
                nx = (p[0] - CX) / d_center
                ny = (p[1] - CY) / d_center
                p[0] = CX + nx * (r_core + r_ball)
                p[1] = CY + ny * (r_core + r_ball)
                vn = v[0] * nx + v[1] * ny
                if vn < 0:
                    v[0] -= 1.85 * vn * nx
                    v[1] -= 1.85 * vn * ny
                    if ts - last_bounce > 0.07:
                        A.note(ts, 14, 0.3)
                        last_bounce = ts

            if not aligned and ts >= t_align:
                aligned = True
                A.chord(ts, 4, 0.4)
                for k in range(6):
                    A.note(ts + k * 0.08, 8 + k * 2, 0.35)
                for k in range(n):
                    bx, by = bob_pts[k]
                    burst(parts, bx, by, c0, 20, 350, rng)
                burst(parts, CX, CY, WHITE, 40, 500, rng)
                E.finish(f, 2.5)

        if dry:
            f += 1
            continue

        img = cv_.frame()

        _draw_hexagon(img, CX, CY, r_out, 0.05 * t, c1, 3)
        _draw_hexagon(img, CX, CY, r_in, -0.08 * t, c2, 3)

        r_mid = (r_out + r_in) / 2.0
        r_amp = (r_out - r_in) / 2.0
        for k in range(n):
            ak = k * TAU / n + 0.04 * t
            fk = (8.0 + k) / t_align
            rk = r_mid - r_amp * math.cos(TAU * fk * t)
            ax = CX + r_out * math.cos(ak)
            ay = CY + r_out * math.sin(ak)
            bx = CX + rk * math.cos(ak)
            by = CY + rk * math.sin(ak)

            line(img, (ax, ay), (bx, by), GREY, 2)
            circle(img, ax, ay, 4, WHITE)

            col_k = hue((k / float(n) + 0.08 * t) % 1.0)
            circle(cv_.trail, bx, by, 18, col_k)
            circle(img, bx, by, 16, col_k)
            circle(img, bx, by, 6, WHITE)

        pulse = 3.0 * math.sin(6.0 * t)
        core_col = c0 if not aligned else YELLOW
        ring(img, CX, CY, 35.0 + pulse, core_col, 4)

        if aligned:
            expand_r = 35.0 + 350.0 * (t - t_align)
            if expand_r < 600:
                ring(img, CX, CY, expand_r, YELLOW, 5)

        step_parts(img, parts)

        circle(cv_.trail, p[0], p[1], r_ball * 0.8, WHITE)
        circle(img, p[0], p[1], r_ball, WHITE)
        circle(img, p[0], p[1], r_ball * 0.5, c0)

        if text:
            title(img, l1, l2)
            if aligned:
                caption(img, "DUAL HEXAGON ALIGNMENT!", 1530, 62, YELLOW)
                caption(img, "PERFECT HARMONIC SYNC!", 1620, 50, WHITE)
            else:
                rem = max(0.0, t_align - t)
                caption(img, f"SYNC IN: {rem:.1f}s", 1530, 60, WHITE)
                caption(img, sub, 1620, 50, GREY)

        V.write(img)
        f += 1

    return (f / FPS if E.end is not None and f < E.maxf else 999.0) if V is None else V.close(A)
