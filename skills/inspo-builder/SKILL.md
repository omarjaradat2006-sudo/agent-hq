---
name: inspo-builder
description: Build Omar's Inspo inbox videos (Agent HQ > YouTube > Inspo) into real Bounce Theory / Ambient Escape templates that go straight into the server's daily rotation. Use when Omar pastes an "Inspo build" prompt from Agent HQ, or says "build my inspos".
---

# Inspo builder (Claude Code on Omar's laptop)

Omar drops TikTok/Instagram links or video files on Agent HQ (YouTube tab > Inspo). The server's Gemini has already watched
most of them and left a breakdown (`analysis`). Your job: turn each one into a template on the Oracle server's engine that
LOOKS and SOUNDS like the inspiration (same idea, not a copy), push it, and mark it built. Omar then approves it on the site.
The server builds nothing itself: you are the builder, so the quality bar is yours.

Work through every item in the prompt. Don't stop to ask Omar anything: if an item can't be done, say why in its card (step 7) and go on.

## 0. Set up (once per run)
- Repos (Omar's GitHub login on this laptop has access to both):
  `git clone https://github.com/omarjaradat2006-sudo/agent-hq "%TEMP%\agent-hq"` (or `git -C ... pull` if it exists).
  Ambient items also need `git clone https://github.com/omarjaradat2006-sudo/bounce-engine "%TEMP%\bounce-engine"`.
- Python: `pip install skia-python pymunk numpy scipy kokoro-onnx soundfile yt-dlp`; ffmpeg must be on PATH.
- Voice model: `KOKORO_DIR=%USERPROFILE%\Downloads\YOUTUBE HQ\_system\assets\kokoro`.
- Engine files live in `agent-hq/data/youtube/auto_templates/`: `engine2.py` (Skia drawing, synth audio, Kokoro voice, writer),
  `auto_bounce2.py` (4 finished templates: jelly_drop, claw_flood, overflow_pendulum, fact_what_if), `facts.py` (narrated facts).
  READ `auto_bounce2.py` fully before writing anything: it is the quality bar and the code style to copy.

## 1. Get each inspiration
- Link: `python -m yt_dlp -f "mp4/best" -o "%TEMP%\inspo\<id>.mp4" <link>` (works from a home connection).
- Uploaded file: `https://raw.githubusercontent.com/omarjaradat2006-sudo/agent-hq/main/<file>`.
- If neither works, mark the card (step 7) "needs the video file" and skip it.

## 2. Study it properly (you can't play video: use frames + audio stats)
- Contact sheets: `ffmpeg -i v.mp4 -vf "fps=10/<dur>,scale=200:-2,tile=10x1" -frames:v 1 sheet.jpg`, plus a dense
  first-3-seconds sheet (`-t 3 -vf fps=4,...tile=12x1`), and a last-3-seconds sheet. Look at all three.
- Sound: use the server's `analysis.sound`; check loudness/beats with `ffmpeg -af volumedetect` / `silencedetect`.
  If it has speech, note the narration style (the voice is Kokoro `am_michael` in our engine).
- Write down, per video: the mechanic (what multiplies/breaks/bounces/races and the rule), hook (frame 1 + text),
  pacing (build-up, payoff, loop), palette, length, sound events. Merge with `analysis` from the prompt.

## 3. Pick the route
- **Bounce physics / satisfying sim** -> new Engine 2 template module (step 4).
- **Narrated fact / what-if** -> no new code: write a fact spec (`facts.SPEC_GUIDE`, real textbook numbers only) and add it to
  `facts.EXAMPLES`; render it with `facts.fact_short`. If the visuals need a new scene type, add it to `facts.py` cleanly.
- **Ambient Escape** -> the Ambient engine (`bounce-engine/ambient/plan.py` + `runtime.py`, read `ambient/README.md`).
  Prefer expressing it as an existing kind (reminder / explainer / long) with new rules; add a new kind only if needed.
  Push bounce-engine to `main` (the server pulls it every morning).

## 3b. It must make a NEW video every day (most important rule)
A template is only useful if the server can make a different video from it every day with no human writing.
- Physics: the knobs + seed must give real variety (counts, colours, shapes, rules, hooks).
- Script-driven formats (narration, Ambient explainers like the blocky toy farm): never ship one fixed script.
  Build a scene LIBRARY that covers many topics (generic actions/props/settings, not just the inspo's topic), let Gemini write
  each day's script into that schema (validate scene names; unknown scene -> closest one), keep the Quran/hadith reference
  check + meaning check, and test with 3 different Gemini-written topics before shipping.
- Add a daily quota to `agents/formats/youtube-lineup.md` (e.g. "2-3 blocky explainers per Ambient lineup") so the YouTube
  team actually schedules it, and say which `format` word triggers it.

## 4. Write the template (Bounce)
File `agent-hq/data/youtube/auto_templates/auto_inspo_<name>.py` (the server's catalog loads every `auto_*.py` there):
- First line `from auto_bounce2 import *` (gives np, math, skia, pymunk, Delaunay, sparse, E=engine2, Frame, Writer, Audio,
  sphere, glow_dot, draw_sprite, draw_balls, stroke_paint, fill_paint, polyline, draw_text, title, hsv, mix, rgb, W, H, FPS, TAU).
- ONE public function `<name>(path, seed=1, text=True, dry=False, **knobs)` returning the length in seconds (`return V.close(A)`).
  Helpers start with `_`. 5-10 knobs with defaults the YouTube team can vary (counts, sizes, hue floats/palettes, speeds, `l1`/`l2`).
- `dry=True` runs the identical physics/timing without drawing (`V.write(None)`) and returns the same length (the server
  times seeds with it). Respect `PREV`-style shortcuts only if you add them as knobs.
- 1080x1920, 60 fps, **18-38 s**. Frame 1 already moving + hook title (`title(c, l1, l2)`: white line + yellow line).
  Text/action between y=120 and y=1450 (YouTube covers the bottom). ~2 s payoff card; last frame close to the first (loop).
- Look: near-black or deep gradient background, shaded 3D balls (`sphere`/`draw_balls`), glow, soft shadows, saturated palette,
  anti-aliased Skia paths. Never flat OpenCV circles.
- Physics: pymunk for anything that collides (moving obstacles = KINEMATIC bodies, set position + velocity every substep;
  `space.on_collision(a, b, begin=fn)` for hit events); numpy for sheets/fields (see jelly_drop). 3-6 substeps per frame.
- Sound on every event: `A.impact(t, speed_px_s, base_hz, "chime", vol, unit=50)` (pitch follows impact speed), `A.tone(..., "thud"/"clack"/"boing"/"pop"/"whoosh")`,
  rate-limit to ~1 per 40-90 ms, a `crash` + `A.chord` on the payoff, a soft `pad` bed. Speech -> `E.say()` + `A.clip()`.
- Speed: under ~3 min to render on 2 CPU cores (keep bodies < ~1,500, sprites cached).
- Generic names only. No logos, watermarks, creator names, copyrighted characters or music.

## 5. Test until it really matches
- Render: `python -c "import sys; sys.path.insert(0, r'<auto_templates>'); import auto_inspo_<name> as m; print(m.<name>('t.mp4', 1), m.<name>(None, 1, dry=True))"`
- ffprobe: 1080x1920, has audio, 18-38 s, dry length within 15 %. Audio peak below -1 dBFS (`volumedetect`).
- Side-by-side: contact sheet of the inspiration over a contact sheet of yours. Fix what's off (sizes, colours, motion,
  timing, hook, payoff) and re-render. Don't settle for "works": it must read as the same style at a glance.
- Try 2-3 seeds; the server picks seeds by dry runs, so every seed must land inside 18-38 s.

## 6. Ship it
- Sample for Omar: `ffmpeg -i t.mp4 -vf scale=540:-2 -c:v libx264 -crf 30 -c:a aac -b:a 96k -movflags +faststart data/youtube/inspo_samples/<id>.mp4`
- Make sure it's in rotation: add an approved board idea to `data/youtube/state.json` `ideas`
  (`{"id": "youtube-inspo-<id>", "title": "Bounce Theory: <hook>", "status": "approved", "channel": "Bounce Theory",
  "format": "Bounce Theory · <name>", "createdAt": <now ISO>, "madeBy": "inspo-builder", "script": "Use template <name>: <what to vary>"}`)
  so the daily lineup uses it first (ideas-first rule). Ambient: same with `"channel": "Ambient Escape"`.
- `git pull --rebase` then commit "Inspo: built <names>" and push to `main` (agent-hq; bounce-engine too if changed).
  The server smoke-tests new `auto_*.py` files and adds them to the template menu on its next 7:05 AM Bounce run.

## 7. Update the cards (data/youtube/inspo.json, same commit)
Per item: `"status": "built"`, `"template": "<name>"`, `"sample": "data/youtube/inspo_samples/<id>.mp4"`,
`"explain": "<one line: what it is + what the YouTube team can vary>"`, `"builtAt": <now ISO>`, `"builtBy": "Claude Code"`.
Couldn't build: `"status": "failed"`, `"error": "<plain reason>"`.

## 8. Tell Omar
A short table: item, route, template name, length, what you matched, anything you couldn't. He approves each on the Inspo tab.
