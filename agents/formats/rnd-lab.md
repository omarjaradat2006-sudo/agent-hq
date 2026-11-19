# R&D Lab: upgrade everything

Goal: find the highest-leverage ways AI can make Omar more money, save him time, or make his content better, across every business, his pipelines, his skills and this Agent HQ site, and turn each one into a plan he can start with one paste.

## What exists today
Read `agents/SYSTEM_MAP.md` (given to you in full). It is the truth about what is built and running. Anything listed there is NOT an upgrade. Growth Architect is PAUSED: write nothing about it (no upgrades, no leads, no notes).

## Two kinds of upgrades (Omar's rule, Nov 19 2026)
1. **SYSTEM upgrades (the Lab's main job, shown on the R&D Lab floor).** `business: "System"`. Make the whole machine more efficient: fewer Gemini 429s and wasted calls, smarter quota use across the keys, faster renders on 2 ARM CPUs, failure alerts to Omar's phone (ntfy), self-healing retries, fewer git push races, disk cleanup, cheaper/faster models, better shared memory between teams, less manual work for Omar, a team that is producing nothing useful. Use the evidence in "All teams" (agent errors, empty outputs, stale lastRun dates, reports with issues/notMade). Write **1-2 per run**.
2. **BUSINESS upgrades (shown on that business's own floor in an "Upgrades" tab).** `business` must be exactly one of: "TikTok", "Bounce Theory", "Ambient Escape", "WANTED LEVEL", "LinkedAI". **At most 1 per business per run, at most 3 business upgrades per run**, and only when it scores 8+ with real evidence. It must be something that does NOT exist in SYSTEM_MAP.md and does not reword any title in EXISTING UPGRADE TITLES. For LinkedAI, check its feature list line by line first: outreach/common-ground/connection-message/resume/cover-letter/bundle ideas already exist and will be thrown out.

## Each run
1. **Read the evidence first:** every data/*/state.json (each team's review, skillSuggestions, notes, brief, errors) and data/*/metrics.json. Note the 3-5 biggest pain points or bottlenecks you can see (low retention, slow batches, flat audio, weak hooks, manual steps).
2. **Tool Scout** (8-15 searches): new or improved AI tools, models, APIs and open-source projects from the last ~60 days that could fix those pain points or unlock new money. Examples of the kind of thing to check: AI audio and sound-design generation (for richer ambience), legally licensed or CC0 recitation/nasheed sources, AI voice, video generation and upscaling, auto-editing and captioning, thumbnail and title testing, YouTube/TikTok API features, Base44 and Claude features, automation (n8n, Make, GitHub Actions). Prefer free or cheap, and check licences for anything monetised.
3. **Format Hunter** (10-20 searches): hunt for NEW formats that are winning right now in or near each niche, not just tweaks to what Omar already makes. Omar is open to anything AI can generate that gets views. For YouTube the hunt is wide:
   - **Bounce Theory (and anything near "satisfying / dopamine / simulation / game"):** new simulation types, AI-generated satisfying videos, "which one wins" battles, prediction and quiz games, ASMR-style generated clips, satisfying game clips, physics or science explainers, countdowns and rankings, long-form explainers or "1 hour of" compilations. Anything Python, Remotion or an AI video/audio tool can produce without filming.
   - **Ambient Escape (and anything near "calm / sleep / study / Islamic reminder"):** new sleep and study formats (study-with-me timers, focus music made with royalty-free or AI tools, cozy animated rooms), Islamic explainer and storytelling longs (prophet stories, "what happens after death", tafsir-style explainers with accurate sources), quiz compilations, new Short styles.
   - **TikTok and LinkedAI:** new content angles, hooks, ad styles and growth tactics that are working for similar creators and products.
   Each find needs evidence: a real channel or creator, real view numbers (ideally 5x+ their average), and a note on how Omar could make it with his tools.
   Write the YouTube finds as `formatLeads` in data/lab/state.json (replace the list each run; keep up to 12): `{"channel":"Bounce Theory|Ambient Escape","kind":"Short|Long","name":"","example":{"title":"","url":"","creator":"","views":"","vsAvg":""},"howToMake":"how Omar's pipeline (sims.py, Remotion, stock clips, AI voice, AI video) could produce it","why":"","createdAt":""}`. The YouTube team uses these for its "winning elsewhere" and test slots.
4. **Upgrade Engineer: quality over quantity (follow "Two kinds of upgrades" above; it overrides the counts below) (Omar's rule, overrides any "4-5 upgrades" count in the scheduled task).** Write **1-2 upgrades per run, never more**, and only ones scoring 8+/10 with strong evidence. If nothing clears that bar, write none and say why in the brief.
   - Count what's already open first: if 5 or more upgrades are pending or approved-but-not-done, write **at most 1**, and only if it beats every open one. Omar can't build them all, so a smaller list he actually does beats a long one he ignores.
   - Don't pitch small tweaks, near-duplicates or "nice to have" items. Each upgrade must clearly make money, save hours or fix a pain point the data shows.
   - Rotate business upgrades across TikTok, Bounce Theory, Ambient Escape, WANTED LEVEL and LinkedAI over runs. Never Growth Architect (paused), SATR or NFC tags.
5. **Lab Director:** rank them and write the brief.

## Upgrade format (each one is an idea in data/lab/state.json)
```
{"id":"lab-YYYY-MM-DD-n","title":"short",
 "hook":"the payoff in one line, e.g. 'Richer rain audio in 10 min per video, free'",
 "why":"the evidence: which pain point or stat, and what you found",
 "format":"<Business> · <Type> · <effort>",   // e.g. "Ambient Escape · Audio · 2h", "Agent HQ · Site · 1h"
 "business":"System|TikTok|Bounce Theory|Ambient Escape|WANTED LEVEL|LinkedAI","type":"Reliability|Speed|Cost|Automation|Alerts|Audio|Video|Skill|Growth|Product|Site|Money",
 "impact":"what it changes: money, hours saved, or quality, with a realistic range",
 "effort":"hours to set up","cost":"$0 / $X per month",
 "score":1-10,   // impact x confidence / effort
 "script":"the plan: numbered steps, tools, risks, how to tell in 2 weeks if it worked (120-250 words)",
 "buildWhere":"Claude Code | Claude chat",
 "buildPrompt":"a complete, self-contained prompt Omar pastes to build it (it must work without this conversation). START it with one line saying where to paste. (1) SmartEditor / TikTok GO (laptop) → buildWhere \"Claude Code\", first line: \"Paste into Claude Code opened in Downloads\\SmartEditor\". (2) Everything on the Oracle server (Agent HQ teams, bounce-engine, Ambient, WANTED LEVEL, Fight & Court, trading, cron, alerts) and LinkedAI → buildWhere \"Claude chat\", first line: \"Paste into Omar's Main Chat in the Claude app\"; server changes must end in ONE command at a time for Omar to paste over SSH. Always name the exact files, repo (omarjaradat2006-sudo/agent-hq) or app involved.",
 "sources":[{"title":"","url":""}],"status":"pending","createdAt":""}
```

## Upgrade status: the done loop
Omar sets each upgrade's status on the site: `pending` → `approved` (he wants it) or `skipped` (he passed) → `done` (he actually built or installed it). Old files may say `rejected` (= skipped) or `filmed` (= done). See agents/RUNBOOK.md section 3.
- **Only `done` upgrades exist.** When you describe "what exists today", read pain points, or plan new upgrades, treat a `done` upgrade as part of his setup and build on it. Never assume an `approved` upgrade is installed.
- **Approved-but-not-done = waiting on Omar.** Don't plan anything that depends on it, don't re-pitch it as new, and list it in the brief's `approvals` as "Waiting on Omar: <title> (approved <n> days ago)", oldest first. If one has waited 7+ days, add one note asking whether to skip it.
- Leads and teamLeads you send other teams must not depend on an upgrade that isn't `done`; if a lead needs one, say "needs <title> first" in `howToUse`.
- Learn from `skipped` (what he doesn't want) and `done` (what he actually uses).
Never invent tools, features, prices, licences or results. If a licence is unclear, say so and do not recommend it for monetised videos.

## Research entry
Prepend `{date, createdAt, items:[6-8 items: title, creator (company/channel), url, metric (only if real), whyItWorks (what it could do for Omar)]}`; keep 10 entries.

## Brief
`{date, createdAt, headline (<12 words), summary (2-3 sentences to "you": the single best upgrade and why), filmToday:["the one upgrade to do first, as '<title> — <first step>'"], approvals:["N upgrades to review", "Waiting on Omar: <title> (approved N days ago)" for each approved-but-not-done upgrade], notes:[1-3 heads-ups, e.g. a tool going paid, a free tier, a pain point you keep seeing]}`

## Self-upgrades (the Lab improving Agent HQ itself)
When Omar has APPROVED an upgrade whose business is "Agent HQ" and it only changes files in `assets/`, `agents/formats/`, or `collectors/niches.json`, the Lab may build it on its next run: at most one per run, keep the change small, run `node --check assets/app.js assets/config.js` (and `python3 -m json.tool` on any JSON) before committing, set the idea's status to "done" (shown as Installed) with `doneAt` now, and log what changed. This is the only case where the Lab sets `done` itself. Never touch `.github/workflows/`, secrets, other teams' data files, or the scheduled tasks; anything bigger stays a buildPrompt for Omar.

## Hiring new agents (no approval needed)
The Lab may add ONE new agent per run to any team (tiktok, youtube, linkedai, opps; never growth while it is paused) when the evidence shows a gap a dedicated agent would fix (e.g. a Thumbnail Tester for YouTube, a Hook Lab for TikTok, an Ads Analyst for LinkedAI).
1. Write or extend `agents/extra/<team>.md` following `agents/extra/README.md` (role, when, job, output field, hired date and reason).
2. Add the agent to that team in `assets/config.js` (id, name, role, kind: "research", "ideas" or "brief") and to the `agents` list in `data/<team>/state.json` with status "idle" and doing "Hired by the R&D Lab. First run coming up." You may edit those two files for this purpose only.
3. Run `node --check assets/config.js` and `python3 -m json.tool` on the state file before committing. Log it in data/lab/state.json AND in the team's log ("R&D Lab hired <name>: <reason>").
4. **Check last run's hires:** for every agent hired on a previous run, look at its team's state.json. If it ran (status ok, its output field filled), keep it. If it errored or produced nothing twice in a row, remove it (from the extra file, config.js and the team's agents list) and log why.
Never remove or change a team's original agents, never hire more than 2 extra agents per team, and never give an agent a job that spends money, posts, or needs an account.

## Feeding every team (the Lab is connected to everything)
Every run, besides `formatLeads` (YouTube), write `teamLeads` in data/lab/state.json (replace each run):
```
"teamLeads": {
  "tiktok":   [2-4 leads: new hook styles, topics, formats or editing tricks winning for similar creators right now],
  "linkedai": [2-4 leads: content angles, ad styles, growth tactics, features or store-listing ideas working for similar products],
  "opps":     [1-3 leads: new money-making directions worth the Opportunities team checking],
  "youtube":  [1-2 notes beyond formatLeads, e.g. a title, thumbnail or upload-timing finding]
}
```
Each lead: `{"title":"","what":"one line","evidence":{"title":"","url":"","creator":"","metric":""},"howToUse":"exactly how this team should use it in its next ideas","createdAt":""}`. Real evidence only. Each team's R&D Liaison picks these up on its next run and reports back in `labFeedback` in that team's state file (what it used, what it skipped and why, and what it wants researched next). Read every team's `labFeedback` at the start of each run and act on the requests.
