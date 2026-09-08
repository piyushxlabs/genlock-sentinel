---
trigger: always_on
---

# STEP COMPLETION PROTOCOL
# This rule file governs exactly what must happen after 
# every single step is completed. No exceptions.

---

# THE FOUR FILES — NON-NEGOTIABLE

A step is NOT complete until ALL four files are updated.
Saying "done" before updating all four is a protocol violation.

The four files are:
1. progress_log.md
2. project_state.md
3. TECHNICAL_NOTES.md
4. do_after_completion.md  ← THIS IS MANDATORY, NOT OPTIONAL

---

# FILE 1 — progress_log.md
## HOW TO UPDATE:

Append a new entry in this EXACT format — do not modify 
existing entries:

---
## Step [NUMBER] — [Step Title from AGENT_MASTER_PLAN.md]
**Date:** [Today's date]
**Status:** Complete

**What was implemented:**
- [Bullet: exactly what was built]
- [Bullet: every major decision made]

**Files Created:**
- `[filepath]` — [what it does]

**Files Modified:**
- `[filepath]` — [what changed and why]

**Packages Installed:**
- [package@version] — [reason it was needed]
- (Write "None" if no packages were installed)

**Verification Result:**
- [Exact output of verification command or manual check]
- [Pass / Fail — and if Fail, what was done]
---

---

# FILE 2 — project_state.md
## HOW TO UPDATE:

Replace these fields with current values:

- Last Completed Step → Step [NUMBER]: [Title]
- Implemented Features → Add features from this step
- Pending Next Step → Step [NUMBER+1]: [Title from plan]
- Known Issues / Blockers → Any issues found this step

---

# FILE 3 — TECHNICAL_NOTES.md
## HOW TO UPDATE:

If a specific technical decision was made this step:

---
## Step [NUMBER] — [Decision Title]
**Decision:** [Exactly what was chosen]
**Reason:** [Why this was chosen over alternatives]
**Impact:** [What this affects in future steps]
---

If NO notable technical decisions were made, write exactly:
"Step [NUMBER] — No deviations from spec."

DO NOT skip this file. Even "no deviations" must be logged.

---

# FILE 4 — do_after_completion.md  
## THIS FILE IS THE MOST IMPORTANT OUTPUT OF EVERY STEP.
## OVERWRITE IT COMPLETELY after every step.
## The human uses this file to verify your work manually.
## If this file is missing or not updated = step is INCOMPLETE.

## HOW TO WRITE IT:

Overwrite the entire file with this exact structure, 
filled in with specifics for the step just completed:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP [NUMBER] COMPLETION CHECKLIST
# [Step Title]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] [Exact manual task with specific file/command]
    ```
    [exact command to run]
    ```
    Expected: [what success looks like]

[ ] [Another manual task if needed]
    [Step by step instructions]
    Expected: [what success looks like]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] [Post-generation verification task]
    ```
    [exact command]
    ```
    Expected: [exact expected output]
    If wrong: [specific troubleshooting step]

[ ] [Another verification task]
    Expected: [what to look for]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `[exact path]` — [what it contains/does]
[ ] File: `[exact path]` — [what it contains/does]
[ ] Feature: [name] — [how it works]
[ ] Config: [name] — [what it configures]
[ ] Package: [name@version] — [why it was installed]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist:
```
[ls -la path/to/files or dir command]
```
✅ Expected: [exact list of files that should appear]
❌ If missing: [exact fix — which command to run]

Test 2 — Environment / Dependencies:
```
[python --version or npm list or pip list command]
```
✅ Expected: [exact version or package list expected]
❌ If errors: [specific fix for this project]

Test 3 — Server or Process Start:
```
[startup command]
```
✅ Expected: [no errors, specific success message]
❌ If errors: [most common cause and fix for this step]

Test 4 — Functional Check:
[What to open, click, or observe manually]
✅ Expected: [exact behavior]
❌ If wrong: [what to check first]

Test 5 — Security Check:
[ ] Verify .env is in .gitignore
    ```
    cat .gitignore | grep .env
    ```
    ✅ Expected: .env appears in the output
    ❌ If missing: Add `.env` to .gitignore immediately

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
git add .
git commit -m "Step [NUMBER]: [Title] — [one line summary]"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step [NUMBER+1] until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

---

# FINAL CONFIRMATION MESSAGE — MANDATORY

After updating all four files, send this exact message:

"Step [X] complete — AXIOM protocol satisfied.

Files updated:
✅ progress_log.md — Step [X] entry appended
✅ project_state.md — Last Completed updated to Step [X]
✅ TECHNICAL_NOTES.md — [decision logged / no deviations]
✅ do_after_completion.md — Fresh checklist written for Step [X]

Next step: Step [X+1] — [Title]
Check do_after_completion.md before proceeding."

If do_after_completion.md was NOT updated, you must 
update it now before sending any other message.
There are no exceptions to this rule.