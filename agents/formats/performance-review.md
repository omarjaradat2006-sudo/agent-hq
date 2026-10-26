# Performance Reviewer (TikTok + YouTube)

Goal: work out WHY some of Omar's videos beat his average and others flopped, then feed that into today's ideas and suggest concrete changes to his skills.

## Inputs
- `data/<team>/metrics.json` → `topVideos` (his own recent uploads).
  - TikTok: views, likes, comments, shares, duration, description (= caption), createTime, url.
  - YouTube: per channel; views, likes, comments, avgViewPct (% of video watched), avgViewSec, subsGained, shares, duration, isShort, published, url.
- `data/<team>/state.json` → ideas with status "filmed" (TikTok: the real scenes/hook he filmed) and the last lineups (YouTube: format + note per slot).
- You cannot watch the videos. Say so where it matters: your read of the hook comes from the caption/title plus the matched script.

## Method
1. Only judge videos older than 48 hours. Use the last ~20 (TikTok) or last ~30 per channel (YouTube; Shorts and longs separately).
2. Baseline = median views of that set. For YouTube Shorts also use avgViewPct (retention is the main Shorts signal; >80% is strong, <50% weak). For longs use avgViewSec and subsGained.
3. Winners = top 3 by views ÷ median (YouTube: per channel). Losers = bottom 3.
4. Match each to the plan: TikTok → a filmed idea whose title/caption/hook matches; YouTube → the lineup slot or idea with the same title, giving its format name. If matched, judge the real hook line / format.
5. For each winner/loser write `why`: hook family, topic pillar, length, opening line, format, title style, posting time. One or two sentences, honest, no invented causes. If the sample is too small to tell, say so.
6. Patterns: 3-5 things the winners share that the losers don't. Score formats/hook families if there are enough data points: `formatScores: [{name, videos, medianViews, vsAvg}]`.

## Output: `review` in data/<team>/state.json (replace the old one)
```
"review": {
  "date": "YYYY-MM-DD", "createdAt": ISO,
  "headline": "< 12 words",
  "summary": "2-3 sentences to 'you'",
  "winners": [{"title","url","channel" (YouTube),"views","avgViewPct" (YouTube),"vsAvg":"3.1x your median","why"}],
  "losers":  [same shape],
  "patterns": ["..."],
  "formatScores": [...],
  "doMore": ["..."], "stopDoing": ["..."],
  "skillSuggestions": ["concrete edit to a named skill, e.g. 'content-scripts: add the Vulnerable admission hook family to the default 3 — 2 of your top 3 used it' or 'bounce-theory-videos: drop colour escape from daily rotation (0.4x median, 3 tries)' or 'NEW SKILL idea: ...'"]
}
```
Also keep `reviewHistory`: prepend {date, headline, patterns} and keep 8.

## Use it
The Strategist/Producer must use doMore/stopDoing when picking today's ideas and lineup, and each idea's `why` should mention the review when relevant.

Skill suggestions are suggestions only. Never edit skills. Omar applies them by telling Claude "apply the reviewer's skill suggestions".
