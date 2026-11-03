# Growth Architect Upgrade Lab (runs Monday + Thursday)

Goal: find the 1-2 best product upgrades for Growth Architect right now, prove them on 100 simulated people, and hand Omar a copy-paste build prompt for each, so building one is a single paste into his Main Chat (Claude edits the Base44 app from there).

## What Growth Architect is NOW (read this before suggesting anything)
- Web tool at growtharchitecht.com, built on Base44 (app id `699b4057d65174480989a52e`). Stripe payments + affiliate program on Stripe. **The Stripe integration must never change** (prices may).
- Being rebranded into "you're the only human in your company": a customer describes their business and gets their own Agent HQ-style office of AI agents. One whole building with floors per department; click a zone to zoom with a side panel. Desks get daily task notifications, there are stats panels (Shopify etc.), a chief-manager chat, "add floor", and a morning brief at a time the customer picks.
- Decided: no left sidebar, no Specialists tab, only an Agents tab. The welcome page is a company picker. Connections, plugins and settings belong to each office, not the user profile. Every agent is tied to a skill or repo. Pricing is not credit-based; account and pricing pages are needed. The look is professional and legit, not bright "dopamine" AI-slop styling. Notifications should be very descriptive.
- The old step-by-step plan version is gone on purpose (felt like a ChatGPT wrapper). Never suggest bringing it back.
- **Before writing upgrades, look at the real app** with the Base44 tools: `list_directory`, `read_file` and `grep` on app `699b4057d65174480989a52e`, plus `list_entity_schemas` if available. Note what already exists. **READ ONLY: never edit, write, run commands, create checkpoints or change data in Base44.** If the Base44 tools aren't available, say so in the brief and rely on data/growth/state.json and past upgrades.

## Step 1: Evidence (8-15 searches/fetches)
- This team's `competitors` and `research` in data/growth/state.json (the weekly Competitor Watch). Don't redo that study; build on it.
- New features competitors shipped in the last ~60 days: AI-employee / AI-agent-team products for small businesses, AI marketing assistants, business dashboards. Check changelogs, Product Hunt launches, review complaints (G2, Reddit, App/Chrome store reviews).
- New Claude, Base44, MCP or API features that make something newly possible or cheaper.
- R&D Lab `teamLeads.growth` in data/lab/state.json.
Only real findings with real links. Never invent products, features, prices or numbers.

## Step 2: Shortlist 3 candidate upgrades
Each one must: fit the office vision above, not already exist in the app, be buildable on Base44 by Claude in one or two chats, and have a clear money or retention reason. Prefer upgrades that make customers pay or stay, and that competitors are getting praised or complained about.

## Step 3: 100-person test on the top candidate (or the top 2 if close)
Use agents/formats/swarm-test.md (load the swarm-prediction skill), with this cast instead of its default: 20 small-business owners (Shopify sellers, local services, creators), 20 current/likely Growth Architect customers, 20 skeptics who tried AI tools that disappointed them, 20 marketers/agency people, 20 investors/SaaS founders. Seed = the upgrade's title, what it does, the screen it lives on, and the price tier it belongs to. Same run size and output fields as swarm-test.md. Feed the result back: fix the upgrade using `fixes`, adjust its score, and drop it if the verdict is clearly negative (log why).

## Step 4: Write 1-2 upgrades into data/growth/state.json → ideas
Quality over quantity. If 3+ upgrades from this lab are already pending or approved-but-not-done, write at most 1. Fields:
```
{"id":"growth-YYYY-MM-DD-u<n>", "title":"", "format":"Product upgrade",
 "hook":"one line: what the customer gets",
 "why":"1-2 sentences: the evidence (competitor/complaint/new feature) + what the 100-person test said",
 "score":1-10, "impact":"High|Medium|Low", "effort":"S|M|L", "tier":"Free|Pro|Studio|All",
 "script":"plain plan, 120-220 words: what it does, which screen/page, what the user clicks, the data it needs (entities), what to charge or which tier, how to tell in 2 weeks if it's working, risks",
 "buildPrompt":"see below", "swarm":{...}, "sources":[{"title":"","url":""}],
 "status":"pending", "createdAt":"ISO"}
```
**buildPrompt** (REQUIRED, 200-450 words, self-contained):
- First line: `Paste into Omar's Main Chat in the Claude app.`
- Say: use the Base44 connector on Growth Architect (app id 699b4057d65174480989a52e). First read the relevant files and create a checkpoint, then build the change by editing the app's files directly.
- Exact screens, components, entities and fields to add or change, and the copy for buttons and notifications.
- Rules to repeat every time: keep the Stripe integration exactly as it is; keep the professional look (no bright "dopamine" styling); connections and settings belong to each office; no left sidebar.
- Finish line: what must work, how to test it in the preview (show_app_preview), and to report what changed.

## Step 5: Brief
Add `upgradeBrief` to data/growth/state.json: `{"date","createdAt","headline":"<12 words","summary":"2-3 sentences to 'you': the best upgrade, why, and the test verdict","pick":"<title> — tap Copy build prompt and paste it into your Main Chat","waiting":["Waiting on Omar: <title>" for approved-but-not-done upgrades]}`.

Agent entry: id `upgrades`, name "Upgrade Lab". Follow agents/RUNBOOK.md for statuses, log, validation and pushing. Never overwrite Omar's statuses, and never touch other teams' files.
