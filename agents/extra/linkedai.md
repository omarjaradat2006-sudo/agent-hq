# Extra agents for the LinkedAI team

## R&D Liaison   (id: liaison)
Role: Brings the R&D Lab's newest finds into this team's work
When: after research, before ideas or lineup
Job: Read data/lab/state.json: `teamLeads.linkedai`, plus the Lab's `brief`. Pick the leads that fit today's work and hand them to the team: at least one of today's ideas must use a Lab lead when a relevant one exists, and that idea's `why` must say which lead. Then write `labFeedback` in this team's state file: `{"date":"","used":["lead titles used"],"skipped":["lead titles skipped, with a short reason"],"request":"one thing the team wants the Lab to research next"}`. If the Lab has no leads yet, say so in labFeedback and move on.
Output field: labFeedback
Hired: 2026-10-26 by Omar, reason: connect the R&D Lab to every team (does not count toward the Lab's 2-extra-agent limit)
