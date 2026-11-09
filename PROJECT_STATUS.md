# PROJECT_STATUS.md

Last updated: 2026-11-09 (audit, Step 1 of the master directive)

Rules in force: no Claude in daily operations (Gemini only) · no keys in chat or git · no purchases or paid APIs without Omar's OK · never delete a video before its upload is verified · no live trading · no automatic bets, no sportsbook logins, **no Bet365 anywhere** · one step at a time.

## 1. What exists today

| Area | Status | Notes |
|---|---|---|
| Agent HQ site (GitHub Pages) | WORKS | Reads `data/<team>/state.json`. Button statuses are never overwritten. |
| Data collectors (Actions) | WORKS, UNRELIABLE TIMING | Hourly cron, but GitHub ran it only ~3 times on Nov 9. |
| 9 Gemini agent teams (TikTok, YouTube, LinkedAI, Growth, Upgrades, Opps, Lab, Repos, Chief) | BUILT, NEVER RUN | Workflows registered and active, but zero runs so far. Needs a manual test run. |
| `GEMINI_API_KEY` secret | DONE | Added by Omar. |
| Claude scheduled tasks | PAUSED | Paused, not deleted. Retire once the Gemini teams are proven. |
| YouTube upload (`upload.py` + duplicate log) | WORKS | 17 uploads per channel per day, Oct 28–Nov 5, with no quota errors. |
| Rendering (`render.py`, explainers v2) | WORKS ON LAPTOP | Daily batch still depends on Claude Code writing `today*.py`. **This is the main Claude dependency left.** |
| Bounce Theory template engine | NOT STARTED | Settings-based engine to replace the daily Claude scripting. |
| Cloud server (Oracle Always Free, Toronto) | BLOCKED: OUT OF CAPACITY | Catcher reached try 552 by Nov 9 15:43. |
| Trading bot (`trading_bot/`) | BUILT, NOT STARTED | Paper mode, 19/19 tests pass, risk limits are correct. Not running on the laptop yet. |
| Perplexity research | NOT STARTED | No free API tier (see costs below). |
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
2. ⏳ Verify the 9 Gemini teams: Omar triggers one run each; fix failures; then check that they actually run on schedule.
3. Cloud: Oracle Pay As You Go decision → server → move the schedule to the server (more reliable than GitHub cron).
4. Bounce Theory template engine + daily runner (removes the last daily Claude dependency).
5. Trading bot: start paper trading on the laptop or server, then review at 30, 60 and 90 days.
6. Fight & Court Intelligence: odds plus Gemini research; CAD $25 a week cap; "no bet" is a valid answer; track results.
7. Video-editing repo shortlist.
8. OpenClaw plan (after the server exists).
9. End-of-day report.

## 4. Log
- 2026-11-09: Audit done. Found that the Gemini teams have never run. Oracle catcher at try 552.
