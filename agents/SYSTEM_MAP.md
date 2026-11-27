# SYSTEM MAP: what Omar's system is and does today (read before proposing anything)

Every team gets this file. If an idea is already listed here as something that exists, it is NOT an upgrade: drop it.
"Exists" means built and running. Upgrades must build on top of what exists, never re-pitch it.
Last updated: 2026-11-27 (by Claude, from the real setup). Omar or Claude update it when something ships.

## STATUS BOARD
| Part | Status |
|---|---|
| TikTok (Omar's own page) | LIVE |
| Bounce Theory (YouTube) | LIVE, fully automatic on the server |
| Ambient Escape (YouTube) | LIVE, fully automatic on the server |
| WANTED LEVEL (GTA 6 clips, YouTube Shorts) | LIVE since Nov 18 2026, automatic on the server |
| LinkedAI (Chrome extension) | LIVE, selling |
| Growth Architect | PAUSED: under full rebuild by Omar. No team runs, no ideas, no upgrades, no leads, no mentions. |
| Fight & Court (NBA + UFC research) | LIVE on the server, research only |
| Trading Desk | LIVE, PAPER money only (Alpaca paper), 1-week test |
| Roblox sky obby | Built by Omar in Roblox Studio with Claude Code. Not run by agents. |
| SATR (Shopify Quran covers) | SHUT DOWN: Omar doesn't run it anymore. Never mention it. |
| NFC tags, TikTok effects | Side projects, not active. Don't pitch upgrades for them. |

## THE MACHINE (where everything runs)
- **Oracle Cloud server "openclaw"** (Always Free A1: 2 CPU, 12 GB RAM, Ubuntu 24.04, Toronto). Runs everything below by cron (`scripts/server/crontab.txt`). Laptop can be off.
- **Brains: Google Gemini API, FREE tier only.** Zero Claude in daily operation (Claude is only used by Omar to build). Separate Gemini keys/projects per area so one running out doesn't stop the others: shared, VIDEO, YOUTUBE, FIGHT, TRADING, WANTED. `agents/gemini/gemini.py` falls back across Flash models on 429/503 and demotes models that hit quota; non-text models (tts, image, live, etc.) are filtered out; broken JSON is repaired.
- **Agent HQ site:** GitHub Pages from repo `omarjaradat2006-sudo/agent-hq`. Each team writes `data/<team>/state.json`; the server runs `run_team.sh` (team.py -> apply_patch.py -> git push). Omar's Approve / Skip / I did it buttons commit straight to the repo. Done loop: pending -> approved / skipped -> done.
- **Private repo `bounce-engine`:** video engine, render and upload code (server has a deploy key).
- **Known weak spots (good places for SYSTEM upgrades):** Gemini free-tier quota and 429s, web-search quota (smaller than normal calls), a single server with no alerting when a job fails, git push races between jobs, logs only in `~/logs` on the server (Omar has to SSH to see them), no ntfy/phone alert yet for failures, render time on 2 ARM CPUs, disk space from renders.
- Omar can't SSH on his own easily; anything needing the server must be one pasted command at a time.

## TEAMS ON THE SERVER (Gemini, cron)
- **TikTok team** daily: performance review (Mon/Wed/Fri), research, 3 scripts in his content-scripts/VoicePrint scene format, caption packs.
- **YouTube team** daily 6:13 AM: writes the full day's lineup for both channels (24 Shorts each + longs), uses approved board ideas FIRST and tags each slot with ideaId, never reuses an uploaded title or recent template+settings combo, performance review.
- **LinkedAI team** weekly Mon: full competitor study + 3 install/conversion ideas (no promo scripts: the Promo Studio writes those).
- **LinkedAI Promo Studio** (connects the TikTok + LinkedAI teams, `agents/gemini/promo_studio.py`): research in small chunks, one an hour 3:37-8:37 AM daily (max 1 Gemini call each, saved to `~/research/promo/` on the server, fresh items skipped): Style Coach studies Omar's full TikTok history (`data/tiktok/history.json`) weekly; Ad Scout has Gemini watch one real AI-tool marketing Short (found with real view counts by the GitHub collector, `data/linkedai/ad_candidates.json`) and searches TikTok/Instagram examples (links kept only if Google loaded them or TikTok oEmbed confirms them). Mon/Wed/Fri 9:12 AM the Promo Director puts it together in one call: 2 promo videos in his content-scripts/VoicePrint format, each modeled on a real video (his or theirs, real link), with screen-recording shots. Shown on the LinkedAI floor's Promo lab tab.
- **LinkedAI Cheap Growth** (`agents/gemini/cheap_growth.py`): researches $0-50 install channels in 9 small chunks (1 Gemini search call an hour, Sat+Sun 3:11-11:11 AM, topics under 5 days old skipped, saved in `~/research/cheap-growth/` on the server), then Sun 12:41 PM one call ranks them into a weekly plan (top 3, steps, ready posts, $50 budget tracker, Chrome Web Store user count) on the LinkedAI floor's Cheap Growth tab. Omar records what he tried there. Never posts or spends.
- **AI Opportunities** weekly Wed: money ideas with build prompts + 100-person simulated test.
- **R&D Lab** every 3 days: SYSTEM upgrades + per-business upgrades (see rnd-lab.md).
- **GitHub Scout** every 3 days: free repos, answers Omar's repo requests.
- **Chief of Staff** weekly: one brief across all teams.
- **Growth Architect team + Upgrade Lab:** PAUSED (do not run).

## TIKTOK (Omar's main page, filmed by him)
- Sit-down talking videos, self-improvement for young guys + living life the Islamic way (most NOT about Islam).
- Pipeline on his laptop, one double-click "TikTok GO": OneDrive inbox -> **SmartEditor** (faster-whisper transcription, AI edit plan, silence/retake cuts that KEEP his stutters and natural pauses but trim the stop-recording bit, zooms at pauses, opening shake, flashes, word-by-word highlighted captions) -> AI caption + 5 hashtags -> uploads to TikTok DRAFTS via the official API (he adds sound and posts himself; never auto-post) -> caption to his phone via ntfy -> backup to OneDrive.
- Full details: `agents/context/tiktok-editing.md`. Captions, fonts, zooms, silence cuts, highlighted subtitles, auto captions, phone delivery are DONE: never pitch them.

## YOUTUBE (no filming, ever)
- **Bounce Theory:** satisfying physics sims (marble races, battles, bounce templates, "what if" physics fact Shorts with voiceover). 24 Shorts a day, one upload per hour, plus longs Mon/Wed/Fri. Rendered from a template menu (`data/youtube/bounce_templates.json`); every slot has `settings` from the menu.
- **Ambient Escape:** long sleep/rain/fire ambience videos from free Pixabay/Pexels clips + synthesized audio; Shorts are Islamic reminders, quizzes and animated Islamic explainer Shorts (refs checked against Quran/hadith texts). 24 Shorts a day.
- **Automatic idea flow (exists):** lineup fills from approved board ideas first; ideas auto-marked done after their video uploads and verifies; "Needs build" ideas wait for a template; the idea-to-template builder runs Tue/Thu/Sat 1:17 PM (Gemini writes a template, safety + test render, adds it to the menu); duplicate ideas are dropped.
- Uploads are verified before any local file is deleted. Channels are strictly separated. English only.
- **WANTED LEVEL:** GTA 6 clip Shorts, one an hour, ONLY from CC-BY sources or streamers who allow clipping (e.g. via Content Rewards). Never unlicensed footage.

## LINKEDAI (Chrome extension, live on the Chrome Web Store)
Already built, never pitch these as new:
- Reads the LinkedIn profile you're on, summarizes the person.
- **Outreach messages that find real common ground** between the user's own profile (jobs, skills, education, certifications, even transferable experience) and the other person, in 3 tones (Professional, Friendly, Direct), for job seeking, networking, recruiting and sales. (So "personalized outreach generator", "common-ground templates", "cold connection request writer" = ALREADY EXISTS.)
- Reads any LinkedIn job posting (job page scraping) and writes a **tailored resume and cover letter** for that job; 9 resume layouts + 9 matching cover-letter designs; downloadable; **Resume + Cover Letter discounted bundle**.
- Profile optimization suggestions; human-sounding writing rules (no AI-tell phrases, no em dashes).
- Google-only sign-in, Firestore credits per user, free plan + Pro monthly/yearly (yearly 20% off, credits delivered monthly), Stripe live checkout, backend on Render, site on Firebase (linkedai-ff45f).
- **LinkedAI Post Writer** app for ChatGPT (posts from notes, rewrite in his voice, hooks) on Cloudflare Workers, under OpenAI review.
- Marketing: short TikTok promos (creator-style, never "I built this") from the Promo Studio (6 a week, each modeled on a real video), UGC creators (flat fee per post + 1-year affiliate link), and the weekly Cheap Growth plan (store SEO/reviews, Reddit/communities, launch sites, newsletters, students, LinkedIn, micro-creators, small ad tests, affiliates). Don't re-pitch those channels as new; build on the plan's results.
Real upgrade areas: getting installs and paid conversions (store listing, reviews, onboarding, retention, referral), reliability when LinkedIn changes its layout, new features that are NOT in the list above, and better promo content.

## FIGHT & COURT
NBA same-game parlays daily (+100 / +500 / +1000 targets), UFC parlays + underdog picks Fridays 8 PM, DWCS Tuesdays, results graded every morning, record tab. FanDuel and DraftKings only, Bet365 excluded. Research only: never places bets, never logs into sportsbooks, no budget/deposit advice.

## TRADING DESK
News-driven paper trading bot (`agenthq-trading` service): news scout -> Gemini triage -> confirmation -> deep analysis (max 5 a day) -> risk officer -> Alpaca PAPER orders; halal screen; meme coins watch-only. Never live money without Omar's explicit authorization.

## HARD RULES FOR EVERY IDEA
- Free or near-free. No paid service or API without showing Omar the cost and getting his yes.
- Nothing posts, spends, bets or trades real money by itself.
- Never expose keys; keys live only in env files on the server.
- Halal income only. English only for YouTube.
- If it already exists above, it's not an idea.
