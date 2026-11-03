# Omar's CURRENT TikTok editing system (READ before suggesting ANY editing, caption, font, subtitle, zoom, cut or video tool)

Last checked against the real code on his laptop: 2026-11-03 (smart_editor.py, 854 lines; tiktok.py, 291 lines).

**Rule:** captions, fonts, keyword highlighting, silence cuts, retake cuts, zooms, opening shake, flashes, AI captions + hashtags, and phone delivery are ALREADY DONE. Never suggest a captioner, subtitle tool, font pack or "add highlighted captions" idea. If a find duplicates something below, write "already covered by SmartEditor/TikTok GO" and drop it. Only suggest things listed under "Real gaps", or something clearly better than what is here (say exactly what it beats and how you'd test it).

Example of a mistake not to repeat: on 2026-11-01 GitHub Scout recommended SmartSub (local highlighted captions). His SmartEditor already does this with more styles, word-by-word highlighting and pop-in animation, so it was useless.

## The flow (one double-click: `Downloads\TIKTOK HQ\TikTok GO.bat` -> `_system\TikTok Tool\tiktok.py go`)
1. He films sit-down talking-to-camera videos on his iPhone (several short clips joined into one), bulk-filming many at once.
2. Videos get to the laptop through **OneDrive > TikTok Inbox** (iCloud is full for now; iCloudPhotos import is also coded). TikTok GO moves them into `TIKTOK HQ\1 New Videos`.
3. TikTok GO runs **SmartEditor** (`Downloads\SmartEditor\SmartEditor\smart_editor.py`) on every new video -> `TIKTOK HQ\2 Edited - Ready to Post`.
4. Claude writes a TikTok caption from the transcript, keeps 2 niche hashtags and adds the 3 fixed ones: `#fyppppppppppppppppppppppp #viral #fyp` (5 hashtags total, TikTok's max). Saved to `captions.txt`.
5. Uploads each video to his **TikTok drafts/inbox** (account o.hustle44) through the official TikTok Content Posting API. He does NOT want auto-posting: he adds sound and posts himself. Unreviewed app = about 5 unposted drafts at a time; the rest wait in "2 Edited" until the next run.
6. Pushes each caption to his phone with the free **ntfy** app (long-press to copy), and copies the video to OneDrive > TikTok Ready as a backup.
7. Moves finished files to `_system\Posted (delete later)`.

## What SmartEditor does to every video (Claude-planned, Sonnet via his own API key)
- **Transcription:** faster-whisper `small.en`, on CPU, word-level timestamps (`.words.json` saved next to each video, editable to fix wrong words, then re-run).
- **Edit plan:** Claude reads the timed words and returns a plan (`.plan.json`, editable): caption style, accent, keywords, hook end, zooms, flashes, B-roll, removals.
- **Cuts:** removes silences over 0.45s (keeps a natural breath), detects clip changes from the frames and cuts tight there (no reaching-for-the-phone moments), snaps cuts to his real voice, and removes stutters, false starts, retakes (keeps the last clean take) and off-camera talk ("wait", "let me redo that").
- **Captions (burned in, always on):**
  - Font: **Montserrat Black** ("punchy") or **Montserrat ExtraBold** ("clean"), white with black outline and shadow, centred about 74% down the frame.
  - "punchy" = UPPERCASE, 2-3 words at a time, the word being spoken lights up in the accent colour.
  - "clean" = sentence case, 3-5 words at a time, only keywords coloured (for calm, emotional or faith videos).
  - Accent per video: yellow (default), green (money/growth), red (warnings/hard truths).
  - Keywords: Claude picks about 1 per 2-3 chunks (numbers, contrast words, stakes, emotion), coloured and 12% bigger.
  - Every caption chunk pops in (80% -> 100% scale with fade); hook captions are 25% bigger.
- **Zooms:** wide / punch (1.15x) / tight (1.25x) sections on phrase starts, changed every 2-6 seconds, punch on hooks and punchlines, framed on his face.
- **Opening shake:** 0.4s shake + punch-in at the start.
- **Flashes:** 0-2 quick white flashes on the biggest reveal (never on mentions of Allah, the Prophet, the Quran, prayer or du'a).
- **No-API fallback:** `--no-ai` gives plain captions and rule-based zooms if API credit runs out.
- Other options: `--plan-only`, `--replan`, `--no-cuts`, `--keep-retakes`, `--zoom-scale`, `--whisper base.en|medium.en`.

## Real gaps (what would actually be an upgrade)
- **B-roll:** the feature is built but his `SmartEditor\broll` folder doesn't exist, so no B-roll is used. A way to auto-fill a tagged, licence-safe B-roll library (e.g. from Pexels/Pixabay, which Agent HQ already downloads for YouTube) would switch it on.
- **Sound effects:** none yet (whooshes on zooms, pops on keywords, hit on flashes). He wants them. Must be free/CC0 and licence-checked.
- **Music:** none on purpose; he adds a TikTok sound in the app. Don't add music.
- **Animations / emojis / text overlays** beyond the caption pop-in: not built.
- **Proofread step:** no pause to fix wrong words before rendering (he has to use `--plan-only` by hand).
- **Phone -> laptop hop:** still manual sharing to OneDrive.
- **Views stuck around 250:** editing is NOT the likely cause (captions and cuts are already pro-level). Hooks, topics, the first caption line / search phrase and posting times are more likely levers. Say so instead of proposing another editor.

## Constraints on any suggestion
- Windows laptop, no strong GPU. Free or very cheap. No new accounts if avoidable.
- Must plug into SmartEditor / TikTok GO (a change to smart_editor.py or tiktok.py), not replace them with a separate app he has to open.
- Licence must allow monetised use; flag AGPL and non-commercial.
- Never auto-post publicly. Never read or copy his API key or TikTok token files.
- Make the build request a ready copy-paste prompt naming the exact file to change.

## Teams that must read this
TikTok team (Strategist, Caption Coach, R&D Liaison), R&D Lab, GitHub Scout, and the LinkedAI / Growth Architect teams before proposing promo-video editing.
