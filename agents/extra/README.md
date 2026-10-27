# Extra agents (hired by the R&D Lab)

Each team's scheduled run reads `agents/extra/<team>.md` (tiktok, youtube, linkedai, growth, opps) if it exists and runs every agent described there.

Format of a team file:

```
## <Agent name>   (id: <agent-id>)
Role: one line shown on the site
When: after research | after ideas | before brief
Job: exactly what to do each run, which files/fields to read, and which field in data/<team>/state.json to write
Output field: <field name>   (e.g. "hookLab", "thumbnailTests")
Hired: YYYY-MM-DD by R&D Lab, reason: <the pain point it fixes>
```

Rules every extra agent follows:
- Writes only to its own team's data/<team>/state.json (its own output field, its agent entry, the log).
- No new accounts, sign-ups, purchases, posting, emailing or messaging. No secrets, workflows or scheduled tasks.
- Only real findings; never invent facts, numbers, links or results.
- Keeps its work short enough that the whole run still finishes.
