# YOUTUBE HQ: daily batch for Bounce Theory + Ambient Escape (Claude Code on Omar's laptop)

You are running in Claude Code ON Omar's Windows laptop, inside `Downloads\YOUTUBE HQ`. You can read, write and run everything here directly. There is no cloud workspace, no file staging and no copying: render, check, upload and clean up yourself. Omar pastes one prompt and walks away, so never stop to hand him commands. Only stop for the cases under "Stop and tell Omar".

## Your skills
- `bounce-theory-videos` (in `.claude\skills\`): formats, variety rules, titles, thumbnails, queue/upload sheet rules for Bounce Theory.
- `ambient-escape-videos` (in `.claude\skills\`): the same for Ambient Escape.
Load both before you start. **These laptop rules override any skill or plan step that says** "render in the cloud", "stage the engine files", "copy to the laptop", "split into parts", "commit pieces into _system\parts", "give Omar the commands", or "render only 3-second previews". Here you render the full batch yourself with render.py.

## The daily run (do every step, in order)
1. **Get today's plans:**
   - `curl -sL https://raw.githubusercontent.com/omarjaradat2006-sudo/agent-hq/main/data/youtube/batch/bounce-theory.md`
   - `curl -sL https://raw.githubusercontent.com/omarjaradat2006-sudo/agent-hq/main/data/youtube/batch/ambient-escape.md`
   - Full data: `.../data/youtube/state.json` (same base URL).
   If either plan's date (in its first line) isn't today's Toronto date, STOP and tell Omar: it's an old plan that was already uploaded.
2. **Never remake an uploaded video:** check `_system\Upload Tool\logs\*_uploaded_log.json` first.
3. **Read the header of `_system\Local Render\render.py`.** It has the job-file contract.
4. **Build new formats** as functions in a new file in `_system\Bounce Engine` (e.g. `today1104.py`). Time escape/race/battle seeds with `dry=True`. Never edit `engine.py` or old files.
5. **Write the job files:** `_system\Local Render\jobs\bounce_today.py` and `ambient_today.py`. JOBS go in lineup order with thumbnails last, and DOWNLOADS list the ready clips. Ambient longs MUST loop the real downloaded clips named in the plan (R.loop_long with copyright-safe audio layers); never generate or draw scenes for them.
6. **Write `queue.json` and `UPLOAD SHEET.txt`** into each "Upload Today" folder. EVERY queue item gets a `slot` (0, 1, 2... in the plan's order).
7. **Render:** from `_system\Local Render`, run `python render.py bounce`, then `python render.py ambient`. They take a long time, so use a long timeout or run them in the background and check on them. If a render errors, fix that job and run the same command again (finished videos are skipped).
8. **Check every video** before uploading:
   - ffprobe: it has audio, the right duration and 1080x1920 (Shorts) or 1920x1080 (longs).
   - Make a contact sheet of each Bounce Theory video next to the same format's most recent upload. Every "Today's twist" must be VISIBLE, so redo any that look the same as before.
   - Ambient longs: confirm they really use the downloaded clips.
9. **Upload:** from `_system\Upload Tool`, run `python upload.py bounce`, then `python upload.py ambient`. Every video must end up scheduled in the 5 PM to 8 AM window, never left Private. If a browser login opens, tell Omar to click Allow.
10. **Mark Agent HQ:**
    - If `_system\agent-hq` doesn't exist, run `git clone https://github.com/omarjaradat2006-sudo/agent-hq "_system\agent-hq"`. Otherwise `git pull --rebase` inside it.
    - In `data/youtube/state.json`:
      - set `made: true` on every lineup item you uploaded (`lineup.channels["Bounce Theory"|"Ambient Escape"][*]`)
      - set `status: "done"` + `doneAt` (ISO now) on the ideas you used (the `★ new` ideas in the plans)
      - prepend 2 log entries: `{"t":now,"agent":"Producer","msg":"Made N <Channel> videos from today's lineup"}`
    - Keep the file's formatting, validate the JSON, then commit and push: `git -c user.name="Omar Jaradat" -c user.email="omarjaradat2006@gmail.com" commit -am "..."`, `git pull --rebase`, `git push`.
    - If the push needs a GitHub login, Omar approves it once in the browser.
11. **Clean up** once both channels are uploaded and scheduled:
    - run `echo y | python render.py clean` in `_system\Local Render`
    - empty `_system\parts` and `_system\Uploaded (delete later)`
    - delete leftover `.part`/temp files and stray `.mp4.json` race-data files in the Upload Today folders
    - **Never delete** anything still listed in a queue.json, the engine/tool code, `4 Channel Branding`, `_system\assets`, fonts, logs, tokens or client secrets.
12. **Finish** with a short report:
    - videos made and uploaded per channel, and the first and last publish times
    - one line per Bounce video on what's visibly new
    - anything you redid
    - space freed

## Ambient Escape animated explainers (8 Shorts a day: `explainer_pov` and `explainer_list`)
These are drawn entirely in code by `_system\Local Render\lib\explainer.py` (already on the laptop, importable from job files as `import explainer as X`). Read its header first: it documents the SPEC, scenes, poses and icons.
- **One-time check before the first one:** run `python -c "from PIL import features; print(features.check('raqm'))"`. If it prints False, run `pip install arabic-reshaper python-bidi` so the Arabic letters come out connected.
- **Build the SPEC from the slot's `note`.** The YouTube team writes the full spec there: POV hook, beats, the Arabic words with their English meaning, icons, source, end and CTA, or the list points with title, meaning, source and scene/pose. Wrap the one keyword per line in `*stars*`. Use `"style": "pov"` or `"list"` and a different `seed` per video.
- **Religious accuracy check (never skip):** before rendering, confirm every hadith reference (collection + number) and every ayah (surah:ayah) matches the wording you put on screen, and that the Arabic is copied exactly from the source text. If anything doesn't match or you can't confirm it, replace that point with one you can confirm, and tell Omar in the final report.
- **Job line:** `("SHORT 0N - <name>.mp4", lambda p: X.make(p, SPEC_N))`. Lengths: pov 15-25 s, list 30-50 s (`X.length(SPEC)` tells you before rendering; change the per-scene `secs` to fit).
- **Check:** make a contact sheet of each one. No text may overlap the figure or run off the screen, the Arabic letters must be connected, and the ﷺ symbol must show (not a box). Fix and re-render if not.
- **Upload sheet:** title from the lineup; the description gives the hadith or ayah reference in full plus 3-5 hashtags (#islam #hadith #shorts ...).
- If you improve explainer.py (a new scene, pose or icon), keep everything that works, back it up first (`explainer_backup_<date>.py`), and say what you added.

## Rules
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
