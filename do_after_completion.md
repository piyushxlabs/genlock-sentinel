━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 21 COMPLETION CHECKLIST
# Cockpit Scroll Affordance, Card Peeking & Flex Shrink Protection
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

[ ] Verify `.shrink-0` wrapper in `frontend/src/App.tsx`:
    ```powershell
    Get-Content "A:\Projects\GENLOCK SENTINEL\frontend\src\App.tsx" | Select-String "shrink-0"
    ```
    Expected: Three `shrink-0` divs wrapping `DiagnosisBadge`, `EvidenceCard`, and `RemediationLog`.

[ ] Verify natural height on `DiagnosisBadge` in `frontend/src/components/DiagnosisBadge.tsx`:
    ```powershell
    Get-Content "A:\Projects\GENLOCK SENTINEL\frontend\src\components\DiagnosisBadge.tsx" | Select-String "320px"
    ```
    Expected: No occurrences (320px constraint removed).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `frontend/src/index.css` — Custom `.cockpit-scroll` cyberpunk scrollbar, `.shrink-0` utility rule, and `gap: 16px` on `.cockpit-col-right`.
[ ] File: `frontend/src/App.tsx` — Applied `.cockpit-scroll` class, wrapped cards in `shrink-0` (`flex-shrink: 0`) wrappers, and added glowing `"Scrollable Feed ↕"` micro-badge header.
[ ] File: `frontend/src/components/DiagnosisBadge.tsx` — Removed forced `maxHeight` constraints from both active `DiagnosisBadge` and `DiagnosisStandbyPanel` for full natural rendering.
[ ] Feature: Flex Shrink Protection — Cards never squash or collapse into unreadable strips inside the flex scroll container.
[ ] Feature: Visual Card Peeking — Natural card height allows `EvidenceCard` to peek cleanly below `DiagnosisBadge`.

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
1. `DiagnosisBadge` standby sensor panel renders at full natural height (header, brainwave SVG, and model telemetry table are completely readable and un-squashed).
2. Right column displays `"Scrollable Feed ↕"` glowing badge at top right.
3. Top header of `EvidenceCard` (Node 2 Observability) peeks into view below `DiagnosisBadge`.
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
git commit -m "Step 21: UI Polish — Fix squashed DiagnosisBadge with flex-shrink-0 protection"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Step 22 until:
[ ] All tests above show ✅
[ ] Git commit is done
[ ] You have read do_after_completion.md fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
