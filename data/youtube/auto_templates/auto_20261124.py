"""Auto-built Bounce Theory template (2026-11-24), no Claude: written by Gemini from the YouTube board idea
youtube-2026-11-15-1: 'Bounce Theory: Triple Helix Pendulum Mirror Pattern #shorts'. Passed autobuild.py safety + test render (23.3 s). """
from sims import *
import math, numpy as np, cv2, random, colorsys

def auto_triple_helix_pendulum_mirror(
    path, seed=1, text=True, dry=False,
    n_bobs=14, cycle_dur=21.0, amp=340.0,
    c0=(50, 205, 255), c1=(235, 95, 170), c2=(225, 220, 60),
    l1="TRIPLE HELIX PENDULUM", l2="MIRROR WAVE SYNC", sub="Watch the pattern align..."
):
    rng = np.random.default_rng(seed)
    A = Audio()
    V = None if dry else Video(path)
    cv_ = Canvas(0.82)
    E = Ender(35)

    base_k = 16
    freqs = [(base_k + i) / cycle_dur for i in range(n_bobs)]
    strand_cols = [c0, c1, c2]

    parts = []
    aligned = False
    aligned_f = None

    y_start = 380
    y_step = 72
    last_side = np.zeros((3, n_bobs), dtype=np.int32)

    f = 0
    while not E.done(f):
        t = f / FPS

        for s in range(3):
            phase_strand = s * (2.0 * math.pi / 3.0)
            for i in range(n_bobs):
                fi = freqs[i]
                phase = 2.0 * math.pi * fi * t + phase_strand + i * (math.pi / 6.0)
                dx = amp * math.cos(phase)
                side = 1 if dx > 0 else -1
                if f > 0 and side != last_side[s, i]:
                    if s == 0 and i % 2 == 0:
                        A.note(t, (i + s * 4) % 15, v=0.18, d=0.25)
                last_side[s, i] = side

        if not aligned and t >= cycle_dur - 0.2:
            aligned = True
            aligned_f = f
            A.chord(t, root=4, v=0.45)
            for i in range(n_bobs):
                py = y_start + i * y_step
                for s in range(3):
                    phase_strand = s * (2.0 * math.pi / 3.0)
                    phase = 2.0 * math.pi * freqs[i] * t + phase_strand + i * (math.pi / 6.0)
                    px = CX + amp * math.cos(phase)
                    burst(parts, px, py, strand_cols[s], 12, 400, rng)
            E.finish(f, 2.5)

        if dry:
            f += 1
            continue

        img = cv_.frame()

        line(img, (CX, y_start - 40), (CX, y_start + n_bobs * y_step), (60, 60, 75), th=2)

        render_nodes = []
        for s in range(3):
            phase_strand = s * (2.0 * math.pi / 3.0)
            col = strand_cols[s]
            pts = []
            for i in range(n_bobs):
                py = y_start + i * y_step
                phase = 2.0 * math.pi * freqs[i] * t + phase_strand + i * (math.pi / 6.0)
                px = CX + amp * math.cos(phase)
                pz = math.sin(phase)
                pts.append((px, py, pz))
                render_nodes.append((pz, s, i, px, py, col))

            for i in range(n_bobs - 1):
                p1 = (pts[i][0], pts[i][1])
                p2 = (pts[i + 1][0], pts[i + 1][1])
                line(img, p1, p2, col, th=3)
                line(cv_.trail, p1, p2, (col[0] // 3, col[1] // 3, col[2] // 3), th=2)

        render_nodes.sort(key=lambda item: item[0])

        for pz, s, i, px, py, col in render_nodes:
            r = int(14 + 6 * pz)
            circle(img, px, py, r + 4, col, th=2)
            circle(cv_.trail, px, py, r, col)
            circle(img, px, py, r, WHITE if pz > 0.5 else col)

        step_parts(img, parts)

        if text:
            title(img, l1, l2)
            if aligned:
                caption(img, "PERFECT MIRROR ALIGNMENT!", 1580, 68, YELLOW)
            else:
                progress = min(1.0, t / cycle_dur)
                caption(img, f"HELIX SYNC: {int(progress * 100)}%", 1580, 56, WHITE)

        V.write(img)
        f += 1

    return (f / FPS if E.end is not None and f < E.maxf else 999) if V is None else V.close(A)
