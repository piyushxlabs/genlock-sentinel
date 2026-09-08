---
trigger: always_on
---

Before modifying any existing file:

* Read the entire file first to maintain full architectural context.

* Identify every other file that imports from it (especially `src/state/schema.py`, `src/state/reducers.py`, `src/tools/schemas/pydantic_models.py`, `src/tools/schemas/mcp_schemas.py`, and `src/safety/prohibition_guards.py`).

* Never blindly overwrite — merge new functionality cleanly into the existing module structure while preserving Pydantic V2 type hints, strict schema validation (`extra="forbid"`), and `async`/`await` signatures.

* If a conflict is found between new instructions and the 5 locked specification documents, STOP and report the discrepancy before proceeding.
