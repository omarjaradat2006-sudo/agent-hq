# Ambient Escape: today's batch (2026-11-03)

Planned by Omar's Agent HQ YouTube team. Omar approves everything, so make exactly these 17 videos, in this order, with these titles. Use the `ambient-escape-videos` skill for content rules, folders, upload sheet and scheduling.

**Rendering happens on Omar's laptop, not in this chat.** Write the job file `_system\Local Render\jobs\ambient_today.py` (contract at the top of `_system\Local Render\render.py`), plus queue.json and UPLOAD SHEET.txt, then give Omar the `python render.py ...` and upload commands. Render only 3-second previews of brand-new formats to check them; this overrides any skill step that says to render in the cloud.

Full data (ideas, footage, review): https://raw.githubusercontent.com/omarjaradat2006-sudo/agent-hq/main/data/youtube/state.json

> **STOP: this plan is from 2026-11-03, not today (2026-11-04). These videos were probably already made and uploaded.** Don't remake them. Tell Omar the YouTube team didn't plan today and ask him to have it run again (or to say "plan it yourself").

## Hard rules
1. **Long videos use the REAL downloaded clips below. Never draw, render or AI-generate a background scene for a slot whose clip says READY.** Download each clip from its link, check it with ffprobe, and list the downloaded files to Omar before rendering anything.
2. A generated or existing scene is only allowed for a slot whose clip is MISSING, and the finish message must name those slots.
3. Audio: copyright-safe only (synthesized rain/noise/fire/wind or CC0). Never reciter recordings, never Omar's voice. Put each clip's credit line in its video description.
4. Religious content must be accurate: ayat with surah:ayah, only authentic hadith with collection and number, double-check quiz answers.
5. **Every video must be scheduled, never left Private.** Give EVERY item in `queue.json` a `slot` (0, 1, 2... in this file's order: strongest Short first, longs in the evening slots). The upload tool (`_system\Upload Tool\upload.py`) turns slots into publish times spread across the 5 PM to 8 AM window, 1 video at a time, never overlapping the previous batch. Check `queue.json` before finishing: if any item has no `slot`, fix it.
6. You don't run the uploader yourself; Omar runs the upload command.
7. English only: every title, on-screen line, description and voice-over. Never Spanish or any other language.
8. Never remake a video that's already uploaded: check `_system\Upload Tool\logs\*_uploaded_log.json` and skip or change any title already there.

## The videos

Most of these are remixes of videos that already won. Keep each winner's recipe (format, hook, length, pacing) and change only the twist.

| Slot | Kind | Title | Format | Based on | Today's twist | Clip |
|---|---|---|---|---|---|---|
| S01 | Short | Hardship is never the end / Quran 94:6 #shorts #quran | ayah_reminder | Your hit: 'Allah hasn't forgotten you / Quran 93:3' · 1,336 views · 96% watched | Falling-snow loop; Quran 94:6 ('Indeed, with hardship comes ease'), 'ease' in yellow; 11 s | `AE-snowfall-night-01.mp4` MISSING (not_found) |
| S02 | Short | What Allah says about forgiveness 🤍 #shorts #islam #quran | what_allah_says | Your hit: 'What Allah says about your parents 🤍' · 1,296 views · 99% watched | Sunrise-clouds loop; Quran 4:110 ('whoever seeks forgiveness of Allah will find Allah Forgiving and Merciful'), 'Forgiving' in yellow; 13 s | `AE-sunrise-clouds-01.mp4` READY |
| S03 | Short | Every bounce, the ball gets BIGGER 😳 Can it fit the circle? #shorts | bounce sim (off-niche) | Your hit: 'Every bounce, the ball gets BIGGER 😳 Wait for the end' · 3,417 views · 76% watched | Same 27 s Bounce Engine scene, now violet and gold with a calm bell note per bounce and a yellow ball-size counter, no Islamic text |  |
| S04 | Short | Remember Me and I will remember you / Quran 2:152 #shorts #quran | ayah_reminder | Your hit: 'Where hearts find rest / Quran 13:28' · 1,175 views · 99% watched | Waterfall loop; Quran 2:152 ('So remember Me; I will remember you'), 'remember you' in yellow; 11 s | `AE-waterfall-forest-01.mp4` READY |
| S05 | Short | What Allah says about your rizq 🤍 #shorts #islam #quran | what_allah_says | Your hit: 'What Allah says about being grateful 🤍' · 950 views · 123% watched | Fire-flames loop; Quran 11:6 ('There is no creature on earth but that its provision is on Allah'), 'provision' in yellow; 13 s | `AE-fire-flames-01.mp4` READY |
| S06 | Short | The heaviest thing on your scale, and it costs nothing 🤍 #shorts #islam #reminder | question_hook_reflection | Your hit: '3 questions in the grave. Are you ready? 🤍' · 1,438 views · 108% watched | Rain-on-leaves loop; 'Nothing is heavier on the Scale than good character' (Sunan al-Tirmidhi 2002), 'good character' in yellow; 12 s | `AE-rain-leaves-01.mp4` READY |
| S07 | Short | The version of you that prays Fajr on time wins #shorts #salah | discipline_reminder | Your hit: 'The version of you that prays on time wins' · 1,457 views · 97% watched | Moon-night loop; same identity line aimed at Fajr, last line in yellow; 10 s | `AE-moon-night-01.mp4` READY |
| S08 | Short | How many prophets are named in the Quran? 🤔 #shorts #quran #quiz | number_quiz | Your hit: 'How many surahs are in the Quran? 🤔' · 912 views · 97% watched | Falling-snow loop; options 15 / 25 / 35, answer 25, then 'comment the one you love most'; 13 s | `AE-snowfall-night-01.mp4` MISSING (not_found) |
| S09 | Short | Which is the longest surah in the Quran? 🤍 #shorts #quiz | guess_the_surah | Your hit: 'Only real ones know this surah 🤍' · 1,017 views · 220% watched | Desert-dunes loop; options Al-Baqarah / Al-Imran / An-Nisa, answer Al-Baqarah (2), 3-s answer reveal; 13 s (format is 0.4x median overall, so one slot only) | `AE-desert-dunes-01.mp4` READY |
| S10 | Short | Allah never burdens a soul beyond its capacity / Quran 2:286 #shorts #quran | ayah_reminder | Your hit: 'You hate it now, but it may be good for you / Quran 2:216' · 1,112 views · 100% watched | Desert-dunes loop; Quran 2:286 ('Allah does not burden a soul beyond its capacity'), 'capacity' in yellow; 11 s | `AE-desert-dunes-01.mp4` READY |
| S11 | Short | Snowed in. No signal... so I watched the snow ❄️ #shorts #cozy #sleep | weather_story_short | Winning elsewhere: 'Cozy Winter Cabin in a Blizzard' by Istorium · 404,734 views · 2.9x their average | Snow-night loop, story text only (one new line per beat: lights flicker → wind rises → full snowfall), synthesized soft wind; 22 s | `AE-snowfall-night-01.mp4` MISSING (not_found) |
| S12 | Short | Surah Al-Ikhlas, line by line, in English 🤍 #shorts #quran | surah_meaning_text | Winning elsewhere: 'beautiful quran recitation ... surah Al fatiha' by Rah-e-noor · 42,023 views · 21.3x their average | Text only, no reciter audio: the 4 ayat of Surah 112 as English meaning, one line per 3 s over a waterfall loop with soft synthesized water ambience; 14 s | `AE-waterfall-forest-01.mp4` READY |
| S13 | Short | Fireplace on, snow outside. 3 hours of this on the channel 🔥❄️ #shorts | seasonal_room_short | Winning elsewhere: '(NO MID-ROLL ADS) Halloween Living Room Ambience' by Phantom Melodies · 100,549 views · 7.0x their average | Fire-flames loop with synthesized crackle and soft wind, no Islamic text, one line in yellow pointing to today's 3-hour Christmas-cozy video; 12 s | `AE-fire-flames-01.mp4` READY |
| S14 | Short | Complete the ayah 🤲 Only 1% get it right #shorts #quran #quiz | complete_the_ayah ★ NEW | Test: your guess_the_surah quizzes hit 1,017 views at 220% watched; the Complete the Ayah spec (done) is a different quiz mechanic with the same pull | Quran 13:28 'Verily, in the remembrance of Allah do ___ find rest' options hearts / eyes / souls, answer hearts, reference on screen, answer re-checked; 13 s | `AE-sunrise-clouds-01.mp4` READY |
| S15 | Short | What Allah says about your tongue 🤍 #shorts #islam #quran | what_allah_says | Your hit: 'What Allah says about being grateful 🤍' · 950 views · 123% watched | Moon-night loop; Quran 50:18 ('Man does not utter any word except that with him is an observer prepared [to record]'), 'observer' in yellow; 13 s | `AE-moon-night-01.mp4` READY |
| L1 | Long | Cozy Christmas Living Room ❄️ Crackling Fireplace & Snowfall / 3 Hours | christmas_cozy_long | Winning elsewhere: 'Cozy Christmas Ambience 4K' by Christmas Notes · 29,598 views · 6.0x their average; 'Halloween Living Room Ambience' by Phantom Melodies · 100,549 views · 7.0x | Scene: Christmas-tree lights loop with the snowy cabin clip crossfaded in every 25 min; audio: fire crackle -10 dB, soft wind -22 dB, no music, no thunder (different from yesterday's storm long) | `AE-christmas-lights-01.mp4 + AE-snowy-cabin-night-01.mp4` MISSING (wanted) |
| L2 | Long | Rain on the Window & Soft Piano 🌧️ Fall Asleep Fast / 3 Hours | rain_piano_long | Winning elsewhere: '(No Ads) Peaceful Rain and Piano Music for Healing Sleep' by Relaxation & Sleep · 65,934 views · 8.9x their average | Scene: landscape rain-on-window clip dimmed 30% after 20 min; audio: steady rain -9 dB, synthesized soft piano pad (own notes, no recorded music) -20 dB, no thunder (different from yesterday's cabin long) | `AE-rain-window-02.mp4` READY |

## Clips to download first

- **AE-snowfall-night-01.mp4** for S01, S08, S11: MISSING (not_found). Use another READY clip that fits, or an existing scene, and say so.
- **AE-sunrise-clouds-01.mp4** for S02, S14: READY (2160x3840 · 20s · 114.9 MB)
  - Download: `curl -L -o "AE-sunrise-clouds-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-03/AE-sunrise-clouds-01.mp4"`
  - Description credit: Video by Kanenori on Pixabay
- **AE-waterfall-forest-01.mp4** for S04, S12: READY (2160x3840 · 20s · 211.7 MB)
  - Download: `curl -L -o "AE-waterfall-forest-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-03/AE-waterfall-forest-01.mp4"`
  - Description credit: Video by Kanenori on Pixabay
- **AE-fire-flames-01.mp4** for S05, S13: READY (2160x2760 · 15s · 3.1 MB)
  - Download: `curl -L -o "AE-fire-flames-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-03/AE-fire-flames-01.mp4"`
  - Description credit: Video by Chris2Far on Pixabay
- **AE-rain-leaves-01.mp4** for S06: READY (2160x3840 · 10s · 21.6 MB)
  - Download: `curl -L -o "AE-rain-leaves-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-02/AE-rain-leaves-01.mp4"`
  - Description credit: Video by TravelGardenB on Pixabay
- **AE-moon-night-01.mp4** for S07, S15: READY (2160x3840 · 24s · 68.4 MB)
  - Download: `curl -L -o "AE-moon-night-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-02/AE-moon-night-01.mp4"`
  - Description credit: Video by Kanenori on Pixabay
- **AE-desert-dunes-01.mp4** for S09, S10: READY (2160x3840 · 17s · 32.4 MB)
  - Download: `curl -L -o "AE-desert-dunes-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-03/AE-desert-dunes-01.mp4"`
  - Description credit: Video by antonlukin on Pixabay
- **AE-christmas-lights-01.mp4 + AE-snowy-cabin-night-01.mp4** for L1: MISSING (not requested). Use another READY clip that fits, or an existing scene, and say so.
- **AE-rain-window-02.mp4** for L2: READY (1920x1080 · 33s · 17.7 MB)
  - Download: `curl -L -o "AE-rain-window-02.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-03/AE-rain-window-02.mp4"`
  - Description credit: Video by Iconikmg on Pixabay
- **AE-snowy-cabin-night-01.mp4** for L1: READY (3840x2160 · 30s · 32.0 MB)
  - Download: `curl -L -o "AE-snowy-cabin-night-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-02/AE-snowy-cabin-night-01.mp4"`
  - Description credit: Video by soundsrelaxing89 on Pixabay
- **AE-christmas-lights-01.mp4** for L1: READY (1920x1080 · 17s · 9.3 MB)
  - Download: `curl -L -o "AE-christmas-lights-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-03/AE-christmas-lights-01.mp4"`
  - Description credit: Video by Skylent on Pixabay

## Build specs for the new concepts

### Complete the Ayah (3-option quiz)  (`youtube-2026-10-26-4`)
*Ambient Escape · Short 20s*

Background: AE-starry-sky-01.mp4 (portrait, loop with 1 s cross-fade) or AE-foggy-forest-01.mp4, darkened 35%. Layout: line 1 (white, y=180): 'Complete the ayah 🤲'; line 2 (yellow, y=320): 'Only 1% get it right'. Main text (white, y=560-900): first half of the ayah in English. Three cards (y=1000-1400): A/B/C. 0-3 s question appears; 3-13 s 10-second countdown ring with soft tick (synthesized); 13 s correct card turns green with the full ayah and reference; 17-20 s 'Comment if you got it ✅'. Audio: soft pad drone + rain (synthesized), optional neutral AI voice reading the English only. NEVER a reciter recording. Today's two verified items (Sahih International wording): (1) 'Verily, in the remembrance of Allah…' A) do hearts find rest ✅ B) is wealth found C) are sins hidden — Ar-Ra'd 13:28. (2) 'For indeed, with hardship…' A) comes patience B) will be ease ✅ C) is reward — Ash-Sharh 94:5 (repeated in 94:6). Spare items for later days: 'Allah does not burden a soul…' → 'beyond that it can bear' (Al-Baqarah 2:286); 'So remember Me…' → 'I will remember you' (Al-Baqarah 2:152); 'And whoever relies upon Allah…' → 'then He is sufficient for him' (At-Talaq 65:3).
Description: Can you complete this ayah before the timer runs out? Comment your answer 🤲
Hashtags: #shorts #quran #islam #quiz #muslim
Tags: complete the ayah, quran quiz, islamic quiz, guess the ayah, quran verses, muslim shorts, islam quiz, ayah of the day, quran reminder, islamic shorts

## R&D upgrades

Only upgrades marked done are installed. Use those; never use one that is only approved.
- Installed (use it): Seasonal room longs for Ambient Escape  (`lab-2026-10-28-3`)
- Installed (use it): A Day in Jannah: AI-visual long videos  (`lab-2026-10-27-1`)

## When the batch is done
- Tell Omar which clip each video used (by file name) and any slot that fell back.
- Confirm every `queue.json` item has a `slot`, give Omar the upload command (`python "%USERPROFILE%\Downloads\YOUTUBE HQ\_system\Upload Tool\upload.py" ambient`), and say the tool schedules everything inside the 5 PM to 8 AM window by itself.
- If this session can push to omarjaradat2006-sudo/agent-hq: set `made: true` on each lineup item made and `status: "done"` (and `doneAt` now) on each used idea in data/youtube/state.json, then commit and push. Never change any other status. Otherwise list the idea ids so Omar can press "I did it" on the site.
- Then wait. When Omar says everything is uploaded/scheduled ("okay", "done"), clean up yourself with the delete permission you asked for at the start: empty `_system\Local Render\work`, `_system\parts` and `_system\Uploaded (delete later)`, plus any `.part`/temp files. Never delete anything still listed in a `queue.json`. Say how much space was freed. If you can't delete, tell him to run `python render.py clean`.

_Generated 2026-11-04 15:15 UTC_
