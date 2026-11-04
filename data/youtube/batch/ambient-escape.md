# Ambient Escape: today's batch (2026-11-04)

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
| S01 | Short | POV: someone cuts you off in traffic 🤍 #shorts #islam #hadith | explainer_pov | Winning elsewhere: '8 Islamic ways to unblock your rizq' / POV hadith explainers by @soulofbaraqah / @tanzil_quran (TikTok, Omar's pick) | POV hook: "POV: someone cuts you off in traffic" / beats: "HONK. He cut right in front of you." (red) ; "Your hands tighten on the wheel" ; "Everything in you wants to shout back" / reveal: ليس الشديد=the strong is not, بالصرعة=the one who overpowers, إنما الشديد=the strong one is only, الذي يملك نفسه=who controls himself, عند الغضب=when angry / icons: no, throw, flex, calm, gauge / source: Sahih al-Bukhari 6114, Sahih Muslim 2609 / end: "The strongest move is staying calm." / "Be strong today." / cta: "Send this to a friend who drives angry" |  |
| S02 | Short | He hears you and He sees you / Quran 20:46 #shorts #quran | ayah_reminder | Your hit: 'Allah hasn't forgotten you / Quran 93:3' · 1,336 views · 96% watched | Moon-night loop; Quran 20:46 ('Fear not; indeed I am with you both, hearing and seeing'), 'hearing and seeing' in yellow; 11 s | `AE-moon-night-01.mp4` READY |
| S03 | Short | 5 Quran & Sunnah habits that open your rizq 🤍 #shorts #islam | explainer_list | Winning elsewhere: '8 Islamic ways to unblock your rizq' / POV hadith explainers by @soulofbaraqah / @tanzil_quran (TikTok, Omar's pick) | hook: "5 habits that open the doors of *rizq*" (door_light) / 1) "Have *taqwa*" — "Whoever fears Allah, He makes a way out and provides from where he never expected" — Quran 65:2-3 — door_light/stand ; 2) "Keep family *ties*" — "Whoever wants his provision widened should keep his family ties" — Sahih al-Bukhari 5986, Sahih Muslim 2557 — lamp_sofa/sit ; 3) "Be *grateful*" — "If you are grateful, I will surely give you more" — Quran 14:7 — sunset_birds/dua ; 4) "Rely on *Allah*" — "Trust Him as the birds do: they leave hungry and return full" — Jami at-Tirmidhi 2344 — sunset_birds/walk ; 5) "Seek *forgiveness*" — "Ask your Lord for forgiveness… He will send rain and increase your wealth" — Quran 71:10-12 — field_rain/dua / end: "Rizq is in Allah's hands." / "Do your part, then trust Him." / cta: "Send this to someone stressed about money" |  |
| S04 | Short | What Allah says when you feel lost 🤍 #shorts #islam #quran | what_allah_says | Your hit: 'What Allah says about your parents 🤍' · 1,296 views · 99% watched | Sunrise-cloud loop; text 'He found you lost and guided you' with Quran 93:7 on screen, 'guided' in yellow; 12 s | `AE-sunrise-clouds-01.mp4` READY |
| S05 | Short | POV: your mum asks for help the second you sit down 🤍 #shorts #islam | explainer_pov | Winning elsewhere: '8 Islamic ways to unblock your rizq' / POV hadith explainers by @soulofbaraqah / @tanzil_quran (TikTok, Omar's pick) | POV hook: "POV: your mum asks for help the second you sit down" / beats: "You just got home. Everything hurts." (red) ; "She says: 'Can you help me?'" ; "You almost sigh" / reveal: فلا تقل لهما=so do not say to them, أف="uff", ولا تنهرهما=nor scold them, وقل لهما=and speak to them, قولا كريما=noble words / icons: no, gauge, throw, hand, heart / source: Quran 17:23 (Al-Isra) / end: "Speak softly today." / "Even when you are tired." / cta: "Send this to a friend who needs to call their mum" |  |
| S06 | Short | Every bounce, the ball gets BIGGER 😳 Will it still fit? #shorts | bounce sim (off-niche) | Your hit: 'Every bounce, the ball gets BIGGER 😳 Wait for the end' · 3,417 views · 76% watched | Same 27 s Bounce Engine scene, now teal and magenta with a calm bell per bounce, a yellow 'SIZE x1.0 → x6.0' counter and a gap in the ring it must fit through; no Islamic text |  |
| S07 | Short | 5 things the Prophet ﷺ said about your tongue 🤍 #shorts #islam | explainer_list | Winning elsewhere: '8 Islamic ways to unblock your rizq' / POV hadith explainers by @soulofbaraqah / @tanzil_quran (TikTok, Omar's pick) | hook: "5 things the Prophet ﷺ said about your *tongue*" (spotlight) / 1) "Speak *good* or stay silent" — "Whoever believes in Allah and the Last Day, let him speak good or keep silent" — Sahih al-Bukhari 6018, Sahih Muslim 47 — table_lamp/sit ; 2) "Leave what is *pointless*" — "Part of the excellence of a person's Islam is leaving what does not concern him" — Jami at-Tirmidhi 2317 — spotlight/stand ; 3) "Avoid *backbiting*" — "Mentioning your brother with what he dislikes" — Sahih Muslim 2589 — market/walk ; 4) "Words are *recorded*" — "He does not utter a word except that a watcher is ready" — Quran 50:18 — spotlight/none ; 5) "Say what is *best*" — "Tell My servants to say that which is best" — Quran 17:53 — lamp_sofa/give / end: "Your words are a trust." / "Spend them well." / cta: "Send this to a friend who talks too much" |  |
| S08 | Short | The version of you that never misses Asr wins #shorts #salah #muslim | discipline_reminder | Your hit: 'The version of you that prays on time wins' · 1,458 views · 97% watched | Desert-dune loop; the line 'The version of you that never misses Asr wins' with 'wins' in yellow; synthesized soft pad; 9 s | `AE-desert-dunes-01.mp4` READY |
| S09 | Short | POV: a stranger insults you in the comments 🤍 #shorts #islam | explainer_pov | Winning elsewhere: '8 Islamic ways to unblock your rizq' / POV hadith explainers by @soulofbaraqah / @tanzil_quran (TikTok, Omar's pick) | POV hook: "POV: a stranger insults you in the comments" / beats: "'You're so cringe.' 47 likes." (red) ; "Your thumbs are already typing" ; "You delete it. Then you type it again" / reveal: وإذا خاطبهم الجاهلون=when the ignorant address them, قالوا=they say, سلاما="Peace" / icons: scale, hand, heart / source: Quran 25:63 (Al-Furqan) / end: "Do not feed it." / "Peace is a reply too." / cta: "Send this to a friend who argues in the comments" |  |
| S10 | Short | 4 things the Prophet ﷺ did before sleep 🤍 #shorts #islam #sunnah | explainer_list | Winning elsewhere: '8 Islamic ways to unblock your rizq' / POV hadith explainers by @soulofbaraqah / @tanzil_quran (TikTok, Omar's pick) | hook: "4 things the Prophet ﷺ did before *sleep*" (desk_night) / 1) "Make *wudu*" — "When you go to bed, make wudu like for prayer, then lie on your right side" — Sahih al-Bukhari 247 — desk_night/sit ; 2) "Recite *Ayat al-Kursi*" — "A protector from Allah stays with you until morning" — Sahih al-Bukhari 2311 — masjid_night/sit ; 3) "Last two verses of *Al-Baqarah*" — "Whoever recites them at night, they will suffice him" — Sahih al-Bukhari 5009, Sahih Muslim 807 — table_lamp/sit ; 4) "Say *tasbih*" — "SubhanAllah 33, Alhamdulillah 33, Allahu Akbar 34" — Sahih Muslim 2727 — dark/dua / end: "End the day with His name." / "Sleep well." / cta: "Send this to a friend who scrolls till 3 AM" |  |
| S11 | Short | 5 things you will be asked about on Judgement Day 🤍 #shorts #islam | question_hook_reflection | Your hit: '3 questions in the grave. Are you ready? 🤍' · 1,439 views · 108% watched | Flame loop; five on-screen lines in order (your life, your youth, how you earned your wealth, how you spent it, what you did with your knowledge) from Jami at-Tirmidhi 2416; 'youth' in yellow; 15 s | `AE-fire-flames-01.mp4` READY |
| S12 | Short | POV: your Fajr alarm rings and the bed is warm 🤍 #shorts #islam | explainer_pov | Winning elsewhere: '8 Islamic ways to unblock your rizq' / POV hadith explainers by @soulofbaraqah / @tanzil_quran (TikTok, Omar's pick) | POV hook: "POV: your Fajr alarm rings and your bed is warm" / beats: "5:12 AM. The alarm again." (red) ; "'Five more minutes…'" ; "The blanket feels like a hug" / reveal: من صلى الصبح=whoever prays Fajr, فهو=then he is, في ذمة الله=in Allah's protection / icons: hand, heart, star / source: Sahih Muslim 657 / end: "Stand up for Fajr." / "You are in His care." / cta: "Send this to a friend who snoozes Fajr" |  |
| S13 | Short | 4 things that happen when you stay patient 🤍 #shorts #islam | explainer_list | Winning elsewhere: '8 Islamic ways to unblock your rizq' / POV hadith explainers by @soulofbaraqah / @tanzil_quran (TikTok, Omar's pick) | hook: "4 things that happen when you stay *patient*" (window_dawn) / 1) "Everything is *good* for you" — "The believer's affair is wonderful: patient in hardship, it is good for him" — Sahih Muslim 2999 — window_dawn/stand ; 2) "Sins are *forgiven*" — "Even a thorn prick, worry or fatigue — Allah expiates sins through it" — Sahih al-Bukhari 5641, Sahih Muslim 2573 — lamp_sofa/sit ; 3) "Success is *near*" — "Be patient, persevere, and fear Allah that you may succeed" — Quran 3:200 — field_rain/stand ; 4) "Reward *without limit*" — "The patient will be given their reward without account" — Quran 39:10 — sunset_birds/none / end: "Patience is never wasted." / "Keep going." / cta: "Send this to someone going through a hard time" |  |
| S14 | Short | Don't lose hope, don't grieve / Quran 3:139 #shorts #quran #islam | ayah_reminder | Your hit: 'Where hearts find rest / Quran 13:28' · 1,175 views · 99% watched | Forest-waterfall loop; Quran 3:139 ('Do not weaken and do not grieve, and you will be superior if you are believers'), 'superior' in yellow; 12 s | `AE-waterfall-forest-01.mp4` READY |
| S15 | Short | Rain in London tonight 🌧️ let it play #shorts #rain #sleep | Named-city rain Short ★ NEW | Winning elsewhere: 'pune weather ☁️ #punerain #rainsounds' by Ashwini ganesh · 71,160 views · 88.4x their average | Follow the Named-city rain spec: night-street rain loop, 'RAIN IN LONDON TONIGHT', synthesized rain only; 20 s | `AE-city-rain-night-01.mp4` READY |
| L1 | Long | Rain Sounds for Deep Sleep / Escape to a Misty Forest Cabin / 3 Hours | rain_cabin_long | Winning elsewhere: 'Rain Sounds for Deep Sleep / Escape to a Cozy Forest Cabin' by Rainful · 33,502 views · 11.6x their average | Scene: landscape forest-cabin clip looped seamlessly, dimmed 25% after 30 min; audio: steady rain on roof -9 dB, distant thunder every ~12 min -20 dB, no music (different from yesterday's fire and piano longs) | `AE-forest-cabin-01.mp4` READY |
| L2 | Long | November Fireplace Ambience / Soft Piano & Crackling Fire / 3 Hours | fireplace_piano_long | Winning elsewhere: '🍂 November Fireplace Ambience / Slow Jazz Guitar & Piano...' by Golden Hour Jazz · 153,974 views · 3.0x their average; 'Enchanted Christmas Library' by Tranquil Jazz Nook · 103,838 views · 11.3x | Scene: landscape fireplace clip looped seamlessly; audio: crackling fire -8 dB, synthesized slow music-box notes (own notes, no recorded music) -22 dB, brown noise -30 dB, no rain, no thunder | `AE-fireplace-room-01.mp4` READY |

## Clips to download first

- **AE-moon-night-01.mp4** for S02: READY (2160x3840 · 24s · 68.4 MB)
  - Download: `curl -L -o "AE-moon-night-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-02/AE-moon-night-01.mp4"`
  - Description credit: Video by Kanenori on Pixabay
- **AE-sunrise-clouds-01.mp4** for S04: READY (2160x3840 · 20s · 114.9 MB)
  - Download: `curl -L -o "AE-sunrise-clouds-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-03/AE-sunrise-clouds-01.mp4"`
  - Description credit: Video by Kanenori on Pixabay
- **AE-desert-dunes-01.mp4** for S08: READY (2160x3840 · 17s · 32.4 MB)
  - Download: `curl -L -o "AE-desert-dunes-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-03/AE-desert-dunes-01.mp4"`
  - Description credit: Video by antonlukin on Pixabay
- **AE-fire-flames-01.mp4** for S11: READY (2160x2760 · 15s · 3.1 MB)
  - Download: `curl -L -o "AE-fire-flames-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-03/AE-fire-flames-01.mp4"`
  - Description credit: Video by Chris2Far on Pixabay
- **AE-waterfall-forest-01.mp4** for S14: READY (2160x3840 · 20s · 211.7 MB)
  - Download: `curl -L -o "AE-waterfall-forest-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-03/AE-waterfall-forest-01.mp4"`
  - Description credit: Video by Kanenori on Pixabay
- **AE-city-rain-night-01.mp4** for S15: READY (1080x1920 · 19s · 14.0 MB)
  - Download: `curl -L -o "AE-city-rain-night-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-04/AE-city-rain-night-01.mp4"`
  - Description credit: Video by BINGIL on Pixabay
- **AE-forest-cabin-01.mp4** for L1: READY (1920x1080 · 60s · 70.7 MB)
  - Download: `curl -L -o "AE-forest-cabin-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-04/AE-forest-cabin-01.mp4"`
  - Description credit: Video by Shayea_Kim on Pixabay
- **AE-fireplace-room-01.mp4** for L2: READY (3840x2160 · 34s · 216.9 MB)
  - Download: `curl -L -o "AE-fireplace-room-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-04/AE-fireplace-room-01.mp4"`
  - Description credit: Video by BFCMUSIC on Pixabay
- **AE-autumn-leaves-01.mp4** for S06: READY (1080x1920 · 10s · 7.9 MB)
  - Download: `curl -L -o "AE-autumn-leaves-01.mp4" "https://github.com/omarjaradat2006-sudo/agent-hq/releases/download/footage-2026-11-04/AE-autumn-leaves-01.mp4"`
  - Description credit: Video by kinchan_kinchan on Pixabay

## Build specs for the new concepts

### Rain in <City> Tonight (named-city rain Short)  (`youtube-2026-11-04-2`)
*Ambient Escape · Named-city rain Short*

Footage: AE-city-rain-night-01.mp4 (portrait stock rain on a night street, no faces or logos); loop it seamlessly to 20 s. Audio: synthesized steady rain -9 dB, soft low wind -26 dB, no music, no thunder. On-screen (white, y 120-1450): line 1 'RAIN IN LONDON TONIGHT' at y=200 (use a different real city each day: London, Istanbul, Toronto, Cairo, Seoul), line 2 yellow 'Put your phone down. Let it play.' at y=1300. Length 20 s. Description: 'Rain in <City> tonight. Sleep sounds from Ambient Escape.' Hashtags: #shorts #rain #rainsounds #sleep #cozy. Tags: rain, rain sounds, city rain, rainy night, sleep sounds, relaxing rain, ambient, cozy, night rain, rain asmr.

## R&D upgrades

Only upgrades marked done are installed. Use those; never use one that is only approved.
- Installed (use it): Seasonal room longs for Ambient Escape  (`lab-2026-10-28-3`)
- Installed (use it): A Day in Jannah: AI-visual long videos  (`lab-2026-10-27-1`)

## When the batch is done
- Tell Omar which clip each video used (by file name) and any slot that fell back.
- Confirm every `queue.json` item has a `slot`, give Omar the upload command (`python "%USERPROFILE%\Downloads\YOUTUBE HQ\_system\Upload Tool\upload.py" ambient`), and say the tool schedules everything inside the 5 PM to 8 AM window by itself.
- If this session can push to omarjaradat2006-sudo/agent-hq: set `made: true` on each lineup item made and `status: "done"` (and `doneAt` now) on each used idea in data/youtube/state.json, then commit and push. Never change any other status. Otherwise list the idea ids so Omar can press "I did it" on the site.
- Then wait. When Omar says everything is uploaded/scheduled ("okay", "done"), clean up yourself with the delete permission you asked for at the start: empty `_system\Local Render\work`, `_system\parts` and `_system\Uploaded (delete later)`, plus any `.part`/temp files. Never delete anything still listed in a `queue.json`. Say how much space was freed. If you can't delete, tell him to run `python render.py clean`.

_Generated 2026-11-04 15:20 UTC_
