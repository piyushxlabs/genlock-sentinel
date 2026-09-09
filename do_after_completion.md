━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 21 COMPLETION CHECKLIST
# Cockpit Scroll Affordance & Visual Card Peeking
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — do these first:

[ ] Verify frontend production bundle builds cleanly
    ```powershell
    cd "A:\Projects\GENLOCK SENTINEL\frontend"
    pnpm build
    ```
    Expected: `✓ built in ~2-3s` with 0 TypeScript errors.

[ ] Verify backend test suite remains 100% passing
    ```powershell
    cd "A:\Projects\GENLOCK SENTINEL\backend"
    uv run pytest tests/ -q
    ```
    Expected: `209 passed, 6 warnings in ~15s`

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — do these now:

[ ] Verify right-column scrollbar styling in `frontend/src/index.css`:
    ```powershell
    Get-Content "A:\Projects\GENLOCK SENTINEL\frontend\src\index.css" | Select-String "cockpit-scroll"
    ```
    Expected: `.cockpit-scroll::-webkit-scrollbar`, `.cockpit-scroll::-webkit-scrollbar-thumb`

[ ] Verify scroll affordance micro-badge in `frontend/src/App.tsx`:
    ```powershell
    Get-Content "A:\Projects\GENLOCK SENTINEL\frontend\src\App.tsx" | Select-String "Scrollable Feed"
    ```
    Expected: `Scrollable Feed ↕`

[ ] Verify card height capping in `frontend/src/components/DiagnosisBadge.tsx`:
    ```powershell
    Get-Content "A:\Projects\GENLOCK SENTINEL\frontend\src\components\DiagnosisBadge.tsx" | Select-String "320px"
    ```
    Expected: `maxHeight: "320px"` on both active and standby panels.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `frontend/src/index.css` — Custom `.cockpit-scroll` cyberpunk scrollbar styling with 6px cyan thumb, `max-height: 680px`, and 12px gap.
[ ] File: `frontend/src/App.tsx` — Applied `.cockpit-scroll` class to right-column container and added glowing `"Scrollable Feed ↕"` micro-badge.
[ ] File: `frontend/src/components/DiagnosisBadge.tsx` — Capped `DiagnosisBadge` and `DiagnosisStandbyPanel` height at `320px` with internal scroll so `EvidenceCard` peeks into view automatically.
[ ] Feature: Cyberpunk Scroll Affordance — Custom slim scrollbar matching deep carbon / cyan theme.
[ ] Feature: Visual Card Peeking — First card constrained to 320px, signaling more observability content below.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Files Exist & Modified:
```powershell
Get-Item "A:\Projects\GENLOCK SENTINEL\frontend\src\index.css"
Get-Item "A:\Projects\GENLOCK SENTINEL\frontend\src\App.tsx"
Get-Item "A:\Projects\GENLOCK SENTINEL\frontend\src\components\DiagnosisBadge.tsx"
```
✅ Expected: All three files exist with recent modification timestamps.
❌ If missing: Restore or pull from source.

Test 2 — TypeScript & Production Build Check:
```powershell
cd "A:\Projects\GENLOCK SENTINEL\frontend"
pnpm build
```
✅ Expected: `tsc && vite build` exits with code 0 in ~2-3s.
❌ If errors: Run `pnpm tsc --noEmit` to identify any type mismatches.

Test 3 — Dev Server Check:
```powershell
cd "A:\Projects\GENLOCK SENTINEL\frontend"
npm run dev
```
✅ Expected: Running at `http://localhost:3000/` with hot module replacement active.
❌ If errors: Check port 3000 conflicts.

Test 4 — Functional UI Check:
Open `http://localhost:3000/` in browser:
✅ Expected:
1. Right column displays `"Scrollable Feed ↕"` glowing badge at top right.
2. `DiagnosisBadge` standby sensor panel sits ≤ 320px height.
3. Top header of `EvidenceCard` (Node 2 Observability) peeks into view below it.
4. Right column scrolls smoothly with custom 6px slim cyan scrollbar.

Test 5 — Security Check:
[ ] Verify .env is in .gitignore
    ```powershell
    Get-Content "A:\Projects\GENLOCK SENTINEL\.gitignore" | Select-String ".env"
    ```
    ✅ Expected: `.env` and `*.env` appear in the output.
    ❌ If missing: Add `.env` to `.gitignore` immediately.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run this ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```powershell
git add .
git commit -m "Step 21: UI Polish — Cockpit scroll affordance and card peeking"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 22 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
