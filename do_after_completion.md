━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STEP 21 COMPLETION CHECKLIST
# Hollywood ICVFX Mission Control Visual Elevation
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⏰ BEFORE running the next prompt — verify these first:

[ ] Frontend dev server is still running
    ```
    # Should already be running from previous session:
    # npm run dev (in A:\Projects\GENLOCK SENTINEL\frontend)
    ```
    Expected: Server on http://localhost:3000/ (already confirmed running)

[ ] Hard-refresh the browser (Ctrl+Shift+R) to pick up hot-reloaded changes
    Open: http://localhost:3000/
    Expected: New dark carbon cockpit UI loads immediately

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ AFTER code was generated — verify these now:

[ ] Build passes with zero errors
    ```
    cd "A:\Projects\GENLOCK SENTINEL\frontend"
    pnpm build
    ```
    Expected: `✓ built in ~3s` — zero TypeScript errors
    ✅ ALREADY VERIFIED: 1868 modules transformed, 2.92s, exit code 0

[ ] Visual inspection at http://localhost:3000/ — check each area:

  HEADER:
  [ ] "GENLOCK SENTINEL" text shows a gradient (white → light cyan)
  [ ] Amber nuclear badge shows live ticking: $X.XX.XX format changing every frame
  [ ] Subtext "CALCULATED AT $1,800/MIN PRODUCTION LOSS" visible below amount
  [ ] Emergency Stop button shows diagonal hazard-stripe pattern
  [ ] Session clock HH:MM:SS is counting up
  [ ] Header has a 2px cyan top border accent

  STEP TRACKER (7-Node Pipeline):
  [ ] Nodes are in a horizontal row connected by SVG arrows
  [ ] Node 1 (Stream Watch) shows cyan halo-pulse ring (active)
  [ ] Connector lines show animated moving-dash cyan arrows
  [ ] Branch legend is visible at the bottom

  CHART (Frame-Sync Telemetry):
  [ ] A vertical beam/line is slowly sweeping left→right→left continuously
  [ ] The sweep is visible even with no data loaded (idle state)
  [ ] Threshold line has a red glowing aura/blur above it
  [ ] Hazard hatch (diagonal stripe) pattern fills area above 150µs
  [ ] 16-node Render-01 to Render-16 LED grid is visible below chart
  [ ] Each node shows a pulsating green LED ping dot
  [ ] "ALL NODES FRAME-LOCKED · 0 DRIFT DETECTED" status bar visible

  EVIDENCE PANEL (empty state):
  [ ] Rotating radar sweep SVG circle is animating
  [ ] "LOKI / TEMPO MCP BUS ACTIVE" label blinks gently
  [ ] Grafana MCP / Loki / Tempo status rows show green CONNECTED/ARMED labels

  DIAGNOSIS PANEL (empty state):
  [ ] Brain-wave EKG SVG with scanning dot is visible
  [ ] "NODE 3 ARMED · AWAITING EVIDENCE BUNDLE" label blinks
  [ ] Model config rows visible: Gemini 3.1 Pro, temp 0.0, etc.

  BACKGROUND:
  [ ] Page background is deep carbon (#070A11) — not pure black, not grey
  [ ] Subtle cyan radial gradient visible at the top center
  [ ] 32px grid lines faintly visible in the background

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ WHAT GOT BUILT THIS STEP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[ ] File: `frontend/src/index.css` — complete carbon cockpit design system:
    15+ new keyframes (halo-pulse, led-ping, radar-sweep, burn-micro, standby-blink),
    32px CSS grid overlay on #root::before, glassmorphism with backdrop-blur(20px),
    nuclear burn badge class, aircraft emergency stop with hazard stripe

[ ] File: `frontend/src/components/StepTracker.tsx` — animated SVG workflow bus:
    moving-dash connector lines energize left-to-right as steps complete,
    cyan halo-pulse ring on active nodes, emerald ring on completed,
    branch legend, RAF-driven tick animation

[ ] File: `frontend/src/components/SyncOffsetChart.tsx` — broadcast-grade telemetry:
    neon gradient area fill (cyanGlow linearGradient), red aura on threshold line,
    SVG hazard hatch pattern above breach perimeter, live RAF radar sweep bounce,
    16-node Render-01→Render-16 LED matrix with staggered emerald ping animations

[ ] File: `frontend/src/components/EvidenceCard.tsx` — cybernetic MCP bus standby:
    animated SVG radar circle sweep, Grafana/Loki/Tempo status rows,
    standby-blink label

[ ] File: `frontend/src/components/DiagnosisBadge.tsx` — armed standby sensor:
    brain-wave SVG with scanning dot, model config panel, standby-blink label

[ ] File: `frontend/src/App.tsx` — nuclear header elevation:
    gradient logo, live ms burn ticker, production loss subtext,
    session clock, Radio SSE indicator, aircraft emergency stop

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 TESTING & VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Test 1 — Build passes:
```
cd "A:\Projects\GENLOCK SENTINEL\frontend"
pnpm build
```
✅ Expected: `✓ built in ~3s` — zero TS errors
❌ If errors: Check for any new unused variables — prefix with underscore

Test 2 — Files exist:
```
dir "A:\Projects\GENLOCK SENTINEL\frontend\src\components"
dir "A:\Projects\GENLOCK SENTINEL\frontend\src"
```
✅ Expected: StepTracker.tsx, SyncOffsetChart.tsx, EvidenceCard.tsx,
   DiagnosisBadge.tsx, App.tsx, index.css all present

Test 3 — Live console at http://localhost:3000/:
- Hard refresh (Ctrl+Shift+R)
✅ Expected: Carbon cockpit UI loads, animations visible immediately
❌ If blank page: Check browser console for errors

Test 4 — Drift injection still works:
```
cd "A:\Projects\GENLOCK SENTINEL\backend"
uv run python scripts/simulate_drift.py --scenario complex
```
✅ Expected: Chart shows spike, step tracker animates through all 7 nodes,
   evidence panel fills with real data, diagnosis standby is replaced,
   HITL modal appears
❌ If backend not running: `uv run uvicorn src.main:app --port 8000`

Test 5 — Interface boundary compliance:
[ ] No chat box or free-text input anywhere on the page
[ ] No manual actuator controls visible in the UI
[ ] No raw credentials or internal session data visible
[ ] Approve/Deny/Stop are the only action controls (modal only when pending)

Test 6 — Security:
[ ] .env is in .gitignore
    ```
    cat "A:\Projects\GENLOCK SENTINEL\.gitignore" | findstr ".env"
    ```
    ✅ Expected: .env appears in output

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 GIT COMMIT
(Run ONLY after all above checks pass)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

```
git add .
git commit -m "Step 21: Hollywood ICVFX Mission Control Visual Elevation — Carbon cockpit, animated SVG workflow bus, neon chart, radar sweep, LED matrix, nuclear burn badge"
```

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✋ DO NOT proceed to Production Readiness until:
[ ] All visual checks above show ✅
[ ] pnpm build shows zero errors
[ ] Drift injection demo still works end-to-end
[ ] Git commit is done
[ ] You have read this file fully
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
