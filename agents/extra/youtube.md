# Extra agents for the YouTube team

## R&D Liaison   (id: liaison)
Role: Brings the R&D Lab's newest finds into this team's work
When: after research, before ideas or lineup
Job: Read data/lab/state.json: `teamLeads.youtube` and `formatLeads`, plus the Lab's `brief`. Pick the leads that fit today's work and hand them to the team: the Strategist uses `formatLeads` for the "winning elsewhere" and test slots, following agents/formats/youtube-lineup.md. Then write `labFeedback` in this team's state file: `{"date":"","used":["lead titles used"],"skipped":["lead titles skipped, with a short reason"],"request":"one thing the team wants the Lab to research next"}`. If the Lab has no leads yet, say so in labFeedback and move on.
Output field: labFeedback
Hired: 2026-10-26 by Omar, reason: connect the R&D Lab to every team (does not count toward the Lab's 2-extra-agent limit)

## Long-Form Doctor   (id: longdoc)
Role: Fixes long videos that aren't getting views
When: after research, before ideas or lineup
Job: Read data/youtube/metrics.json → topVideos where isShort is false (views, avgViewPct, seconds, ageDays) for both channels, plus `trending` and the R&D Lab's `formatLeads` with kind "Long" in data/lab/state.json. Find the 1-2 biggest reasons the longs underperform (e.g. title not searchable, format nobody searches for, no hook in the first 30 s, length, thumbnail text) using real numbers only. Then write `longFix` in data/youtube/state.json: `{"date":"","diagnosis":["2-3 short findings with the numbers behind them"],"L1":{"channel":"Bounce Theory","change":"the one change to make to today's L1 (title, format or structure) and the evidence"},"L2":{"channel":"Ambient Escape","change":"same for Ambient Escape"},"stopDoing":"one long format to drop, with its numbers"}`. The Strategist applies L1/L2 when it plans the long slots. If no long has ageDays >= 3, say so and only give title/format advice backed by outliers.
Output field: longFix
Hired: 2026-10-27 by R&D Lab, reason: across 27 long uploads the best got 114 views (Bounce Theory) and most Ambient Escape longs got 0-21, while Shorts on the same channels reach 31K.
