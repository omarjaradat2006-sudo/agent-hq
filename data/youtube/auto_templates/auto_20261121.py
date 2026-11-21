"""Auto-built Bounce Theory template (2026-11-21), no Claude: written by Gemini from the YouTube board idea
youtube-2026-11-13-1: 'Bounce Theory: Dual Hexagon Pendulum Alignment #shorts'. Passed autobuild.py safety + test render (25.17 s). """
from sims import *

def _hex_points(cx, cy, radius, n_points):
    pts = []
    verts = [
        (cx + radius * math.cos(k * math.pi / 3), cy + radius * math.sin(k * math.pi / 3))
        for k in range(6)
    ]
    per_edge = n_points // 6
    for k in range(6):
        v0 = np.array(verts[k])
        v1 = np.array(verts[(k + 1) % 6])
        for j in range(per_edge):
            frac = j / per_edge
            p = v0 + frac * (v1 - v0)
            pts.append((float(p[0]), float(p[1])))
    return pts

def auto_dual_hexagon_pendulum_alignm(
    path, seed=1, text=True, dry=False,
    n_inner=12, n_outer=24, align_time=22.0,
    c0=(255, 220, 50), c1=(235, 95, 170), c2=(50, 205, 255),
    l1="DUAL HEXAGON WAVE", l2="WATCH THEM ALIGN", sub="Wait for the perfect sync..."
):
    rng = np.random.default_rng(seed)
    A = Audio()
    V = None if dry else Video(path)
    cv_ = Canvas(0.85)
    E = Ender(32 * FPS)

    total_n = n_inner + n_outer
    center_y = CY - 50

    pts_in = _hex_points(CX, center_y, 220, n_inner)
    pts_out = _hex_points(CX, center_y, 420, n_outer)
    all_pts = pts_in + pts_out

    n_base = 16
    freqs = [(n_base + i) / align_time for i in range(total_n)]
    lengths = [270.0 - 90.0 * (i / max(1, total_n - 1)) for i in range(total_n)]
    pivots = [(px, py - L) for (px, py), L in zip(all_pts, lengths)]

    cols = []
    for i in range(total_n):
        if i < n_inner:
            t_col = i / n_inner
            col = hue(0.52 + 0.18 * t_col)
        else:
            t_col = (i - n_inner) / n_outer
            col = hue(0.78 + 0.28 * t_col)
        cols.append(col)

    prev_sin = [0.0] * total_n
    parts = []
    aligned = False

    f = 0
    amp = 0.50

    while not E.done(f):
        t = f / FPS
        bobs = []
        sync_sum = 0.0

        for i in range(total_n):
            freq = freqs[i]
            phase = 2.0 * math.pi * freq * t
            s_val = math.sin(phase)
            sync_sum += abs(s_val)

            if prev_sin[i] < 0 and s_val >= 0:
                if t < align_time - 0.5:
                    note_idx = (i * 2) % 15
                    A.note(t, note_idx, v=0.12, d=0.3)
            prev_sin[i] = s_val

            theta = amp * s_val
            px, py = all_pts[i]
            L = lengths[i]
            bx = px + L * math.sin(theta)
            by = (py - L) + L * math.cos(theta)
            bobs.append((bx, by))

        if not aligned and t >= align_time - 0.04:
            aligned = True
            E.finish(f, 3.2)
            A.chord(t, root=2, v=0.35)
            A.note(t + 0.12, 9, v=0.35, d=0.8)
            A.note(t + 0.24, 12, v=0.35, d=0.8)
            A.note(t + 0.36, 14, v=0.4, d=1.2)
            for (px, py), col in zip(all_pts, cols):
                burst(parts, px, py, col, 8, 280, rng)

        if dry:
            f += 1
            continue

        img = cv_.frame()

        for pts_group, base_col in [(pts_in, (70, 70, 70)), (pts_out, (50, 50, 50))]:
            np_pts = np.array(pts_group, np.int32)
            cv2.polylines(img, [np_pts], True, base_col, 1, cv2.LINE_AA)

        for i in range(total_n):
            hx, hy = pivots[i]
            bx, by = bobs[i]
            col = cols[i]
            line(img, (hx, hy), (bx, by), (65, 65, 75), 1)
            px, py = all_pts[i]
            circle(img, px, py, 3, (90, 90, 90), 1)
            circle(cv_.trail, bx, by, 7, col)

        step_parts(img, parts)

        for i in range(total_n):
            bx, by = bobs[i]
            col = cols[i]
            circle(img, bx, by, 11, col, -1)
            circle(img, bx, by, 5, WHITE, -1)

        if text:
            title(img, l1, l2)
            if aligned:
                caption(img, "PERFECT ALIGNMENT! 🌊", 1580, 68, YELLOW)
            else:
                caption(img, sub, 1550)

        V.write(img)
        f += 1

    return (f / FPS if E.end is not None and f < E.maxf else 999) if V is None else V.close(A)
