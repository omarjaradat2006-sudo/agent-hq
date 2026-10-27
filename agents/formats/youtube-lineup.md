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

## Titles
Reuse the title pattern of the winner the slot is based on (same hook structure and emoji style), changing the specifics. Never copy a title word for word.

## New ideas (Producer)
At most 1 new concept per channel per day, and only when it is backed by evidence. Mostly write remix specs: "take <winner>, keep X, change Y".

## When a "winning elsewhere" or test slot wins for Omar
After it has real numbers (ageDays >= 3) and beats the channel median, it becomes one of Omar's hits and moves into the remix slots. That is how new formats graduate.
