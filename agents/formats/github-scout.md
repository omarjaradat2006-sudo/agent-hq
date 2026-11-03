# GitHub Scout: free repos that make Omar's work easier

Goal: find free, open-source GitHub repos (tools, models, Claude Code skills/plugins, MCP servers, scripts) that save Omar time or money, or make his content better, across his whole setup: Bounce Theory and Ambient Escape video pipelines (Python, ffmpeg, the local `render.py`), TikTok editing, AI voice, thumbnails, LinkedAI (Chrome extension), Growth Architect (Base44 app), SATR (Shopify), NFC tags, and Agent HQ itself. Example of the kind of find: an open-source alternative to a paid AI video tool.

## Know what he already has
Before proposing anything for TikTok editing, captions, fonts or video tools, READ `agents/context/tiktok-editing.md` (his SmartEditor / "TikTok GO" pipeline and SmartSub captions). Only propose what beats or adds to it; if a repo duplicates it, skip it and say "already covered".

## Quality over quantity (Omar's rule)
Write **1-3 repos per run, never more**, only ones that clearly beat what he uses now. If 5 or more repos are pending or approved-but-not-done, write at most 1. No near-duplicates of earlier finds. If nothing is good enough, write none and say why in the brief.

## Omar's requests come first
`requests` in data/repos/state.json holds what Omar typed on the site ({text, at, status:"open"}). Handle every open request (max 3) before anything else:
- Find **at least 3-5 candidate repos** for it and compare them side by side (stars, last commit, features, licence, what it needs to run). Never recommend the first hit.
- For the strongest 1-2, **inspect the code**: clone into a throwaway sandbox folder (e.g. /tmp/scout/<name>, never inside agent-hq), read the install script, requirements and main entry points, and look for red flags (obfuscated code, curl|bash from unknown hosts, credential collection, crypto miners, telemetry to unknown servers).
- **Try it in the sandbox** when it can run on CPU in a few minutes (install in a venv, run its example or tests). Say exactly what you ran and what happened. If it needs a GPU or a paid key, say so and don't fake a result.
- Write the winner as a repo idea (status "pending") with `request` set to the request text, and in `why` say which others it beat and why. Then set the request's `status` to "answered" and `answer` to one line ("Best: owner/repo — beat X and Y because ...", or "Nothing good enough yet: ..."). Delete the sandbox folder afterwards.
Requests don't count toward the 1-3 weekly limit below.

## Each run
1. **Read first:** every data/*/state.json (pain points in reviews, briefs, Lab upgrades, errors) and this file's earlier repos (don't repeat; learn from what he approved, skipped and marked done).
2. **Repo Scout** (15-25 searches): GitHub search/topics, "awesome" lists, Hacker News, Reddit, X posts about new repos from the last ~90 days. Target the pain points you found.
3. **Fit Checker**, for every candidate, check on the repo page itself:
   - **Real and alive:** stars, last commit within ~6 months, open issues not full of "doesn't work".
   - **Licence:** MIT/Apache/BSD/GPL fine for his use; flag non-commercial licences (he monetizes videos) and model weights with separate licences.
   - **Safety:** official repo (not a fork posing as it), no cracked/pirated software, nothing that wants his passwords or tokens, no obfuscated install scripts. Skip anything doubtful.
   - **Runs for him:** say exactly where: Claude Code cloud session, his Windows laptop CPU, or needs a GPU (he has no strong GPU; say if it needs a paid cloud GPU and the rough cost).
4. **Scout Lead:** rank, write the brief.

## Repo format (each one is an idea in data/repos/state.json)
```
{"id":"repos-YYYY-MM-DD-n","title":"<repo name>: what it does in 5 words",
 "hook":"the payoff in one line, e.g. 'Free AI voice that sounds better than Kokoro'",
 "why":"which pain point it fixes, with the evidence",
 "format":"<Business> · <Runs on: Claude Code / Laptop / GPU> · <setup time>",
 "business":"Bounce Theory|Ambient Escape|TikTok|LinkedAI|Growth Architect|SATR|NFC tags|Agent HQ|All",
 "repo":"https://github.com/owner/name","stars":12345,"lastCommit":"YYYY-MM-DD","license":"MIT",
 "score":1-10, "script":"what it replaces or adds, step-by-step setup, risks, how to tell in a week if it helped (100-200 words)",
 "buildPrompt":"a complete, self-contained prompt to install and wire it up (name the repo URL, the folder, the skill or script it plugs into). First line says where to paste: \"Paste into Claude Code opened in Downloads\\YOUTUBE HQ\" (or Downloads\\SmartEditor) when it changes his laptop tools, YouTube pipeline, SmartEditor/TikTok GO or the two video skills; otherwise \"Paste into Omar's Main Chat in the Claude app\"",
 "sources":[{"title":"repo","url":""}],"status":"pending","createdAt":""}
```
Statuses follow agents/RUNBOOK.md section 3: pending → approved / skipped → done. Only a "done" repo counts as installed; approved-but-not-done ones are "Waiting on Omar" in the brief. Only ever install or run repos inside a throwaway sandbox folder in your own session, never on Omar's computer and never inside the agent-hq repo. Never sign up or pay for anything, and never paste any of Omar's keys or tokens into a repo.

## Research entry
Prepend `{date, createdAt, items:[5-8 candidates you looked at: title, creator (owner/repo), url, metric ("12.3k stars, updated Oct 2026"), whyItWorks (fits or why rejected)]}`; keep 8 entries.

## Brief
`{date, createdAt, headline (<12 words), summary (2-3 sentences to "you": the best find and what it replaces), filmToday:["<repo> — first step"], approvals:["N repos to review", "Waiting on Omar: <title>" ...], notes:[1-3 heads-ups, e.g. a licence catch]}`
