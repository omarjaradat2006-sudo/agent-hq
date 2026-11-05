# YouTube lineup: win-first

The lineup exists to repeat what already wins, not to experiment. Every slot must be backed by evidence. Per channel per day: exactly 15 Shorts + 2 long videos.

## Slot mix for the 15 Shorts (per channel)
| Share | Type | What it is |
|---|---|---|
| 9-11 slots | **Proven (yours)** | A remix of one of Omar's own best videos from `metrics.json` → `topVideos` (top by views and retention over 90 days, `ageDays` >= 3). Keep the winner's recipe: same format, hook style, title pattern, length (within ±3 s) and pacing. Change ONE visible thing (colours, count, frame shape, melody, timer, matchup) so it is a fresh video, not a re-upload. |
| 3-5 slots | **Proven (elsewhere)** | A format that is winning for other channels in or near the niche right now: the R&D Lab's `formatLeads` in data/lab/state.json (read these first: they are new formats with evidence, and they don't have to be physics sims or ambience), a `trending` outlier at 5x+ its channel average, or a research finding with real numbers. Adapt it to Omar's pipeline. |
| 0-2 slots | **Test** | A new concept, preferably the strongest Lab `formatLead` that needs a new build. Only with a real reason. Never more than 2. |

The best remixes go in the first slots (S01-S05), because the first uploads of a day get the most reach.

Weight by results: a format with a 30K-view hit gets more slots than one that peaks at 1K. Use the review's `formatScores`. Formats the review marks as weak (low median views and low retention) get at most 1 slot, or none.

## Channel separation (Omar's rule, never break it)
Each channel only gets its own kind of video, even if an off-niche video once did well there.
- **Ambient Escape:** only calm sleep/ambience longs, Islamic reminders, quizzes and animated explainers. **Never** a Bounce Engine video, physics simulation, ball/ring/marble/race/battle format or any 'bounce sim (off-niche)' slot. Ambient's old bounce hit ('Every bounce, the ball gets BIGGER') is NOT a remix source for Ambient; leave it out of Ambient's winners.
- **Bounce Theory:** only Bounce Engine simulations. Never Islamic content, stock footage or ambience.
- If a format belongs to the other channel, put it in that channel's lineup instead.

## Ambient Escape experiment: 8 animated explainers + 7 proven (Omar's rule, from 2026-11-04)
Omar's current Ambient Shorts are flat, so **every Ambient Escape lineup has exactly 8 animated explainer Shorts + 7 Shorts from the mix above** (the 7 = the strongest proven remixes). This overrides the 9-11 / 3-5 / 0-2 split for Ambient Shorts only; Bounce Theory is unchanged. Keep it until Omar changes it; the Performance Reviewer compares the two groups (views, % watched) in every review and says which wins.

They are rendered by `explainer.py` on his laptop (`_system\Local Render\lib\explainer.py`, all drawn in code: glowing figures, dark scenes, gold keyword, synthesized sound effects, no footage, no reciter audio). Inspired by @tanzil_quran (POV road-rage → hadith) and @soulofbaraqah ("8 Islamic ways to unblock your rizq"). Never copy their wording, scenes or topics word for word.

Two formats (use both every day, at least 3 of each):
- **`explainer_pov`** (15-25 s): "POV: <everyday situation a young Muslim knows>" → 2-3 tension beats → the hadith/ayah revealed word by word (Arabic + English gloss + an icon per word) → a share line ("Send this to a friend who …"). Situations: getting cut off, someone insults you online, parents asking for help when you're tired, a friend backbiting, missing Fajr, exam stress, losing a game, waiting in a long line.
- **`explainer_list`** (30-50 s): "N Islamic ways to <outcome>" / "N things the Prophet ﷺ did <when>" → one scene per point (counter 01/N, title with one gold keyword, one-line meaning, source) → ending line + share CTA. 4-8 points.

**Variety (Omar's rule):** never reuse a hadith, ayah, POV situation or list topic used in the last 14 days. Check `pastLineups` and the upload logs first. Spread the 8 across different life areas each day (anger, family, money/rizq, salah, friends, school/work, phone/social media, gratitude, sleep, character) and vary the scenes; when no existing scene fits, write `new scene: <what to draw>` in the note so the batch adds it to explainer.py.

Put 3 explainers in S01-S05 (first uploads get the most reach) and spread the rest. Titles: "POV: <situation> 🤍 #shorts #islam #hadith" or "<N> Islamic ways to <outcome> 🤍 #shorts #islam" (under 70 chars).

**Every explainer slot's `note` must hold the full spec** so the batch can render it without guessing, in this exact shape:
- pov: `POV hook: "<situation>" | beats: "<line>" (red) ; "<line>" ; "<line>" | reveal: <Arabic words with English gloss, each "ar=en"> | icons: <one per word from no, flex, throw, calm, gauge, heart, hand, scale, star> | source: <collection + number> | end: "<line>" / "<line2>" | cta: "Send this to a friend who <...>"`
- list: `hook: "<title with *keyword*>" (scene) | 1) "<title *kw*>" — "<meaning>" — <source> — <scene>/<pose> ; 2) ... | end: "<line>" / "<line2>" | cta: "..."`
- Scenes available: dark, window_dawn, lamp_sofa, market, houses, field_rain, table_lamp, spotlight, sunset_birds, pipe, pipe_flow, road_pov, masjid_night, desk_night, door_light. Poses: stand, ruku, sujud, sit, give, dua, walk, none. Pick the scene that shows the point.
- **Religious accuracy is non-negotiable:** Quran with surah:ayah, only sahih/hasan hadith with collection and number, meanings paraphrased faithfully, Arabic text exactly as in the source. If you are not sure of a reference, pick a different point. Never invent or merge hadith.
- `basis`: "Winning elsewhere: '<their title>' by @tanzil_quran / @soulofbaraqah (TikTok, Omar's pick)" or a real outlier the Analyst found. `footage`: omit (no clip needed).

## Long videos (L1, L2)
Long videos have no big hits yet, so base them on what wins elsewhere plus Omar's strongest Short formats:
- **Bounce Theory:** L1 = a compilation or tournament built ONLY from his top Short formats (e.g. the pendulum wave and string art that got 31K and 9K), with text. L2 = "Satisfying Clips for Edits Vol. N (No Text)" from the same top formats.
- Either long slot may instead use a winning long format from the Lab's `formatLeads` (e.g. an explainer, a ranking, a story video) when it has real evidence.
- **Ambient Escape:** pick the scene + sound mix and title formula from sleep and ambient videos that are outliers right now (from `trending` and the research), using today's downloaded clips. Never reciter audio.

## Every lineup item gets a `basis`
`basis` says why this slot exists, with the evidence:
- `"Your hit: '<title>' · 31,726 views · 94% watched"`
- `"Winning elsewhere: '<title>' by <channel> · 12x their average"`
- `"Test: <one-line reason>"`

The `note` is the visible twist on that winner ("same 30-pendulum wave, now rainbow-to-gold gradient and a glass-chime melody").

## Language: English only
Every title, on-screen line, description, tag and AI voice-over on BOTH channels is in English. Never translate a winner into Spanish or any other language, even if a foreign-language video did well (Islamic Shorts may show Arabic ayat with the English meaning). Swap any non-English title for an English one before saving.

## Titles
Reuse the title pattern of the winner the slot is based on (same hook structure and emoji style), changing the specifics. Never copy a title word for word.

## New ideas (Producer)
At most 1 new concept per channel per day, and only when it is backed by evidence. Mostly write remix specs: "take <winner>, keep X, change Y".

## When a "winning elsewhere" or test slot wins for Omar
After it has real numbers (ageDays >= 3) and beats the channel median, it becomes one of Omar's hits and moves into the remix slots. That is how new formats graduate.

## R&D upgrades: only use what is done
The R&D Lab's upgrades (ideas in data/lab/state.json for Bounce Theory, Ambient Escape or YouTube: new sims.py formats, audio upgrades, pipeline changes) have a status Omar sets: pending → approved / skipped → done. See agents/RUNBOOK.md section 3.
- Plan slots that rely on an upgrade (a new format function, new audio, a new pipeline step) **only when that upgrade's status is `done`**. `approved` means Omar hasn't built it yet.
- Approved-but-not-done upgrades are "waiting on Omar": no slot may depend on them. List them in the brief's `approvals` as "Waiting on Omar: <title>".
- Lab `formatLeads` that need a new build count as a Test slot (0-2), built in the batch from a Producer idea's spec, never from an upgrade that isn't done.
- Your own video ideas: new ones are `approved` (up next); the batch marks them `done` when made, or Omar presses "I did it". `skipped` ideas never go in a lineup.

## Scheduling (Omar's rule)
Every video in a lineup gets uploaded scheduled, never left Private: the batch gives every `queue.json` item a `slot` in lineup order, and Omar's upload tool spreads them across the 5 PM to 8 AM window, one at a time, never overlapping the previous batch. So order the lineup the way it should go public: strongest Shorts first (S01-S05), longs in the evening.
