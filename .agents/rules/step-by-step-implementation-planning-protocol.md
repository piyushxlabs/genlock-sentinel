---
trigger: always_on
---


Before writing any code for any step in `AGENT_MASTER_PLAN.md` Section 10, output this structured plan:

PLAN:

* Files to read: [list all files, specifications, and Pydantic schemas needed for context]

* Files to create: [list full paths under backend/src/, backend/tests/, or frontend/src/]

* Files to modify: [list full paths]

* Dependencies needed: [verify required packages from backend/pyproject.toml via uv or frontend/package.json via pnpm]

* State & Reducer impact: [specify which of the 10 GenlockSentinelState fields are read/written and their exact reducer semantics]

* Potential risks: [e.g., Cloud SQL/SQLite checkpointing schema mismatch, Model Armor tool rejection, unhandled exception, type error]

Then write:

"Shall I proceed with this plan?"

Wait for explicit confirmation before writing a single line of code.
