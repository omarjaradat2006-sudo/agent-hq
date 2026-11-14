"""Auto-built Bounce Theory template (2026-11-14), no Claude: written by Gemini from the YouTube board idea
youtube-2026-11-12-1: 'Needs build: Pendulum Wave: Triple Helix Mirror Pattern'. Passed autobuild.py safety + test render (23.5 s). """
from sims import *


def _get_arm_pos(m, k, n, r_min, r_max, amp, n_min, t_cycle, t):
    arm_ang = m * (TAU / 3.0)
    u = (math.cos(arm_ang), math.sin(arm_ang))
    vp = (-math.sin(arm_ang), math.cos(arm_ang))
    rk = r_min + k * (r_max - r_min) / max(1, n - 1)
    fk = (n_min + k) / t_cycle
    phi = TAU * fk * t
    offset = amp * math.sin(phi)
    px = CX + rk * u[0] + offset * vp[0]
    py = CY + rk * u[1] + offset * vp[1]
    p0x = CX + rk * u[0]
    p0y = CY + rk * u[1]
    return (px, py), (p0x, p0y), phi


def auto_needs_build_pendulum_wave_tr(
    path,
    seed=1,
    text=True,
    dry=False,
    n=21,
    t_cycle=21.0,
    n_min=15,
    amp=120.0,
    r_min=160.0,
    r_max=680.0,
    c0=(50, 205, 255),
    c1=(235, 95, 170),
    c2=(245, 160, 50),
    l1="PENDULUM WAVE",
    l2="TRIPLE HELIX MIRROR",
    sub="Watch 3 arms intertwine & sync...",
):
    rng = np.random.default_rng(seed)
    A = Audio()
    V = None if dry else Video(path)
    cv_ = Canvas(0.85)
    E = Ender(30)

    arm_cols = [c0, c1, c2]
    parts = []

    last_sign = np.zeros((3, n), dtype=np.int32)
    helix1_played = False
    helix2_played = False
    sync_played = False

    f = 0
    while not E.done(f):
        t = f / FPS

        bobs = []
        pivots = []
        phases = []
        for m in range(3):
            b_arm, p_arm, ph_arm = [], [], []
            for k in range(n):
                pos, p0, phi = _get_arm_pos(
                    m, k, n, r_min, r_max, amp, n_min, t_cycle, t
                )
                b_arm.append(pos)
                p_arm.append(p0)
                ph_arm.append(phi)

                sign = 1 if math.sin(phi) >= 0 else -1
                if f > 0 and sign > 0 and last_sign[m, k] < 0:
                    if m == 0 and k % 3 == 0:
                        A.note(t, (k // 3) % 10, 0.12, 0.25)
                last_sign[m, k] = sign
            bobs.append(b_arm)
            pivots.append(p_arm)
            phases.append(ph_arm)

        if t >= t_cycle / 3.0 and not helix1_played:
            helix1_played = True
            A.chord(t, root=4, v=0.35)
            if not dry:
                for m in range(3):
                    for k in range(0, n, 3):
                        bx, by = bobs[m][k]
                        burst(parts, bx, by, arm_cols[m], 8, 300, rng)

        if t >= 2.0 * t_cycle / 3.0 and not helix2_played:
            helix2_played = True
            A.chord(t, root=7, v=0.35)
            if not dry:
                for m in range(3):
                    for k in range(0, n, 3):
                        bx, by = bobs[m][k]
                        burst(parts, bx, by, arm_cols[m], 8, 300, rng)

        if t >= t_cycle and not sync_played:
            sync_played = True
            A.chord(t, root=0, v=0.5)
            A.chord(t + 0.15, root=7, v=0.5)
            if not dry:
                for m in range(3):
                    for k in range(n):
                        bx, by = bobs[m][k]
                        burst(parts, bx, by, arm_cols[m], 15, 500, rng)
            E.finish(f, hold=2.5)

        if dry:
            f += 1
            continue

        img = cv_.frame()

        for m in range(3):
            arm_ang = m * (TAU / 3.0)
            ax_end = (
                CX + (r_max + 30) * math.cos(arm_ang),
                CY + (r_max + 30) * math.sin(arm_ang),
            )
            line(img, (CX, CY), ax_end, (40, 35, 30), 1)

        for k in range(n):
            t_col = hue((k / n + t * 0.05) % 1.0, 0.6, 0.4)
            pA = bobs[0][k]
            pB = bobs[1][k]
            pC = bobs[2][k]
            line(img, pA, pB, t_col, 1)
            line(img, pB, pC, t_col, 1)
            line(img, pC, pA, t_col, 1)

        for m in range(3):
            col = arm_cols[m]
            for k in range(n):
                line(img, pivots[m][k], bobs[m][k], (50, 50, 50), 1)
            for k in range(n - 1):
                line(img, bobs[m][k], bobs[m][k + 1], col, 2)

        for m in range(3):
            col = arm_cols[m]
            for k in range(n):
                bx, by = bobs[m][k]
                circle(cv_.trail, bx, by, 4, col)
                circle(img, bx, by, 9, col, -1)
                circle(img, bx, by, 11, WHITE, 1)

        step_parts(img, parts)

        circle(img, CX, CY, 16, WHITE, -1)
        circle(img, CX, CY, 22, YELLOW, 2)

        if text:
            title(img, l1, l2)
            if sync_played:
                caption(img, "PERFECT SYNCHRONIZATION!", 1550, 68, YELLOW)
            elif (
                t >= 2.0 * t_cycle / 3.0 - 0.5
                and t <= 2.0 * t_cycle / 3.0 + 2.0
            ):
                caption(img, "TRIPLE HELIX MIRROR PHASE!", 1550, 60, WHITE)
            elif t >= t_cycle / 3.0 - 0.5 and t <= t_cycle / 3.0 + 2.0:
                caption(img, "TRIPLE HELIX PHASE!", 1550, 60, WHITE)
            else:
                caption(img, sub, 1620)

        V.write(img)
        f += 1

    return (
        (f / FPS if E.end is not None and f < E.maxf else 999)
        if V is None
        else V.close(A)
    )
