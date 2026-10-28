# Agent HQ

Omar's AI agent teams: TikTok, YouTube, LinkedAI, Growth Architect, AI Opportunities.

- Live sites: https://omarjaradat2006-sudo.github.io/agent-hq/
- Setup and data connections: [SETUP.md](SETUP.md)

## How it works

- `index.html` is the HQ floor. Each team has its own site in its folder (`tiktok/`, `youtube/`, …).
- Agents (Claude scheduled tasks) write to `data/<team>/state.json`: activity log, idea queue, research, daily brief.
- Hourly data collectors (`collectors/collect.py`, run by GitHub Actions) write `data/<team>/metrics.json`: your stats and what's trending in your niches.
- The sites read those files and refresh every minute.

## state.json shape (for agents)

```json
{
  "team": "tiktok", "hired": true, "updatedAt": "ISO",
  "agents": [{"id": "analyst", "name": "Analyst", "role": "...", "lead": false,
              "status": "working|idle|ok|waiting|error|off", "doing": "...", "lastRun": "ISO", "nextRun": "ISO"}],
  "log": [{"t": "ISO", "agent": "Analyst", "msg": "..."}],
  "ideas": [{"id": "tiktok-YYYY-MM-DD-1", "title": "", "hook": "", "why": "", "format": "", "script": "",
             "score": 8, "sources": [{"title": "", "url": ""}], "status": "pending|approved|skipped|done", "decidedAt": "ISO", "createdAt": "ISO"}],
  "research": [{"date": "YYYY-MM-DD", "createdAt": "ISO", "items": [{"title": "", "creator": "", "url": "", "metric": "", "whyItWorks": ""}]}],
  "brief": {"date": "", "createdAt": "ISO", "headline": "", "summary": "", "filmToday": [], "approvals": [], "notes": []},
  "processedIssues": [12, 13]
}
```

Keep `log` to the newest 100 entries and `research` to the newest 14 days.
