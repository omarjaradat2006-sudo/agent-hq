# AI Opportunities: build prompts and rule checks

Omar doesn't want to piece together prompts himself. **Every opportunity gets a `buildPrompt`**, a complete prompt he copies with one tap on the site ("Copy build prompt") and pastes into a NEW Claude chat. That chat does the building.

## What goes in `buildPrompt`
Write it to Claude, in second person, as one self-contained block (it must work without this conversation or this repo's other files). 150-400 words. Include:

1. **Context in 2-3 lines.** Who Omar is (student in Mississauga, Ontario, Canada; Muslim, so no haram income streams; small budget; Windows laptop, runs steps in PowerShell, downloads files to Downloads) and which of his assets it reuses, by exact name: LinkedAI Chrome extension (Firebase project linkedai-ff45f, backend on Render, Stripe), Growth Architect (Base44 app id 699b4057d65174480989a52e), Agent HQ repo omarjaradat2006-sudo/agent-hq, his skills (content-scripts, voiceprint, bounce-theory-videos, ambient-escape-videos, swarm-prediction, trend-ideas), TikTok page, YouTube channels Bounce Theory and Ambient Escape, SATR Shopify store, NFC review tags.
2. **The goal and the finish line.** What exists when the chat is done (e.g. "a deployed Cloudflare Worker at /mcp that passes these checks", "10 outreach DMs and a one-page offer as a doc", "a Python script in Downloads\clipper that turns a YouTube URL into 5 captioned 9:16 clips").
3. **Build it, don't explain it.** Tell Claude to do the work itself with its tools, step by step: write the files, test them, and package anything Omar has to run as one zip plus one PowerShell command. Ask him only for what Claude truly can't do (logins, payments, verification, uploading).
4. **Constraints.** Free or cheapest tools, no new paid subscriptions without saying the monthly cost, and the platform rules from the rule check below.
5. **How to know it worked.** The 2-week test from the plan, written as a checklist.

If the opportunity is mostly service or outreach rather than code, the prompt builds the first assets instead: offer page, price sheet, DM templates in his voice (voiceprint skill), a lead list method, or a demo.

## Rule check (required before scoring)
Before writing any opportunity that depends on a platform (app stores, GPT/ChatGPT app directory, Chrome Web Store, Whop, TikTok/YouTube programs, marketplaces), **fetch that platform's current policy page** and confirm the money mechanism is allowed: subscriptions, upsells, affiliate links, reposted content, AI disclosure, payouts in Canada. Put the policy page in `sources`, and add one line to `script`, "Rule check: …", saying what's allowed and what isn't. If the mechanism isn't allowed, change the plan to one that is, or drop the idea.

Lesson: on 2026-10-28 the team pitched "free limit + link to the LinkedAI upgrade page" for a ChatGPT app. OpenAI's app guidelines don't allow freemium upsells for digital subscriptions, so it had to be rebuilt as a free funnel.

## Field order in each idea
id, title, hook, why, format, script, buildPrompt, score, sources, status, createdAt (plus `swarm` when tested).
