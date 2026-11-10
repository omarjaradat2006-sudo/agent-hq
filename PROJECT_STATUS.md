# PROJECT_STATUS.md

Last updated: 2026-11-09 evening (Step 5: trading bot ready to install on the server; Step 6: Fight & Court Intelligence built and scheduled. Both wait on Omar's server commands)

Rules in force: no Claude in daily operations (Gemini only) · no keys in chat or git · no purchases or paid APIs without Omar's OK · never delete a video before its upload is verified · **no live trading, ever** (paper URL hard-coded, live `AK` keys refused, service won't start otherwise) · no automatic bets, no sportsbook logins, **no Bet365 anywhere** (odds, comparisons, calculations) · no budget, staking or deposit advice for Fight & Court (Omar decides his own money) · one step at a time.

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
| Trading bot (`trading_bot/`) | READY FOR SERVER, NOT STARTED | Moves to openclaw as systemd service `agenthq-trading` (Restart=always, starts at boot) in its own clone `~/agent-hq-trading`. PAPER only. Alpaca paper keys typed hidden into `~/.trading-bot.env` (600) by `set_keys.sh`; Gemini key reused from `~/.agent-hq.env`. Risk Officer is plain code (`risk.py` + `config.py`), runs before and after the AI and can veto any trade; the AI can only say no. Every risk trigger + error logged to `local/events.jsonl`. Trading tab updates 5x a day + after trades. 7-day report timer daily 4:45 PM ET. 26/26 tests pass. **Fixed a bug that made every live Gemini triage call fail** (model name was a string, not a list) and made triage Flash-Lite only so it can't eat the teams' Flash quota. **Waits on Omar: install, keys, check, start.** |
| Perplexity research | SKIPPED (Omar agreed) | No free API tier; the MCP needs the same paid key. Gemini grounding does it for free. |
| Fight & Court Intelligence (UFC + NBA) | BUILT + TESTED OFFLINE, WAITS ON ODDS KEY | Gemini team in `agents/fight/` on the Oracle server (`scripts/server/run_fight.sh`, cron in `crontab.txt`). Research and recommendations only: no bet placing, no sportsbook logins, no credentials. Best odds only from Omar's books (FanDuel, DraftKings, BetMGM, BetRivers); the other Ontario books are read only for the fair price (9 on: BetMGM, FanDuel, DraftKings, Caesars, BetRivers, Betway, 888sport, LeoVegas, Pinnacle); Bet365 never requested, dropped if it appears, scrubbed from text. Singles, parlays (2-3 legs, different games, one book) and an underdog review, each with reasoning, implied %, no-vig fair %, our %, edge and EV per $100. Value is decided in code (blended prob +2.5 pts over fair and +2% EV), else "no bet"; "lock"/"guaranteed" wording is scrubbed. Every pick graded automatically (Odds API scores, then sourced Gemini search for UFC). Agent HQ room "Fight & Court" with tabs: Today's picks, Underdogs, Record (win rate, profit per $100, by bet type and sport, closing-price check), Research, Odds & books. 5/5 offline tests pass. **Waits on Omar: free Odds API key → `setup_fight.sh`.** |
| Video-editing repo shortlist | NOT STARTED | |
| OpenClaw | LATER | Waits for the server. Least-privilege access only. |

## 2. Costs found (nothing bought)

- **Perplexity API:** no free tier. Sonar is about $1 per million tokens plus a per-request fee. The old Sonar API is being retired (support ended Sep 27, 2026) in favour of the Agent API. Gemini with Google Search grounding already does this job for free. **Recommendation: skip for now.**
- **Oracle Pay As You Go upgrade:** $0 if we stay inside the Always Free limits, and it raises the chance of getting a server. Needs a card, and a $1 budget alert (an alert, not a hard cap). **Needs Omar's approval.**
- **Hetzner fallback:** CX23 (2 vCPU, 4 GB) is about €5.49–5.99 a month plus €0.50 for IPv4. US plans cost about 20% more, and the cheap plans have often been unavailable to order. **Needs approval. Only if Oracle fails.**
- **Odds data (checked Nov 9):** The Odds API free Starter plan = 500 credits a month, no card, **$0**. Asking for 9-10 named books costs the same as one region, so: NBA picks 3 credits/day, NBA closing check 3/day, scores 2/day, UFC ~4/week → about **270 credits a month**, under the cap. The free `/events` call is used first so no credits are spent on days with no games. Code stops spending when 40 credits are left (grading keeps working) and skips the optional closing check under 120. Paid plans (about US$30/month and up) are **not needed**. Bet365 is excluded in code.
- **Gemini for Fight & Court:** free tier, ~2 calls per card (research with Google Search + estimates) plus a few result lookups; no Claude.

## 3. Order of work

1. ✅ Audit + this file
2. ✅ Verify the 9 Gemini teams: Omar triggers one run each; fix failures; then check that they actually run on schedule.
3. ✅ Cloud: Oracle Pay As You Go decision → server → move the schedule to the server (more reliable than GitHub cron).
4. 🔶 Bounce Theory template engine + daily runner: built and tested; goes live after Omar's 3 server steps and one supervised run (`run_bounce.sh noupload`).
5. 🔶 Trading bot on the server: 1-week paper test (Omar chose 7 days, not 30/60/90) → 7-day report (`data/trading/report_7d.md`, Trading tab "7-day test") + backtest of the last 6-12 months (`tb backtest 365`, resumable on the free Gemini tier) → Omar decides. Real money is NOT part of this step; any change to live trading needs Omar's explicit decision and new code.
6. 🔶 Fight & Court Intelligence (UFC + NBA): built, tested offline, scheduled. No budget cap (Omar decides his own money). Goes live after Omar adds the free Odds API key (`setup_fight.sh`). Review the record after ~100 settled picks; watch "beat the closing price" before that.
7. Video-editing repo shortlist.
8. OpenClaw plan (after the server exists).
9. End-of-day report.

## 4. Log
- 2026-11-09: Audit done. Found that the Gemini teams have never run. Oracle catcher at try 552.
- 2026-11-09: All 9 Gemini teams pass. Oracle server caught (try 572), set up, runs teams via cron. Claude scheduled tasks stay paused.
- 2026-11-09: Bounce Engine code copied from the laptop to private repo bounce-engine (64 files, 3 MB, secret scan clean). Template engine built + tested in the cloud (render on 2 cores: ~1.3 min per Short). YouTube team now runs 6:13 AM so the 7:05 batch has a lineup. Laptop doc says Bounce is made on the server (copy it to the laptop only after the server's first good run).
- 2026-11-09 (evening): Trading bot prepared for the server. New: `trading_bot/server/` install.sh, set_keys.sh (hidden `read -s`), `tb` helper, systemd service + 7-day report timer, `paper_guard.py`; `weekly.py` (7-day report: trades, win rate, P&L, max drawdown, every risk-rule trigger, every error, restarts); backtest rebuilt for 6-12 months (monthly news cache, per-day Gemini cache, 150-call budget per run, no look-ahead in the equity maths, -10% kill switch simulated, month-by-month + risk-rule counts). Site: new "7-day test" tab, Backtest tab shows PARTIAL progress and months. Fixed: Gemini triage model bug (all live triage calls would have failed), stuck-rebase guard when saving to GitHub.
- 2026-11-09: Step 6 built. Fight & Court Intelligence (UFC + NBA) as a Gemini team on the Oracle server: Ontario books only, Bet365 excluded everywhere, singles/parlays/underdog review with implied %, value check in code, "no bet" when nothing has value, auto-graded record (win rate, profit per $100, by bet type) on a new Agent HQ room. Old "CAD $25 a week cap" removed at Omar's request. Schedule (Toronto): NBA picks 1:27 PM daily, NBA closing check 6:37 PM, UFC picks Fri 2:33 PM (after weigh-ins), UFC closing check Sat 5:43 PM, grading 9:47 AM daily, licence check Sun 12:53 PM. Caveat: prices come from each brand's US/UK feed; the Ontario app's price can differ slightly, so the site says to confirm it there.
- NEXT (step 6): Omar gets a free key at the-odds-api.com, then on the server: `bash ~/agent-hq/scripts/server/setup_fight.sh` (asks for the key, installs the schedule, tests the key for free).
- NEXT: Omar runs the trading server steps (install → set_keys → tb check → tb start → tb backtest 365). Day 7 ≈ one week after `tb start` → read the FINAL 7-day report + backtest together before any real-money decision. Bounce steps (deploy key, tokens, setup) still open in parallel.
