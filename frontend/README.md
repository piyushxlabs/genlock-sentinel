# 🖥️ Genlock Sentinel — Operations Console

> **Hollywood Carbon Cockpit Operations Dashboard for In-Camera Visual Effects (ICVFX)**  
> *Built with React 18, Vite, TypeScript, Tailwind CSS, and Lucide Icons.*

---

## Overview

The Genlock Sentinel Operations Console provides on-set virtual production supervisors, SREs, and volume engineers with real-time, broadcast-grade observability and control over cluster genlock synchronization.

Designed to live in high-contrast cinema control rooms, the interface features a specialized `#070A11` carbon cyberpunk design system with glassmorphism cards, an animated SVG workflow bus, moving-dash connectors, glowing status badges, a live radar sweep, an interactive 16-node cluster matrix, and an executive stage burn rate ticker ($1,800/min).

---

## Architectural Highlights

### 1. Zero-Jank AG-UI SSE Streaming Layer
- Direct connection to backend via Server-Sent Events (SSE) at `GET /sessions/{session_id}/stream`.
- Receives typed protocol events (`RUN_STARTED`, `STEP_STARTED`, `TOOL_CALL_*`, `REASONING_*`, `STATE_DELTA`, `RUN_PAUSED`, `RUN_FINISHED`, `SYNC_OFFSET_SAMPLE`).
- Projects incoming RFC 6902 JSON Patch state deltas automatically according to declared backend reducer semantics (`append-only`, `merge-by-key`, `last-write-wins`).

### 2. Generative UI Component Matrix
- **`SyncOffsetChart.tsx`:** Explicit 280px viewport container with rose glow breach gradients, live radar sweep line, 150µs breach threshold boundary, and permanent 16-node cluster matrix (R01–R16) with pulsing organic emerald/red indicators.
- **`StepTracker.tsx`:** Animated 7-node ADK Workflow graph pipeline with moving-dash connectors, step lifecycle badges (`active`, `completed`, `paused`, `error`), and elapsed millisecond execution clocks.
- **`DiagnosisBadge.tsx`:** Real-time brainwave activity visualizer, Gemini 3.1 Pro reasoning token stream, confidence rating dials, and diagnostic metadata tables.
- **`EvidenceCard.tsx`:** Dual-tabbed Grafana Loki log feed and Tempo distributed trace visualizer with Model Armor sanitization tags.
- **`ApprovalCardModal.tsx`:** High-contrast modal overlay triggered upon Node 6 `RUN_PAUSED` events, displaying financial cost delta estimates, visual impact risk ratings, and discrete Approve / Deny action buttons.
- **`RemediationLog.tsx`:** Append-only chronological audit trail of all autonomous and supervisor-authorized cluster mitigations with execution latencies.
- **`FailureBanner.tsx`:** Persistent global alert banner for permanent failures or circuit breaker trips with manual retry controls.

---

## Development & Build

### Running Locally
```bash
pnpm install
pnpm dev
```
*Console runs at `http://localhost:3000`.*

### Building Production Bundle
```bash
pnpm build
```
*Compiles 1868 modules via `tsc && vite build` in ~2.2s.*
