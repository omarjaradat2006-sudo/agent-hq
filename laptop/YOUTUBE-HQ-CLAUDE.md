# YOUTUBE HQ: daily batch for Ambient Escape (Claude Code on Omar's laptop)

> **Bounce Theory is no longer made here.** Since 2026-11-09 the Oracle server makes, uploads and schedules it every day at 7 AM from the lineup's template settings (private repo `bounce-engine`, runner `scripts/server/run_bounce.sh`). Never render or upload Bounce Theory from the laptop: it would double-post. To change how Bounce videos look, add or improve formats in the bounce-engine repo (they appear in the template menu by themselves).

You are running in Claude Code ON Omar's Windows laptop, inside `Downloads\YOUTUBE HQ`. You can read, write and run everything here directly. There is no cloud workspace, no file staging and no copying: render, check, upload and clean up yourself. Omar pastes one prompt and walks away, so never stop to hand him commands. Only stop for the cases under "Stop and tell Omar".

## Your skills
- `ambient-escape-videos` (in `.claude\skills\`): the same for Ambient Escape.
Load it before you start. **These laptop rules override any skill or plan step that says** "render in the cloud", "stage the engine files", "copy to the laptop", "split into parts", "commit pieces into _system\parts", "give Omar the commands", or "render only 3-second previews". Here you render the full batch yourself with render.py.

## The daily run (do every step, in order)
1. **Get today's plans:**
   - `curl -sL https://raw.githubusercontent.com/omarjaradat2006-sudo/agent-hq/main/data/youtube/batch/ambient-escape.md`
   - Full data: `.../data/youtube/state.json` (same base URL).
   If the plan's date (in its first line) isn't today's Toronto date, STOP and tell Omar: it's an old plan that was already uploaded.
2. **Never remake an uploaded video:** check `_system\Upload Tool\logs\*_uploaded_log.json` first.
3. **Read the header of `_system\Local Render\render.py`.** It has the job-file contract.
4. (Bounce Theory is made on the server; skip it.)
5. **Write the job file:** `_system\Local Render\jobs\ambient_today.py`. JOBS go in lineup order with thumbnails last, and DOWNLOADS list the ready clips. Ambient longs MUST loop the real downloaded clips named in the plan (R.loop_long with copyright-safe audio layers); never generate or draw scenes for them.
6. **Write `queue.json` and `UPLOAD SHEET.txt`** into each "Upload Today" folder. EVERY queue item gets a `slot` (0, 1, 2... in the plan's order).
7. **Render:** from `_system\Local Render`, run `python render.py ambient`. They take a long time, so use a long timeout or run them in the background and check on them. If a render errors, fix that job and run the same command again (finished videos are skipped).
8. **Check every video** before uploading:
   - ffprobe: it has audio, the right duration and 1080x1920 (Shorts) or 1920x1080 (longs).
   - Ambient longs: confirm they really use the downloaded clips.
9. **Upload:** from `_system\Upload Tool`, run `python upload.py ambient`. Every video must end up scheduled in the 5 PM to 8 AM window, never left Private. If a browser login opens, tell Omar to click Allow.
10. **Mark Agent HQ:**
    - If `_system\agent-hq` doesn't exist, run `git clone https://github.com/omarjaradat2006-sudo/agent-hq "_system\agent-hq"`. Otherwise `git pull --rebase` inside it.
    - In `data/youtube/state.json`:
      - set `made: true` on every Ambient Escape lineup item you uploaded (`lineup.channels["Ambient Escape"][*]`)
      - set `status: "done"` + `doneAt` (ISO now) on the ideas you used (the `★ new` ideas in the plans)
      - prepend 2 log entries: `{"t":now,"agent":"Producer","msg":"Made N <Channel> videos from today's lineup"}`
    - Keep the file's formatting, validate the JSON, then commit and push: `git -c user.name="Omar Jaradat" -c user.email="omarjaradat2006@gmail.com" commit -am "..."`, `git pull --rebase`, `git push`.
    - If the push needs a GitHub login, Omar approves it once in the browser.
11. **Clean up** once Ambient Escape is uploaded and scheduled:
    - run `echo y | python render.py clean` in `_system\Local Render`
    - empty `_system\parts` and `_system\Uploaded (delete later)`
    - delete leftover `.part`/temp files and stray `.mp4.json` race-data files in the Upload Today folders
    - **Never delete** anything still listed in a queue.json, the engine/tool code, `4 Channel Branding`, `_system\assets`, fonts, logs, tokens or client secrets.
12. **Finish** with a short report:
    - videos made and uploaded per channel, and the first and last publish times
    - anything you redid
    - space freed

## Ambient Escape animated explainers (8 Shorts a day: `explainer_pov` and `explainer_list`)
**Use explainer2 (Omar approved this style on 2026-11-08). Do NOT use the old `explainer.py` for new videos.**
It lives in `_system\Local Render\lib\explainer2\` (the master copy is `render/explainer2/` in the agent-hq repo; if the laptop copy is missing or older, copy the repo folder over it). Read the header of `explainer2.py` first: it documents the SPEC, the scenes and their modes, and the voice rotation. Approved samples: `_system\migration\review\rebuilt\SHORT 01 ... (v2).mp4` and `SHORT 03 ... (v2).mp4` (the specs `S01`/`S03` inside explainer2.py).
- **One-time setup:** `pip install pycairo kokoro-onnx soundfile opencv-python pillow numpy`, and `python -c "from PIL import features; print(features.check('raqm'))"` must print True (else `pip install arabic-reshaper python-bidi`).
- **Look (keep it):** flat illustrated scenes that fill the whole 9:16, faceless characters with real poses, title zone at the top, action in the middle, captions + source pill at the bottom, nothing overlapping, Poppins only (Amiri just for Arabic and ﷺ), camera push-ins, pose changes, word-by-word captions, cross-fades.
- **Sound (Omar's rules, never break):** Kokoro narration + the small built-in sound effects ONLY. No background bed, no rain, no music or instrumental, no tones, no echo.
- **Voices rotate:** one male voice per video, a different voice for every video. Pass `index=k` (k = 0..7, the explainer's position in today's lineup) and explainer2 picks the voice; never pin one voice for the whole batch. Never use female voices.
- **Build each SPEC from the slot's `note`** (the YouTube team writes POV hook, beats, reveal words, source, end, CTA, or the list points). Map it onto explainer2 scene dicts: POV = 1-3 situation scenes (pick or extend a scene that actually shows the situation; phone scenes take `chat`, `draft`, `reply`) → a `reveal` scene with the Arabic words + English gloss timed to the narration → an ending scene with the CTA. List = hook scene → one scene per point (`label` "01 / 04", `title` with one *keyword*, `arabic`, `source`, two narration lines) → ending + CTA. Write narration in calm, plain English; hadith only as reported meaning ("told us, in meaning").
- **New situations:** when no scene fits (the note may say `new scene: ...`), add a new scene function to `scenes.py` in the same flat style (action inside y 450-1140, register it in `SCENES`), and copy the improved file back to the agent-hq repo `render/explainer2/` so the next batch has it. Never depict prophets, angels or anything presented as them; characters stay faceless.
- **Religious accuracy check (never skip):** before rendering, confirm every hadith reference (collection + number) and every ayah (surah:ayah) matches the wording on screen and in the narration, and that the Arabic is copied exactly from the source. If you can't confirm it, replace that point with one you can confirm, and tell Omar in the final report.
- **Job line:** `import explainer2 as X2` (add the explainer2 folder to `sys.path`), then `("SHORT 0N - <name>.mp4", lambda p: X2.make(p, SPEC_N, index=k))`. Lengths: pov 25-40 s, list 35-50 s.
- **Check:** contact sheet of each one (`python explainer2.py stills ...` or ffmpeg tile): no text over the action or off screen, Arabic letters connected, ﷺ shows (not a box), audio has only the voice and the small effects.
- **Upload sheet:** title from the lineup; the description gives the hadith or ayah reference in full, "Voice: AI narration. Animation and audio: original. No music.", plus 3-5 hashtags (#islam #hadith #shorts ...).

## Rules
- **Channel check (never break):** Ambient Escape never gets a Bounce Engine / physics-sim / bounce / race / battle video, and Bounce Theory never gets Islamic, ambience or stock-footage videos. If a plan slot breaks this, skip that slot, don't render or upload it, and say so in the final report. Before uploading, check every item in each queue.json belongs to that channel.
- English only, everywhere (titles, on-screen text, descriptions, voice-over).
- Keep each plan's order and titles. Most videos are remixes of winners: keep the winner's recipe (format, hook, length, pacing) and change only the listed twist.
- Never open, print or copy `client_secret_*.json`, `token_*.json` or any key file. upload.py uses them itself.
- Don't post anywhere other than the two YouTube channels through upload.py.

## Stop and tell Omar only if
- a plan is old (not today's date)
- YouTube's daily upload limit is hit (say how many are left in the queue; rerun upload.py tomorrow)
- something keeps failing after 3 fix attempts

## Upgrades
To change how videos are made, edit the skill files in `.claude\skills\<skill>\SKILL.md` (this laptop copy is the one the daily batch uses). Keep changes small and say what you changed. Agent HQ planning changes go in the agent-hq repo, not here.
