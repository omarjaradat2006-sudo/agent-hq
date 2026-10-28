# Extra agents for the TikTok team

## R&D Liaison   (id: liaison)
Role: Brings the R&D Lab's newest finds into this team's work
When: after research, before ideas or lineup
Job: Read data/lab/state.json: `teamLeads.tiktok`, plus the Lab's `brief`. Pick the leads that fit today's work and hand them to the team: at least one of today's ideas must use a Lab lead when a relevant one exists, and that idea's `why` must say which lead. Then write `labFeedback` in this team's state file: `{"date":"","used":["lead titles used"],"skipped":["lead titles skipped, with a short reason"],"request":"one thing the team wants the Lab to research next"}`. If the Lab has no leads yet, say so in labFeedback and move on.
Output field: labFeedback
Hired: 2026-10-26 by Omar, reason: connect the R&D Lab to every team (does not count toward the Lab's 2-extra-agent limit)

## Caption Coach   (id: captions)
Role: Writes search-friendly captions and on-screen keywords for each script
When: after ideas
Job: For each of today's scripts in data/tiktok/state.json → ideas (status pending, created today), write a caption pack: a first caption line that is a natural search phrase for the topic (e.g. "stoic advice for young muslim men"), one specific question for the second line, 2-4 specific hashtags (never #fyp, #viral or "Follow for more"), and the on-screen text to show in the first 3 seconds (same phrase). Check data/tiktok/metrics.json and the review for which caption styles the last posts used. Write `captionPacks` in data/tiktok/state.json: `{"date":"","packs":[{"ideaId":"","firstLine":"","question":"","hashtags":[""],"onScreen":""}],"note":"one line on what the last 10 captions did, from real numbers"}`. Base the rules on Metricool's 2026 TikTok SEO guide (https://metricool.com/tiktok-seo/); no invented stats.
Output field: captionPacks
Hired: 2026-10-28 by R&D Lab, reason: TikTok views fell from ~700 to ~250 since Oct 21 and 15 of the last 20 captions end in "Follow for more"; captions and on-screen keywords are what TikTok uses to file a video.
