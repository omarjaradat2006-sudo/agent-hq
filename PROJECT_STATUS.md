# PROJECT_STATUS.md

Last updated: 2026-11-09 (Step 4: Bounce Theory template engine built; server setup waiting on Omar)

Rules in force: no Claude in daily operations (Gemini only) · no keys in chat or git · no purchases or paid APIs without Omar's OK · never delete a video before its upload is verified · no live trading · no automatic bets, no sportsbook logins, **no Bet365 anywhere** · one step at a time.

## 1. What exists today

| Area | Status | Notes |
|---|---|---|
| Agent HQ site (GitHub Pages) | WORKS | Reads `data/<team>/state.json`. Button statuses are never overwritten. |
| Data collectors (Actions) | WORKS, UNRELIABLE TIMING | Hourly cron, but GitHub ran it only ~3 times on Nov 9. |
| 9 Gemini agent teams (TikTok, YouTube, LinkedAI, Growth, Upgrades, Opps, Lab, Repos, Chief) | WORKS | All 9 tested Nov 9. Fall back across free Flash models on 429/503. Daily schedule runs on the Oracle server (`scripts/server/crontab.txt`); GitHub workflows are now manual backup only. |
| `GEMINI_API_KEY` secret | DONE | Added by Omar. |
| Claude scheduled tasks | PAUSED | Paused, not deleted. Retire once the Gemini teams are proven. |
| YouTube upload (`upload.py` + duplicate log) | WORKS | 17 uploads per channel per day, Oct 28–Nov 5, with no quota errors. |
| Rendering (`render.py`, explainers v2) | BOUNCE: SERVER READY · AMBIENT: LAPTOP | Engine, renderer and upload tool now live in the private repo `bounce-engine` (no keys). Ambient Escape still uses Claude Code on the laptop. |
| Bounce Theory template engine | BUILT + TESTED, NOT LIVE YET | `bounce-engine/templates/`: 134 formats as templates (133 pass the smoke test), YouTube team writes `settings` per slot from `data/youtube/bounce_templates.json`, server runner `scripts/server/run_bounce.sh` (cron 7:05) plans, renders, uploads, marks Agent HQ, writes `data/youtube/bounce_report.json`. Tested: 3 real Shorts rendered + checked, compilation, marking. **Waits on Omar: deploy key, YouTube token copy, `setup_bounce.sh`.** |
| Cloud server (Oracle Always Free, Toronto) | WORKS | "openclaw", 2 OCPU/12 GB/200 GB, Ubuntu 24.04, 40.233.127.117. Pay As You Go + $1 budget alert. Security updates + fail2ban on. Deploy key (agent-hq only). Gemini key in ~/.agent-hq.env (600). Logs in ~/logs. SSH key on laptop: Downloads\\oracle.key.key |
| Trading bot (`trading_bot/`) | BUILT, NOT STARTED | Paper mode, 19/19 tests pass, risk limits are correct. Not running on the laptop yet. |
| Perplexity research | SKIPPED (Omar agreed) | No free API tier; the MCP needs the same paid key. Gemini grounding does it for free. |
| Fight & Court Intelligence (UFC + NBA) | NOT STARTED | Research and recommendations only. |
| Video-editing repo shortlist | NOT STARTED | |
| OpenClaw | LATER | Waits for the server. Least-privilege access only. |

## 2. Costs found (nothing bought)

- **Perplexity API:** no free tier. Sonar is about $1 per million tokens plus a per-request fee. The old Sonar API is being retired (support ended Sep 27, 2026) in favour of the Agent API. Gemini with Google Search grounding already does this job for free. **Recommendation: skip for now.**
- **Oracle Pay As You Go upgrade:** $0 if we stay inside the Always Free limits, and it raises the chance of getting a server. Needs a card, and a $1 budget alert (an alert, not a hard cap). **Needs Omar's approval.**
- **Hetzner fallback:** CX23 (2 vCPU, 4 GB) is about €5.49–5.99 a month plus €0.50 for IPv4. US plans cost about 20% more, and the cheap plans have often been unavailable to order. **Needs approval. Only if Oracle fails.**
- **Odds data:** The Odds API has a free tier of 500 credits a month and covers MMA and NBA. Bet365 must be filtered out in code.

## 3. Order of work

1. ✅ Audit + this file
2. ✅ Verify the 9 Gemini teams: Omar triggers one run each; fix failures; then check that they actually run on schedule.
3. ✅ Cloud: Oracle Pay As You Go decision → server → move the schedule to the server (more reliable than GitHub cron).
4. 🔶 Bounce Theory template engine + daily runner: built and tested; goes live after Omar's 3 server steps and one supervised run (`run_bounce.sh noupload`).
5. Trading bot: start paper trading on the laptop or server, then review at 30, 60 and 90 days.
6. Fight & Court Intelligence: odds plus Gemini research; CAD $25 a week cap; "no bet" is a valid answer; track results.
7. Video-editing repo shortlist.
8. OpenClaw plan (after the server exists).
9. End-of-day report.

## 4. Log
- 2026-11-09: Audit done. Found that the Gemini teams have never run. Oracle catcher at try 552.
- 2026-11-09: All 9 Gemini teams pass. Oracle server caught (try 572), set up, runs teams via cron. Claude scheduled tasks stay paused.
- 2026-11-09: Bounce Engine code copied from the laptop to private repo bounce-engine (64 files, 3 MB, secret scan clean). Template engine built + tested in the cloud (render on 2 cores: ~1.3 min per Short). YouTube team now runs 6:13 AM so the 7:05 batch has a lineup. Laptop doc says Bounce is made on the server (copy it to the laptop only after the server's first good run).
- NEXT: Omar's 3 server steps (deploy key, tokens, setup) → supervised `run_bounce.sh noupload` → first full run → retire Bounce from the laptop. Then step 5 (trading bot).
