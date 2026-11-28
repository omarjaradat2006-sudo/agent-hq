"""Auto-built Bounce Theory template (2026-11-28), no Claude: written by Gemini from the YouTube board idea
youtube-inspo-in-20261123-wdwa: '100 AIs learning to fly through a cave #shorts #ai'. Passed autobuild.py safety + test render (22.0 s). """
from sims import *

def auto_100_ais_learning_to_fly_thro(
    path, seed=42, text=True, dry=False,
    n=100, gens=4, w1=110.0, amp=260.0,
    l1="100 AIs IN CAVE", l2="EVOLUTION GEN 1",
    sub="Can neural nets learn to fly?"
):
    rng = np.random.default_rng(seed)
    A = Audio()
    V = None if dry else Video(path)
    cv_ = Canvas(0.85)
    E = Ender(22)  # target ~20-22 seconds total

    # Cave generation parameters
    cave_len = 3500.0
    dx = cave_len / 300.0
    xs = np.linspace(0, cave_len, 301)
    
    # Generate multi-frequency cave walls
    def make_cave(g_idx):
        # As generations progress, the cave gets slightly wider / more forgiving
        wid = w1 + g_idx * 15.0
        # Smooth random noise for top and bottom walls
        top = 250.0 + 80.0 * np.sin(xs * 0.003 + g_idx) + 50.0 * np.sin(xs * 0.008 - g_idx * 2)
        bot = (H - 250.0) - 80.0 * np.cos(xs * 0.003 + g_idx) - 50.0 * np.sin(xs * 0.007 + g_idx)
        # Ensure enough space
        diff = bot - top
        too_narrow = diff < wid * 2.2
        bot[too_narrow] = top[too_narrow] + wid * 2.2
        return top, bot

    current_gen = 0
    top_w, bot_w = make_cave(current_gen)

    # Agents: [x, y, vx, vy, alive, fitness, best_x]
    # We'll run 4 generations, about 5-6 seconds each (~330 frames per generation at 60fps)
    frames_per_gen = 300
    f = 0
    
    # Initialize agents
    agents = np.zeros((n, 7))
    def reset_generation():
        nonlocal agents
        agents[:, 0] = 100.0  # x
        agents[:, 1] = CY     # y
        agents[:, 2] = rng.uniform(150.0, 250.0, n)  # vx
        agents[:, 3] = rng.uniform(-50.0, 50.0, n)   # vy
        agents[:, 4] = 1.0    # alive
        agents[:, 5] = 100.0  # fitness (max x reached)
        agents[:, 6] = 100.0  # best_x

    reset_generation()
    parts = []
    gen_start_f = 0
    max_reached_overall = 100.0

    while not E.done(f):
        t = f / FPS
        
        # Check generation switch
        elapsed_gen_f = f - gen_start_f
        if elapsed_gen_f >= frames_per_gen and current_gen < gens - 1:
            # Sort agents by furthest distance reached
            sorted_idx = np.argsort(agents[:, 6])[::-1]
            # Breed / mutate top performers
            best_agents = agents[sorted_idx[:15]]
            
            current_gen += 1
            top_w, bot_w = make_cave(current_gen)
            gen_start_f = f
            
            # Reset agents with slight mutations around best performers
            reset_generation()
            for i in range(n):
                parent = best_agents[i % 15]
                agents[i, 2] = parent[2] + rng.uniform(-30, 30)
                agents[i, 3] = parent[3] + rng.uniform(-40, 40)
            
            l2 = f"EVOLUTION GEN {current_gen + 1}"
            sub = f"Surviving AI bots adapting..."
            A.chord(t, 2 + current_gen)

        # Final generation celebration or finish
        if current_gen == gens - 1 and elapsed_gen_f == frames_per_gen - 10:
            E.finish(f, 2.5)

        for _ in range(SUB):
            dt_sub = DT / SUB
            for i in range(n):
                if agents[i, 4] <= 0:
                    continue
                
                # Simple neural control / physics: pull towards center of cave ahead, add lift/flap
                cx_pos = agents[i, 0]
                idx = int(np.clip(cx_pos / dx, 0, 300))
                t_wall = top_w[idx]
                b_wall = bot_w[idx]
                mid_y = (t_wall + b_wall) / 2.0
                
                # AI neural-like heuristic steering towards center + forward thrust
                steer = (mid_y - agents[i, 1]) * 4.0
                agents[i, 3] += steer * dt_sub
                agents[i, 3] += rng.standard_normal() * 40.0 * dt_sub  # slight turbulence
                agents[i, 2] = 220.0 + current_gen * 15.0  # forward speed increases each gen
                
                agents[i, 0] += agents[i, 2] * dt_sub
                agents[i, 1] += agents[i, 3] * dt_sub
                
                # Track max distance
                if agents[i, 0] > agents[i, 6]:
                    agents[i, 6] = agents[i, 0]
                    if agents[i, 6] > max_reached_overall:
                        max_reached_overall = agents[i, 6]

                # Check collision with cave walls
                if agents[i, 0] >= 0 and agents[i, 0] <= cave_len:
                    curr_idx = int(np.clip(agents[i, 0] / dx, 0, 300))
                    if agents[i, 1] <= top_w[curr_idx] + 8 or agents[i, 1] >= bot_w[curr_idx] - 8:
                        agents[i, 4] = 0.0  # died
                        burst(parts, agents[i, 0], agents[i, 1], (50, 150, 255), 8, 120, rng)
                        if rng.random() < 0.05:
                            A.pop(t, 0.1)

        if dry:
            f += 1
            continue

        # Render frame
        img = cv_.frame()

        # Camera scroll based on average leading alive agent
        alive_mask = agents[:, 4] > 0
        cam_x = np.mean(agents[alive_mask, 0]) if np.any(alive_mask) else agents[0, 0]
        cam_x = np.clip(cam_x - 300.0, 0.0, cave_len - W)

        # Draw cave walls
        for x_i in range(300):
            x1 = xs[x_i] - cam_x
            x2 = xs[x_i + 1] - cam_x
            if x2 < 0 or x1 > W:
                continue
            # Top wall
            line(img, (x1, top_w[x_i]), (x2, top_w[x_i + 1]), (80, 180, 255), 4)
            # Bottom wall
            line(img, (x1, bot_w[x_i]), (x2, bot_w[x_i + 1]), (80, 180, 255), 4)

        # Draw particle effects
        step_parts(img, parts, cam_x)

        # Draw agents
        surviving_count = 0
        for i in range(n):
            if agents[i, 4] > 0:
                surviving_count += 1
                ax = agents[i, 0] - cam_x
                ay = agents[i, 1]
                if 0 <= ax <= W:
                    col = hue(0.33 + current_gen * 0.15)
                    circle(img, ax, ay, 6, col)

        # UI / Text overlay
        if text:
            title(img, l1, l2)
            caption(img, f"SURVIVORS: {surviving_count} / {n}", 1530, 60, WHITE)
            if current_gen == gens - 1 and elapsed_gen_f > frames_per_gen - 60:
                caption(img, "SUCCESS: FLIGHT ACHIEVED!", 1620, 72, YELLOW)
            else:
                caption(img, sub, 1640, 50, GREY)

        V.write(img)
        f += 1

    if dry:
        return float(f / FPS)
    return V.close(A)
