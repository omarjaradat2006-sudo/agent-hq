# Ambient Escape: today's batch (2026-10-28)

Planned by Omar's Agent HQ YouTube team. Omar approves everything, so make exactly these 17 videos, in this order, with these titles. Use the `ambient-escape-videos` skill for how to render, folders, upload sheet and scheduling.

Full data (ideas, footage, review): https://raw.githubusercontent.com/omarjaradat2006-sudo/agent-hq/main/data/youtube/state.json

## Hard rules
1. **Long videos use the REAL downloaded clips below. Never draw, render or AI-generate a background scene for a slot whose clip says READY.** Download each clip from its link, check it with ffprobe, and list the downloaded files to Omar before rendering anything.
2. A generated or existing scene is only allowed for a slot whose clip is MISSING, and the finish message must name those slots.
3. Audio: copyright-safe only (synthesized rain/noise/fire/wind or CC0). Never reciter recordings, never Omar's voice. Put each clip's credit line in its video description.
4. Religious content must be accurate: ayat with surah:ayah, only authentic hadith with collection and number, double-check quiz answers.
5. **Every video must be scheduled, never left Private.** Give EVERY item in `queue.json` a `slot` (0, 1, 2... in this file's order: strongest Short first, longs in the evening slots). The upload tool (`_system\Upload Tool\upload.py`) turns slots into publish times spread across the 5 PM to 8 AM window, 1 video at a time, never overlapping the previous batch. Check `queue.json` before finishing: if any item has no `slot`, fix it.
6. You don't run the uploader yourself; Omar runs the upload command.

## The videos

Most of these are remixes of videos that already won. Keep each winner's recipe (format, hook, length, pacing) and change only the twist.

| Slot | Kind | Title | Format | Based on | Today's twist | Clip |
|---|---|---|---|---|---|---|
| S01 | Short | Allah is near, He answers you / Quran 2:186 #shorts #quran | ayah_reminder | Your hit: 'Allah hasn't forgotten you / Quran 93:3' · 1,334 views · 96% watched | Starry sky loop; Quran 2:186 ('...indeed I am near. I respond to the invocation of the supplicant when he calls upon Me'), 'I am near' in yellow; 11 s | `AE-starry-sky-01.mp4` READY |
| S02 | Short | What Allah says about people who hurt you 🤍 #shorts #islam #quran | what_allah_says | Your hit: 'What Allah says about your parents 🤍' · 1,298 views · 102% watched | Forest mist loop; topic: people who hurt you, Quran 41:34 ('Repel evil with what is better...as though he was a devoted friend'); 13 s | `AE-forest-mist-01.mp4` READY |
| S03 | Short | The version of you that never misses Fajr is waiting #shorts #fajr | discipline_reminder | Your hit: 'Your salah is not a break from your day' · 869 views · 84% watched (and 'The version of you that prays on time wins' · 1,045 views on day 1) | Ocean waves at dawn; 'the version of you' identity line focused on Fajr, last line in yellow; 10 s | `AE-ocean-waves-01.mp4` READY |
| S04 | Short | Allah is closer to you than you think / Quran 50:16 #shorts #quran | ayah_reminder | Your hit: 'Where hearts find rest / Quran 13:28' · 1,173 views · 99% watched | Candle glow loop; Quran 50:16 ('We are closer to him than his jugular vein'), 'closer' in yellow; 11 s | `AE-candle-glow-01.mp4` READY |
| S05 | Short | What Allah says about your rizq 🤍 #shorts #islam #quran | what_allah_says | Your hit: 'What Allah says about being grateful 🤍' · 886 views · 101% watched | Snowfall loop (new scene); topic: provision, Quran 65:2-3 ('...He will make for him a way out and provide for him from where he does not expect'); 13 s | `AE-snowfall-01.mp4` MISSING (not_found) |
| S06 | Short | Which surah equals a third of the Quran? 🤍 #shorts #quiz | guess_the_surah | Your hit: 'Only real ones know this surah 🤍' · 1,017 views · 228% watched | Snowfall loop; clue: the surah equal to a third of the Quran; answer Al-Ikhlas (112), source Sahih al-Bukhari 5013 on screen; 3-s answer reveal; 13 s | `AE-snowfall-01.mp4` MISSING (not_found) |
| S07 | Short | How many prophets are named in the Quran? 🤔 #shorts #quran #quiz | number_quiz | Your hit: 'How many surahs are in the Quran? 🤔' · 912 views · 97% watched | Starry sky; options 15 / 25 / 40, answer 25, then 'comment the one you love most'; 13 s | `AE-starry-sky-01.mp4` READY |
| S08 | Short | Name the surah named after a spider in 3 seconds 🕷️ #shorts #quiz | guess_the_surah | Your hit: 'Guess the surah in 5 seconds ⏱️' · 870 views · 153% watched | Forest mist; 3-second timer instead of 5; answer Al-'Ankabut (29); 12 s | `AE-forest-mist-01.mp4` READY |
| S09 | Short | You hate it now, but it may be good for you / Quran 2:216 #shorts | worry_reminder | Your hit: 'Allah won't give you more than you can bear' · 921 views · 224% watched | Ocean waves; Quran 2:216 ('...perhaps you hate a thing and it is good for you... Allah knows, while you know not'); 11 s | `AE-ocean-waves-01.mp4` READY |
| S10 | Short | It's not a Fajr problem, it's a bedtime problem #shorts #fajr | discipline_reminder | Your hit: 'You missed Fajr again, didn't you?' · 815 views · 78% watched | Candle glow; reframes missed Fajr as sleeping too late, 3 short lines, last one in yellow: 'Fix your night, Fajr fixes itself'; 12 s | `AE-candle-glow-01.mp4` READY |
| S11 | Short | The first thing you'll be asked about on Judgement Day 🤍 #shorts | question_hook_reflection | Winning elsewhere: 'The Question That Leaves Every Soul Silent' by Tartil Offical · 4.6x their average (11,568 views) | Night rain window; answer: the prayer, per Jami' at-Tirmidhi 413 shown on screen; question held for 4 s before the reveal; 14 s | `AE-night-rain-window-01.mp4` READY |
| S12 | Short | It's raining? Say this dua 🌧️ #shorts #dua #sunnah | rain_dua_reminder | Winning elsewhere: event-timed Sunnah reminder by Basa'ir @alkamalii · 27.4x their recent median (159K views) | Night rain window; dua 'Allahumma sayyiban nafi'an' (O Allah, make it a beneficial rain) in Arabic transliteration + English, Sahih al-Bukhari 1032 on screen; post on a rainy day; 12 s | `AE-night-rain-window-01.mp4` READY |
| S13 | Short | 3 questions in the grave. Are you ready? 🤍 #shorts #islam #reminder | question_hook_reflection | Winning elsewhere: 'The Question That Leaves Every Soul Silent' by Tartil Offical · 4.6x their average (11,568 views) | Starry sky; the 3 questions (Who is your Lord? What is your religion? Who is this man sent among you?), Sunan Abi Dawud 4753 on screen; one question per 3 s; 13 s | `AE-starry-sky-01.mp4` READY |
| S14 | Short | The power went out... then the rain came 🌧️ #shorts #rain #sleep | Power Cut, Then the Rain (rain story Short) ★ NEW | Test: Ghibli Village Stories' power-cut rain story hit 178,950 views (4.3x), and your plain text Shorts dropped to 8-220 views in 2 days | Candle-lit silence → first drops → full rain on the window; story text only, no Islamic text; 22 s | `AE-night-rain-window-01.mp4` READY |
| S15 | Short | Read this if you feel nobody sees you / Quran 20:46 #shorts #quran | ayah_reminder | Your hit: 'Read this if you feel like giving up / Quran 94:5' · 656 views · 116% watched | Ocean waves; Quran 20:46 ('Fear not. Indeed, I am with you both; I hear and I see'), 'I hear and I see' in yellow; 11 s | `AE-ocean-waves-01.mp4` READY |
| L1 | Long | The Winter Library Hideaway ❄️ Snowy Window & Crackling Fireplace / 3 Hours for Sleep | Blizzard Cabin Fireplace + Brown Noise 3 Hours | Winning elsewhere: 'The Christmas Library Hideaway / ... Crackling Fireplace Ambience' by Tranquil Jazz Nook · 27.5x their average (22,389 views) | Scene: snowy window loop full-frame with the fireplace clip crossfaded in every 20 min; audio: fire crackle -8 dB, soft wind -20 dB, brown noise -24 dB, no music; 3:00:00. Test & Compare titles: 1) this one, 2) 'Snowy Night in a Cozy Library ❄️ Fireplace Sounds for Deep Sleep / 3 Hours', 3) 'Can't Sleep? Crackling Fireplace & Falling Snow ❄️ 3 Hours' | `AE-snowy-window-01.mp4, AE-fireplace-close-01.mp4` MISSING (wanted) |
| L2 | Long | Rainy Autumn Night in a Cozy Room 🍂 Rain on the Window & Fireplace / 3 Hours | rain_long | Winning elsewhere: 'Halloween Ambience 🎃 Cozy Living Room, Rain Sounds, Fireplace' by Phantom Melodies · 2.8x (36,581 views) and 'Cozy Fall Morning Ambience 🍂' by Delger Family Farm · 5.0x (20,284) | Scene: autumn rain loop (different from L1's snow); audio: steady rain -10 dB, soft fire crackle -18 dB, one distant thunder roll every ~25 min at -26 dB, no music; screen dims after 2 h; 3:00:00. Test & Compare titles: 1) this one, 2) 'Autumn Rain & Crackling Fireplace 🍂 Fall Asleep Fast / 3 Hours', 3) 'Cozy Rainy Fall Night 🍂 Rain Sounds for Sleeping / 3 Hours' | `AE-autumn-rain-01.mp4` READY |

## Clips to download first

- **AE-starry-sky-01.mp4** for S01, S07, S13: READY (28s · 15.6 MB)
  - Download: `curl -L -o "AE-starry-sky-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-10-26/AE-starry-sky-01.mp4"`
  - Description credit: Video by bellergy on Pixabay
- **AE-forest-mist-01.mp4** for S02, S08: READY (1080x1920 · 54s · 71.2 MB)
  - Download: `curl -L -o "AE-forest-mist-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-10-27/AE-forest-mist-01.mp4"`
  - Description credit: Video by Matthias_Groeneveld on Pixabay
- **AE-ocean-waves-01.mp4** for S03, S09, S15: READY (1080x1920 · 16s · 10.0 MB)
  - Download: `curl -L -o "AE-ocean-waves-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-10-26/AE-ocean-waves-01.mp4"`
  - Description credit: Video by Mario_Krimer on Pixabay
- **AE-candle-glow-01.mp4** for S04, S10: READY (1080x1920 · 20s · 2.0 MB)
  - Download: `curl -L -o "AE-candle-glow-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-10-27/AE-candle-glow-01.mp4"`
  - Description credit: Video by Placidplace on Pixabay
- **AE-snowfall-01.mp4** for S05, S06: MISSING (not_found). Use another READY clip that fits, or an existing scene, and say so.
- **AE-night-rain-window-01.mp4** for S11, S12, S14: READY (2160x3840 · 10s · 16.7 MB)
  - Download: `curl -L -o "AE-night-rain-window-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-10-28/AE-night-rain-window-01.mp4"`
  - Description credit: Video by Turning_Pages on Pixabay
- **AE-snowy-window-01.mp4, AE-fireplace-close-01.mp4** for L1: MISSING (not requested). Use another READY clip that fits, or an existing scene, and say so.
- **AE-autumn-rain-01.mp4** for L2: READY (1920x1080 · 19s · 12.1 MB)
  - Download: `curl -L -o "AE-autumn-rain-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-10-28/AE-autumn-rain-01.mp4"`
  - Description credit: Video by Life-Of-Vids on Pixabay
- **AE-snowy-window-01.mp4** for L1: READY (3840x2160 · 26s · 11.4 MB)
  - Download: `curl -L -o "AE-snowy-window-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-10-28/AE-snowy-window-01.mp4"`
  - Description credit: Video by briroseee on Pixabay
- **AE-fireplace-close-01.mp4** for L1: READY (3840x2160 · 10s · 23.5 MB)
  - Download: `curl -L -o "AE-fireplace-close-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-10-28/AE-fireplace-close-01.mp4"`
  - Description credit: Video by MountainDweller on Pixabay

## Build specs for the new concepts

### Power Cut, Then the Rain (rain story Short)  (`youtube-2026-10-28-2`)
*Ambient Escape · Rain story Short*

Footage: AE-night-rain-window-01.mp4 (portrait) for the rain section, AE-candle-glow-01.mp4 for the opening. 0-4 s: candle clip, near silence (room tone -40 dB), text 'The power just went out... 🕯️'. 4-8 s: crossfade to the night window, first single drops (synthesized drip, -20 dB), text 'Then I heard it...'. 8-18 s: full rain on glass (rain synth -10 dB) plus one distant rumble at 12 s (-24 dB), text 'Rain. Finally. 🌧️'. 18-22 s: hold the rain; final line in yellow: 'Save this for nights you can't sleep 🤍'. Loop: last frame matches the first candle flicker so it replays smoothly. No voice, no music, no faces.
Description: The power went out... then the rain came. Save this for the nights you can't sleep.
Hashtags: #rain #rainsounds #sleep #cozy #shorts
Tags: rain sounds, rain at night, rain on window, power cut rain, cozy rain, sleep sounds, rainy night, relaxing rain, rain short, calm night

## When the batch is done
- Tell Omar which clip each video used (by file name) and any slot that fell back.
- Confirm every `queue.json` item has a `slot`, give Omar the upload command (`python "%USERPROFILE%\Downloads\YOUTUBE HQ\_system\Upload Tool\upload.py" ambient`), and say the tool schedules everything inside the 5 PM to 8 AM window by itself.
- If this session can push to omarjaradat2006-sudo/agent-hq: set `made: true` on each lineup item made and `status: "done"` (and `doneAt` now) on each used idea in data/youtube/state.json, then commit and push. Never change any other status. Otherwise list the idea ids so Omar can press "I did it" on the site.

_Generated 2026-10-28 22:29 UTC_
