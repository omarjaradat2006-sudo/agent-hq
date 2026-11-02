# Ambient Escape: today's batch (2026-11-02)

Planned by Omar's Agent HQ YouTube team. Omar approves everything, so make exactly these 17 videos, in this order, with these titles. Use the `ambient-escape-videos` skill for content rules, folders, upload sheet and scheduling.

**Rendering happens on Omar's laptop, not in this chat.** Write the job file `_system\Local Render\jobs\ambient_today.py` (contract at the top of `_system\Local Render\render.py`), plus queue.json and UPLOAD SHEET.txt, then give Omar the `python render.py ...` and upload commands. Render only 3-second previews of brand-new formats to check them; this overrides any skill step that says to render in the cloud.

Full data (ideas, footage, review): https://raw.githubusercontent.com/omarjaradat2006-sudo/agent-hq/main/data/youtube/state.json

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
| S01 | Short | Allah will bring ease after hardship / Quran 65:7 #shorts #quran | ayah_reminder | Your hit: 'Allah hasn't forgotten you / Quran 93:3' · 1,336 views · 96% watched | Starry sky loop; Quran 65:7 ('Allah will bring about, after hardship, ease'), 'ease' in yellow; 11 s | `AE-starry-sky-01.mp4` READY |
| S02 | Short | What Allah says about patience 🤍 #shorts #islam #quran | what_allah_says | Your hit: 'What Allah says about your parents 🤍' · 1,296 views · 99% watched | Forest mist loop; topic: patience, Quran 2:153 ('Indeed, Allah is with the patient'); 13 s | `AE-forest-mist-01.mp4` READY |
| S03 | Short | Every bounce, the ring gets SMALLER 😳 Wait for the end #shorts | bounce sim (off-niche) | Your hit: 'Every bounce, the ball gets BIGGER 😳 Wait for the end' · 3,417 views · 76% watched | Same 27 s Bounce Engine scene, now the ring shrinks in teal and gold with a calm bell note per bounce and no Islamic text; generated, no footage |  |
| S04 | Short | Don't despair of Allah's mercy / Quran 39:53 #shorts #quran | ayah_reminder | Your hit: 'Where hearts find rest / Quran 13:28' · 1,175 views · 99% watched | Ocean waves loop; Quran 39:53 ('Do not despair of the mercy of Allah'), 'mercy' in yellow; 11 s | `AE-ocean-waves-01.mp4` READY |
| S05 | Short | What Allah says about your plans 🤍 #shorts #islam #quran | what_allah_says | Your hit: 'What Allah says about being grateful 🤍' · 950 views · 123% watched | Candle glow loop; topic: plans, Quran 3:159 ('when you have decided, then rely upon Allah'); 13 s | `AE-candle-glow-01.mp4` READY |
| S06 | Short | 3 things that follow you after you die 🤍 #shorts #islam #reminder | question_hook_reflection | Your hit: '3 questions in the grave. Are you ready? 🤍' · 1,438 views · 108% watched | Night rain window; ongoing charity, beneficial knowledge, a righteous child who prays for him (Sahih Muslim 1631 on screen); one item per 3 s; 13 s | `AE-night-rain-window-01.mp4` READY |
| S07 | Short | The version of you that prays Isha on time wins #shorts #salah | discipline_reminder | Your hit: 'The version of you that prays on time wins' · 1,457 views · 97% watched | Moon night loop; same identity line aimed at Isha, last line in yellow; 10 s | `AE-moon-night-01.mp4` READY |
| S08 | Short | How many verses are in Surah Al-Fatiha? 🤔 #shorts #quran #quiz | number_quiz | Your hit: 'How many surahs are in the Quran? 🤔' · 912 views · 97% watched | Starry sky; options 5 / 7 / 9, answer 7, then 'comment the one you love most'; 13 s | `AE-starry-sky-01.mp4` READY |
| S09 | Short | Which surah has no Bismillah at its start? 🤍 #shorts #quiz | guess_the_surah | Your hit: 'Only real ones know this surah 🤍' · 1,017 views · 220% watched | Forest mist; answer At-Tawbah (9), 3-s answer reveal; 13 s | `AE-forest-mist-01.mp4` READY |
| S10 | Short | He is with you wherever you are / Quran 57:4 #shorts #quran | ayah_reminder | Your hit: 'Allah is closer to you than you think / Quran 50:16' · 785 views · 141% watched | Ocean waves loop; Quran 57:4 ('And He is with you wherever you are'), 'with you' in yellow; 11 s | `AE-ocean-waves-01.mp4` READY |
| S11 | Short | No signal... so I listened to the rain 🌧️ #shorts #rain #sleep | Rain story Short | Winning elsewhere: 'Power Cut on a Hot Summer Night 🌙 Then the Monsoon Rain Begins!' by Ghibli Village Stories · 4.3x their average (178,950 views) | Candle-lit silence → first drops on the window → full rain, story text only, new line each beat; 22 s | `AE-night-rain-window-01.mp4` READY |
| S12 | Short | Surah Al-Fatiha, line by line, in English 🤍 #shorts #quran | fatiha_meaning_text | Winning elsewhere: 'beautiful quran recitation ... surah Al fatiha' by Rah-e-noor · 21.0x their average (41,857 views) | Text only, no reciter audio: the 7 ayat as English meaning, one line per 3 s over a rain-on-leaves loop with synthesized rain, last line in yellow; 20 s | `AE-rain-leaves-01.mp4` READY |
| S13 | Short | Snowed in. Phone off. 3 hours of this on the channel ❄️🔥 #shorts | seasonal_room_short | Winning elsewhere: 'Cozy Winter Cabin in a Blizzard' by Istorium · 2.9x their average (404,734 views) | Fireplace loop with synthesized crackle and soft wind, no Islamic text, one line in yellow, points to the 3-hour long; 15 s | `AE-fire-portrait-01.mp4` MISSING (not_found) |
| S14 | Short | Complete the ayah 🤲 Only 1% get it right #shorts #quran #quiz | Complete the Ayah (3-option quiz) ★ NEW | Test: your guess_the_surah quizzes reach 1,017 views at 220% watched; a complete-the-verse quiz adds a choice to tap | Follow the approved Complete the Ayah spec; verse reference on screen and answer re-checked against the Quran text; 20 s | `AE-starry-sky-01.mp4` READY |
| S15 | Short | What Allah says about your night prayer 🤍 #shorts #islam #quran | what_allah_says | Your hit: 'What Allah says about being grateful 🤍' · 950 views · 123% watched | Moon night loop; topic: tahajjud, Quran 17:79 ('...pray with it as additional worship for you; it is expected that your Lord will resurrect you to a praised station'); 13 s | `AE-moon-night-01.mp4` READY |
| L1 | Long | Heavy Rain & Thunder on a Stormy Night ⛈️ Dark Screen for Sleep / 3 Hours | rain_thunder_long | Winning elsewhere: 'Heavy Rain and Thunder Sounds for Sleeping / Defeat Insomnia ... Black Screen' by Deep Sleep Rain · 9.5x their average (54,089 views) | Scene: dark storm-cloud loop dimmed to 85% black after 20 min; audio: heavy rain -8 dB, thunder roll every ~12 min -18 dB, wind -26 dB, brown noise -30 dB, no music; 3:00:00. Test & Compare titles: 1) this one, 2) 'Heavy Rain and Thunder Storm ⛈️ Fall Asleep Fast / Dark Screen 3 Hours', 3) 'Can't Sleep? Thunderstorm & Pouring Rain 🌧️ Black Screen' | `AE-storm-clouds-01.mp4` READY |
| L2 | Long | Snowed In at a Mountain Lodge ❄️ Blizzard Wind & Crackling Fire / 3 Hours | blizzard_cabin_long | Winning elsewhere: 'Cozy Winter Cabin in a Blizzard' by Istorium · 2.9x their average (404,734 views); 'Halloween Living Room Ambience' by Phantom Melodies · 6.8x (99,386) | Scene: snowy cabin night loop, fireplace clip crossfaded in every 20 min; audio: blizzard wind -12 dB, fire crackle -14 dB, brown noise -28 dB, no music, no thunder (differs from L1); 3:00:00. Test & Compare titles: 1) this one, 2) 'Blizzard Outside, Fire Inside ❄️🔥 Cozy Cabin for Deep Sleep / 3 Hours', 3) 'Winter Storm Cabin Ambience ❄️ Snowstorm & Fireplace' | `AE-snowy-cabin-night-01.mp4 + AE-fireplace-close-01.mp4` MISSING (wanted) |

## Clips to download first

- **AE-starry-sky-01.mp4** for S01, S08, S14: READY (28s · 15.6 MB)
  - Download: `curl -L -o "AE-starry-sky-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-10-26/AE-starry-sky-01.mp4"`
  - Description credit: Video by bellergy on Pixabay
- **AE-forest-mist-01.mp4** for S02, S09: READY (1080x1920 · 54s · 71.2 MB)
  - Download: `curl -L -o "AE-forest-mist-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-10-27/AE-forest-mist-01.mp4"`
  - Description credit: Video by Matthias_Groeneveld on Pixabay
- **AE-ocean-waves-01.mp4** for S04, S10: READY (1080x1920 · 16s · 10.0 MB)
  - Download: `curl -L -o "AE-ocean-waves-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-10-26/AE-ocean-waves-01.mp4"`
  - Description credit: Video by Mario_Krimer on Pixabay
- **AE-candle-glow-01.mp4** for S05: READY (1080x1920 · 20s · 2.0 MB)
  - Download: `curl -L -o "AE-candle-glow-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-10-27/AE-candle-glow-01.mp4"`
  - Description credit: Video by Placidplace on Pixabay
- **AE-night-rain-window-01.mp4** for S06, S11: READY (2160x3840 · 10s · 16.7 MB)
  - Download: `curl -L -o "AE-night-rain-window-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-10-28/AE-night-rain-window-01.mp4"`
  - Description credit: Video by Turning_Pages on Pixabay
- **AE-moon-night-01.mp4** for S07, S15: READY (2160x3840 · 24s · 68.4 MB)
  - Download: `curl -L -o "AE-moon-night-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-02/AE-moon-night-01.mp4"`
  - Description credit: Video by Kanenori on Pixabay
- **AE-rain-leaves-01.mp4** for S12: READY (2160x3840 · 10s · 21.6 MB)
  - Download: `curl -L -o "AE-rain-leaves-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-02/AE-rain-leaves-01.mp4"`
  - Description credit: Video by TravelGardenB on Pixabay
- **AE-fire-portrait-01.mp4** for S13: MISSING (not_found). Use another READY clip that fits, or an existing scene, and say so.
- **AE-storm-clouds-01.mp4** for L1: READY (1920x1080 · 40s · 25.7 MB)
  - Download: `curl -L -o "AE-storm-clouds-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-02/AE-storm-clouds-01.mp4"`
  - Description credit: Video by Macb3t on Pixabay
- **AE-snowy-cabin-night-01.mp4 + AE-fireplace-close-01.mp4** for L2: MISSING (not requested). Use another READY clip that fits, or an existing scene, and say so.
- **AE-fireplace-close-01.mp4** for L2: READY (3840x2160 · 10s · 23.5 MB)
  - Download: `curl -L -o "AE-fireplace-close-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-10-28/AE-fireplace-close-01.mp4"`
  - Description credit: Video by MountainDweller on Pixabay
- **AE-snowy-cabin-night-01.mp4** for L2: READY (3840x2160 · 30s · 32.0 MB)
  - Download: `curl -L -o "AE-snowy-cabin-night-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-02/AE-snowy-cabin-night-01.mp4"`
  - Description credit: Video by soundsrelaxing89 on Pixabay

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

_Generated 2026-11-02 23:13 UTC_
