# YouTube lineup: win-first

The lineup exists to repeat what already wins, not to experiment. Every slot must be backed by evidence. Per day: **Bounce Theory exactly 24 Shorts (S01-S24)** + its long videos; **Ambient Escape exactly 24 Shorts** + 2 long videos.

## Slot mix for the Shorts (per channel; for Bounce's 24 Shorts scale the counts up by 1.6x)
| Share | Type | What it is |
|---|---|---|
| 9-11 slots | **Proven (yours)** | A remix of one of Omar's own best videos from `metrics.json` → `topVideos` (top by views and retention over 90 days, `ageDays` >= 3). Keep the winner's recipe: same format, hook style, title pattern, length (within ±3 s) and pacing. Change ONE visible thing (colours, count, frame shape, melody, timer, matchup) so it is a fresh video, not a re-upload. |
| 3-5 slots | **Proven (elsewhere)** | A format that is winning for other channels in or near the niche right now: the R&D Lab's `formatLeads` in data/lab/state.json (read these first: they are new formats with evidence, and they don't have to be physics sims or ambience), a `trending` outlier at 5x+ its channel average, or a research finding with real numbers. Adapt it to Omar's pipeline. |
| 0-2 slots | **Test** | A new concept, preferably the strongest Lab `formatLead` that needs a new build. Only with a real reason. Never more than 2. |

The best remixes go in the first slots (S01-S05), because the first uploads of a day get the most reach.

Weight by results: a format with a 30K-view hit gets more slots than one that peaks at 1K. Use the review's `formatScores`. Formats the review marks as weak (low median views and low retention) get at most 1 slot, or none.

## Never repeat what's already up (Omar's rule)
- Your context lists every title ALREADY UPLOADED on each channel and the Bounce template+settings rendered in the last 14 days. **Never reuse an uploaded title**, not even with a new emoji or one word changed; write a new hook.
- Every Bounce slot is a fresh variation of its winner: different colours AND at least one of count, shape/frame, speed or size vs that template's recent settings, and a hook that names the new thing ("PURPLE vs LIME", "12 balls", "HEXAGON edition").
- If a slot would still repeat, the server changes its settings and title itself and makes it anyway; it never skips a slot.

## Channel separation (Omar's rule, never break it)
Each channel only gets its own kind of video, even if an off-niche video once did well there.
- **Ambient Escape:** only calm sleep/ambience longs, Islamic reminders, quizzes and animated explainers. **Never** a Bounce Engine video, physics simulation, ball/ring/marble/race/battle format or any 'bounce sim (off-niche)' slot. Ambient's old bounce hit ('Every bounce, the ball gets BIGGER') is NOT a remix source for Ambient; leave it out of Ambient's winners.
- **Bounce Theory:** only Bounce Engine simulations. Never Islamic content, stock footage or ambience.
- If a format belongs to the other channel, put it in that channel's lineup instead.

## Ambient Escape: 12 animated explainers + 12 proven (Omar's rule, from 2026-11-04)
Omar's current Ambient Shorts are flat, so **every Ambient Escape lineup has exactly 12 animated explainer Shorts + 12 Shorts from the mix above** (the 12 = the strongest proven remixes). This overrides the 9-11 / 3-5 / 0-2 split for Ambient Shorts only; Bounce Theory is unchanged. Keep it until Omar changes it; the Performance Reviewer compares the two groups (views, % watched) in every review and says which wins.

They are rendered by **explainer2** (`render/explainer2/` in this repo, approved by Omar 2026-11-08): flat illustrated full-frame scenes, faceless characters acting the situation out, Kokoro narration with a different male voice on every video, small sound effects only (no background, no music), no footage, no reciter audio. Inspired by @tanzil_quran (POV road-rage → hadith) and @soulofbaraqah ("8 Islamic ways to unblock your rizq"). Never copy their wording, scenes or topics word for word.

Two formats (use both every day, at least 3 of each):
- **`explainer_pov`** (15-25 s): "POV: <everyday situation a young Muslim knows>" → 2-3 tension beats → the hadith/ayah revealed word by word (Arabic + English gloss + an icon per word) → a share line ("Send this to a friend who …"). Situations: getting cut off, someone insults you online, parents asking for help when you're tired, a friend backbiting, missing Fajr, exam stress, losing a game, waiting in a long line.
- **`explainer_list`** (30-50 s): "N Islamic ways to <outcome>" / "N things the Prophet ﷺ did <when>" → one scene per point (counter 01/N, title with one gold keyword, one-line meaning, source) → ending line + share CTA. 4-8 points.

**Variety (Omar's rule):** never reuse a hadith, ayah, POV situation or list topic used in the last 14 days. Check `pastLineups` and the upload logs first. Spread the 12 across different life areas each day (anger, family, money/rizq, salah, friends, school/work, phone/social media, gratitude, sleep, character) and vary the scenes; when no existing scene fits, write `new scene: <what to draw>` in the note so the batch adds it to explainer2's scenes.py.

Put 3 explainers in S01-S05 (first uploads get the most reach) and spread the rest. Titles: "POV: <situation> 🤍 #shorts #islam #hadith" or "<N> Islamic ways to <outcome> 🤍 #shorts #islam" (under 70 chars).

**Every explainer slot's `note` must hold the full spec** so the batch can render it without guessing, in this exact shape:
- pov: `POV hook: "<situation>" | beats: "<line>" (red) ; "<line>" ; "<line>" | reveal: <Arabic words with English gloss, each "ar=en"> | icons: <one per word from no, flex, throw, calm, gauge, heart, hand, scale, star> | source: <collection + number> | end: "<line>" / "<line2>" | cta: "Send this to a friend who <...>"`
- list: `hook: "<title with *keyword*>" (scene) | 1) "<title *kw*>" — "<meaning>" — <source> — <scene>/<pose> ; 2) ... | end: "<line>" / "<line2>" | cta: "..."`
- Scenes available (explainer2): living_room (two people on a sofa), phone (group chat / typing / delete-and-send), reveal (night sky + masjid, for the hadith), street_walk (night street), market (stall, buying), neighbors (street, morning greeting or evening wave), park (path, removing harm), sunset (rooftop dhikr, masjid at sunset). Pick the one that shows the point, or write `new scene: <what to draw>`. Icons are no longer used (the `icons` field can be left out). Write beats and lines so they can be read aloud: the narration reads them.
- **Religious accuracy is non-negotiable:** Quran with surah:ayah, only sahih/hasan hadith with collection and number, meanings paraphrased faithfully, Arabic text exactly as in the source. If you are not sure of a reference, pick a different point. Never invent or merge hadith.
- `basis`: "Winning elsewhere: '<their title>' by @tanzil_quran / @soulofbaraqah (TikTok, Omar's pick)" or a real outlier the Analyst found. `footage`: omit (no clip needed).

## Bounce Theory: every slot is a template + settings (the server makes the batch, no Claude)
Bounce Theory is rendered automatically on the server at 7 AM from your lineup. The server can only use the formats in the **Bounce template menu** (in your context; full file: data/youtube/bounce_templates.json). It cannot write new code. So every Bounce Theory item MUST carry:
```
"settings": {"template": "<menu name>", "params": {"<knob>": <value>, ...}, "secs": [lo, hi]}
```
- `template`: a name from the menu, of the right kind (Short for S01-S24, Long for L1). Pick the template that matches the winner the slot remixes (same family: pendulum, brick, string, marble, shrink, chaos, merge, melody, weapon...).
- `params`: the visible twist, ONLY through that template's knobs and only with the listed colour names. Colour knobs take one colour name ("GOLD"); list knobs take a list (["RED", "CYAN"]). `l1`/`l2` are the on-screen title lines (uppercase, max 40 characters each, a question or challenge). Counts, sizes and speeds stay within about half to double the default. Never invent a knob.
- Change at least 2 things vs the winner (e.g. colours + count, or shape + colours), so no video is a default re-render. Colours/seeds you leave out are filled with fresh ones the server hasn't used on that template in 7 days.
- `secs` (optional): the length window for Shorts, e.g. [20, 26] to cut a format that loses viewers late. Default [13, 34].
- `note` stays: one plain sentence describing what these settings will show.
- **L1** (marble run): `{"template": "<a Long marble_run_* template>"}` plus `"titleOptions": [3 titles]` on the item. The server fits the course to about 10 minutes.
- **L2** ("Clips for Edits", no text): `{"clips": ["<template>", "<template>", "<template>"]}`: three Short templates from his top formats; the server renders 10 clips of each with new colours (about 5-6 min). Add `"minutes": N` (max 60) to loop it longer. A title must never promise more than the video is: no "10 Hours" titles; the server skips a long whose title claims over 60 min.
- A format that is NOT in the menu needs a build: don't put it in the lineup. Write it as a Producer idea (title starting "Needs build:", with the full spec) so Omar can build it in Claude Code; once built it appears in the menu by itself. Test slots must also use menu templates (a new combination of knobs counts as a test).
- Bad or missing settings never stop the batch: the server falls back to the closest template in the slot's family and reports it in data/youtube/bounce_report.json. Read yesterday's report and fix whatever fell back.

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
- Lab `formatLeads` that need a new build can't go in a Bounce Theory lineup until they're in the template menu: write them as a "Needs build:" Producer idea instead (see the template section).
- Your own video ideas: new ones are `approved` (up next); the batch marks them `done` when made, or Omar presses "I did it". `skipped` ideas never go in a lineup.

## Scheduling (Omar's rule)
Every video in a lineup gets uploaded scheduled, never left Private: the batch gives every `queue.json` item a `slot` in lineup order. **Bounce Theory** goes public one video every hour around the clock (24 a day), continuing from the previous batch. **Ambient Escape** is spread across the 5 PM to 8 AM window. So order the lineup the way it should go public: strongest Shorts first (S01-S05), longs in the evening.
