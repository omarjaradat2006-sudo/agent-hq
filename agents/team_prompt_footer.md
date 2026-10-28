(Reference copy of the shared steps used in every team's scheduled task.)

STEP 0 — Call ToolSearch "select:ArtifactData", then ArtifactData action "set", url https://claude.ai/artifact/ShAXm2hq51Xp6Wsr1iuwX9, collection "debug", doc_id "<TEAM>-latest", data {"startedAt":"<ISO now>","step":"started"}.
STEP 1 — Get the repo: cd /home/claude/agent-hq 2>/dev/null && git pull --rebase || git clone https://github.com/omarjaradat2006-sudo/agent-hq /home/claude/agent-hq
STEP 2 — Show you're working, commit "<Team>: run started", push.
STEP 3 — Omar's decisions: follow agents/RUNBOOK.md section 3. The site writes statuses (pending / approved / skipped / done) straight into state.json; never overwrite them. Only `done` R&D upgrades are available; approved-but-not-done ones are listed as "Waiting on Omar" and never used in plans.
... team work ...
FINISH — statuses ok, lastRun, nextRun, log, validate JSON, commit, push (pull --rebase, retry 3x). Error → status error + plain-English doing.
LAST — ArtifactData "set" debug/<TEAM>-latest {"finishedAt","result"}.
