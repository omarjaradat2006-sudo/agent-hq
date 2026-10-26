# Swarm test: 100 simulated people debate the idea

Use Omar's swarm-prediction skill (Skill tool: "swarm-prediction" or "anthropic-skills:swarm-prediction"). Load it and follow its phases, with these settings. If the skill isn't available, run the same thing by hand (personas, rounds, report) without the engine.

## What to test
- AI Opportunities: the opportunity the Venture Lead ranks #1 this run.
- Growth Architect / LinkedAI: the positioning, feature, pricing or ad-angle idea from this run (or the top promo hook if there isn't one).
Seed material = the idea's title, hook, why and script, plus the product facts in your prompt and the competitor findings from this run.

## Cast: 100 agents, 5 groups of 20
1. Investors / VCs / angel investors (would they fund or buy this?)
2. Target customers (job seekers or small-business owners, depending on the product; for opportunities, the people who'd pay)
3. Skeptics and critics (people who have tried competitors, Reddit-style "this is a wrapper" voices)
4. Marketers / growth people / creators (would this spread? what's the hook?)
5. Everyday users and bystanders (casual scrollers, students, parents)
Mix ages, countries (lean Canada/US), stances and activity levels. All agents are invented representative people (mark invented: true); never impersonate real named people.

## Run size (keep it inside one scheduled run)
platform "reddit" (threaded debate), total_simulation_hours 12, minutes_per_round 60, agents_per_hour_min 15, agents_per_hour_max 30. One initial post presents the idea. Let them argue: reply to each other, change minds only for a reason.

## Output: add to the idea as "swarm", and prepend to "swarms" in state.json (keep 10)
```
"swarm": {
  "date", "createdAt", "ideaId", "idea": "title",
  "verdict": "one sentence: would people back it, and the condition that decides it",
  "score": 1-10,
  "support": {"for": %, "against": %, "undecided": %},   // final stances across all 100
  "groups": [{"name":"Investors","for":%, "quote":"real post from the sim", "username":"@..."}],  // all 5 groups
  "topPraise": ["..."], "topObjections": ["..."],
  "changedMinds": "what argument moved people, if any",
  "fixes": ["1-3 concrete changes that would win over the objectors"],
  "limits": "one line: one model played all 100 agents; this is a rehearsal, not a forecast"
}
```
Only quote posts the agents actually made in the sim. Feed the result back: adjust the idea's score and mention the verdict in its why.
