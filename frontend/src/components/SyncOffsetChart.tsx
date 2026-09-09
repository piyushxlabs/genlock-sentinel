import React, { useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, Radio, ShieldCheck } from "lucide-react";
import { DriftEvent, SyncOffsetSample } from "../stream/agui-client";

export interface SyncOffsetChartProps {
  samples: SyncOffsetSample[];
  thresholdUs?: number;
  activeDriftEvents?: Record<string, DriftEvent>;
}

export interface TelemetryPoint {
  timestamp: string; // HH:MM:SS
  offset: number;    // in microseconds
}

// 16 render node names for the idle cluster matrix
const RENDER_NODES = Array.from({ length: 16 }, (_, i) =>
  `Render-${String(i + 1).padStart(2, "0")}`
);

const NODE_COLORS: Record<string, string> = {
  "render-07": "#06b6d4",
  "render-12": "#a855f7",
  "render-01": "#10b981",
};

// Stagger LED ping durations for organic feel
const LED_DURATIONS = RENDER_NODES.map((_, i) => 1.8 + (i % 5) * 0.35);

/**
 * Generate 60 baseline telemetry points covering the last 30 seconds.
 */
const generateInitialBuffer = (): TelemetryPoint[] => {
  const now = Date.now();
  const points: TelemetryPoint[] = [];
  let current = 42.0;

  for (let i = 59; i >= 0; i--) {
    const t = new Date(now - i * 500);
    const timeStr = t.toTimeString().split(" ")[0];
    const walk = (Math.random() - 0.5) * 3.5;
    current = Math.max(35.0, Math.min(65.0, current + walk));
    points.push({
      timestamp: timeStr,
      offset: Math.round(current * 10) / 10,
    });
  }

  return points;
};

export const SyncOffsetChart: React.FC<SyncOffsetChartProps> = ({
  samples,
  thresholdUs = 150.0,
  activeDriftEvents = {},
}) => {
  // ── 60-Sample Rolling Telemetry Buffer ────────────────────────────────
  const [buffer, setBuffer] = useState<TelemetryPoint[]>(generateInitialBuffer);

  // ── Radar sweep beam position (0 to 100%) ────────────────────────────
  const [sweepX, setSweepX] = useState(0);
  const sweepRef = useRef<number | null>(null);
  const sweepDirRef = useRef(1);

  useEffect(() => {
    const animate = () => {
      setSweepX((prev) => {
        const next = prev + sweepDirRef.current * 1.6;
        if (next >= 100) sweepDirRef.current = -1;
        if (next <= 0) sweepDirRef.current = 1;
        return Math.max(0, Math.min(100, next));
      });
      sweepRef.current = requestAnimationFrame(animate);
    };
    sweepRef.current = requestAnimationFrame(animate);
    return () => {
      if (sweepRef.current !== null) cancelAnimationFrame(sweepRef.current);
    };
  }, []);

  // ── 500ms Rolling Update Interval with Realistic Jitter & Drift ──────
  useEffect(() => {
    const timer = setInterval(() => {
      setBuffer((prev) => {
        const lastPoint = prev[prev.length - 1];
        let current = lastPoint ? lastPoint.offset : 42.0;

        // Check for active unresolved drift events
        const activeList = Object.values(activeDriftEvents || {});
        const activeDrift = activeList.find(
          (e) => e.status !== "resolved" && e.status !== "closed"
        );

        // Check recent incoming sample from SSE stream
        const latestSample = samples.length > 0 ? samples[samples.length - 1] : null;
        const isSampleBreached =
          latestSample && latestSample.sync_offset_us > thresholdUs;

        const hasActiveBreach = !!activeDrift || !!isSampleBreached;
        const targetOffset = hasActiveBreach
          ? (activeDrift?.sync_offset_us || latestSample?.sync_offset_us || 185.4)
          : null;

        if (targetOffset !== null) {
          // Sharp interpolation towards the spiked breach value
          const diff = targetOffset - current;
          if (Math.abs(diff) > 2.5) {
            current = current + diff * 0.42 + (Math.random() - 0.5) * 2.0;
          } else {
            current = targetOffset + (Math.random() - 0.5) * 3.0;
          }
        } else {
          // Normal idle or healed state: return to green baseline (< 50µs)
          if (current > 65.0) {
            // Smooth exponential decay downwards after action/healing
            current = current + (42.0 - current) * 0.35 + (Math.random() - 0.5) * 2.0;
          } else {
            // Baseline PTP jitter between 35µs and 65µs (random-walk)
            const walk = (Math.random() - 0.5) * 4.0;
            const pullToCenter = (44.0 - current) * 0.12;
            current = Math.max(35.0, Math.min(65.0, current + walk + pullToCenter));
          }
        }

        const now = new Date();
        const timeStr = now.toTimeString().split(" ")[0];
        const newPoint: TelemetryPoint = {
          timestamp: timeStr,
          offset: Math.round(current * 10) / 10,
        };

        return [...prev.slice(1), newPoint];
      });
    }, 500);

    return () => clearInterval(timer);
  }, [activeDriftEvents, samples, thresholdUs]);

  // ── Derived KPI Metrics ──────────────────────────────────────────────
  const latestPoint = buffer[buffer.length - 1] || { offset: 42.0, timestamp: "" };
  const latestOffset = latestPoint.offset;
  const isLatestBreached = latestOffset > thresholdUs;

  // Maximum scale value: minimum 300µs to accommodate scale lines
  const maxScale = useMemo(() => {
    const highest = Math.max(...buffer.map((p) => p.offset), thresholdUs * 1.2);
    return Math.max(300, Math.ceil(highest / 50) * 50);
  }, [buffer, thresholdUs]);

  // Highest peak point in buffer for breach badge
  const { peakIndex, peakOffset } = useMemo(() => {
    let maxIdx = 0;
    let maxVal = -1;
    buffer.forEach((p, idx) => {
      if (p.offset > maxVal) {
        maxVal = p.offset;
        maxIdx = idx;
      }
    });
    return { peakIndex: maxIdx, peakOffset: maxVal };
  }, [buffer]);

  const hasPeakBreach = peakOffset > thresholdUs;

  // ── SVG Geometry ─────────────────────────────────────────────────────
  const W = 680;
  const H = 230;
  const PL = 50;
  const PR = 16;
  const PT = 24;
  const PB = 28;
  const CW = W - PL - PR;
  const CH = H - PT - PB;

  // Y coordinate of the 150µs breach threshold
  const threshY = PT + CH * (1 - thresholdUs / maxScale);

  // Scaled coordinates for all 60 points
  const points = useMemo(() => {
    return buffer.map((p, i) => {
      const x = PL + (i / Math.max(1, buffer.length - 1)) * CW;
      const y = PT + CH * (1 - Math.min(p.offset, maxScale) / maxScale);
      return { x, y, offset: p.offset, timestamp: p.timestamp };
    });
  }, [buffer, CW, CH, maxScale, PL, PT]);

  // SVG Waveform paths
  const linePath = useMemo(() => {
    return points
      .map((p, i) => `${i === 0 ? "M" : "L"} ${p.x.toFixed(1)},${p.y.toFixed(1)}`)
      .join(" ");
  }, [points]);

  const areaPath = useMemo(() => {
    if (points.length < 2) return "";
    const lastX = points[points.length - 1].x.toFixed(1);
    const firstX = points[0].x.toFixed(1);
    const bottomY = (PT + CH).toFixed(1);
    return `${linePath} L ${lastX},${bottomY} L ${firstX},${bottomY} Z`;
  }, [linePath, points, PT, CH]);

  const sweepAbsPx = PL + (sweepX / 100) * CW;
  const peakPt = points[peakIndex] || points[points.length - 1];

  // Latest node status list from samples
  const latestByNode = useMemo(() => {
    const map = new Map<string, SyncOffsetSample>();
    for (const s of samples) map.set(s.node_id, s);
    return Array.from(map.values());
  }, [samples]);

  const hasClusterBreach =
    isLatestBreached ||
    hasPeakBreach ||
    latestByNode.some((s) => s.sync_offset_us > thresholdUs);

  // Floating badge coordinates
  const badgeW = 168;
  const badgeH = 22;
  const badgeX = Math.max(PL + 6, Math.min(W - PR - badgeW - 6, peakPt.x - badgeW / 2));
  const badgeY = Math.max(PT + 2, peakPt.y - 30);

  return (
    <div
      className="glass-panel min-h-[640px] flex flex-col justify-between"
      style={{
        padding: "20px",
        minHeight: "640px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
      }}
    >
      {/* ── Header ────────────────────────────────────────────────────── */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "14px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Activity size={19} color="var(--color-cyan)" />
          <div>
            <h2 style={{ fontSize: "0.95rem", fontWeight: 700, letterSpacing: "-0.01em" }}>
              Real-Time Frame-Sync Telemetry
            </h2>
            <div
              style={{
                fontSize: "0.68rem",
                color: "var(--text-muted)",
                marginTop: "1px",
                fontFamily: "var(--font-mono)",
              }}
            >
              PROMETHEUS SCRAPE · nDISPLAY SYNC_OFFSET_US (60 SAMPLES)
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {hasClusterBreach ? (
            <span className="badge badge-critical pulse-active">
              <AlertTriangle size={12} /> Threshold Breach ({thresholdUs}µs)
            </span>
          ) : (
            <span className="badge badge-nominal">
              <ShieldCheck size={12} /> Frame-Sync Locked · 60.000 Hz
            </span>
          )}
        </div>
      </div>

      {/* ── 2-Column Section: Waveform (Left 3 cols) + HUD KPI Sidebar (Right 1 col) ── */}
      <div
        style={{
          display: "flex",
          gap: "16px",
          alignItems: "stretch",
          marginBottom: "14px",
        }}
      >
        {/* Left: SVG Telemetry Waveform Viewport */}
        <div
          style={{
            flex: 1,
            minWidth: 0,
            height: "260px",
            position: "relative",
            background: "rgba(6,182,212,0.02)",
            border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: "10px",
            overflow: "hidden",
          }}
        >
          <svg
            viewBox={`0 0 ${W} ${H}`}
            preserveAspectRatio="none"
            style={{ width: "100%", height: "100%", display: "block" }}
          >
            <defs>
              {/* Dynamic Waveform Area Gradient */}
              <linearGradient id="offsetGradient" x1="0" y1="0" x2="0" y2="1">
                <stop
                  offset="0%"
                  stopColor={
                    isLatestBreached
                      ? "rgba(239,68,68,0.36)"
                      : "rgba(6,182,212,0.28)"
                  }
                />
                <stop
                  offset="60%"
                  stopColor={
                    isLatestBreached
                      ? "rgba(239,68,68,0.09)"
                      : "rgba(6,182,212,0.06)"
                  }
                />
                <stop offset="100%" stopColor="rgba(0,0,0,0)" />
              </linearGradient>

              {/* Hazard hatch pattern above threshold */}
              <pattern
                id="hazardHatch"
                patternUnits="userSpaceOnUse"
                width="8"
                height="8"
                patternTransform="rotate(45)"
              >
                <line
                  x1="0"
                  y1="0"
                  x2="0"
                  y2="8"
                  stroke="rgba(239,68,68,0.18)"
                  strokeWidth="2"
                />
              </pattern>

              {/* Radar sweep beam gradient */}
              <linearGradient id="sweepGrad" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="rgba(6,182,212,0)" />
                <stop offset="40%" stopColor="rgba(6,182,212,0.08)" />
                <stop offset="70%" stopColor="rgba(6,182,212,0.22)" />
                <stop offset="100%" stopColor="rgba(6,182,212,0.55)" />
              </linearGradient>

              {/* Chart clipping perimeter */}
              <clipPath id="waveformClip">
                <rect x={PL} y={PT} width={CW} height={CH} rx={4} />
              </clipPath>
            </defs>

            {/* Background grid box */}
            <rect
              x={PL}
              y={PT}
              width={CW}
              height={CH}
              fill="rgba(6,182,212,0.015)"
              rx={4}
            />

            {/* Y-Axis Grid Lines: 0, 50, 100, 150, 200, 300 µs */}
            {[0, 50, 100, 150, 200, 300].map((val) => {
              if (val > maxScale) return null;
              const y = PT + CH * (1 - val / maxScale);
              return (
                <g key={`grid-y-${val}`}>
                  <line
                    x1={PL}
                    y1={y}
                    x2={PL + CW}
                    y2={y}
                    stroke="rgba(255,255,255,0.05)"
                    strokeDasharray="3 3"
                  />
                  <text
                    x={PL - 8}
                    y={y + 3.5}
                    fill="var(--text-muted)"
                    fontSize="9"
                    fontFamily="var(--font-mono)"
                    textAnchor="end"
                  >
                    {val}µs
                  </text>
                </g>
              );
            })}

            {/* Hazard zone above threshold */}
            <rect
              x={PL}
              y={PT}
              width={CW}
              height={Math.max(0, threshY - PT)}
              fill="url(#hazardHatch)"
              clipPath="url(#waveformClip)"
            />

            {/* Threshold line glow aura */}
            <line
              x1={PL}
              y1={threshY}
              x2={PL + CW}
              y2={threshY}
              stroke="rgba(239,68,68,0.22)"
              strokeWidth={8}
            />

            {/* Red Dashed Threshold Line */}
            <line
              x1={PL}
              y1={threshY}
              x2={PL + CW}
              y2={threshY}
              stroke="#ef4444"
              strokeWidth={1.5}
              strokeDasharray="5 4"
            />
            <text
              x={PL + CW - 8}
              y={threshY - 6}
              fill="#ef4444"
              fontSize="9.5"
              fontWeight="700"
              fontFamily="var(--font-mono)"
              textAnchor="end"
              letterSpacing="0.04em"
            >
              150µs THRESHOLD BREACH
            </text>

            {/* ── Area Gradient Fill Underneath ───────────────────────── */}
            <path
              d={areaPath}
              fill="url(#offsetGradient)"
              clipPath="url(#waveformClip)"
            />

            {/* ── Glowing Stroke Waveform ──────────────────────────────── */}
            {/* Outer soft glow layer */}
            <path
              d={linePath}
              fill="none"
              stroke={isLatestBreached ? "#ef4444" : "#06b6d4"}
              strokeWidth={7}
              strokeOpacity={isLatestBreached ? 0.35 : 0.22}
              strokeLinecap="round"
              strokeLinejoin="round"
              clipPath="url(#waveformClip)"
            />
            {/* Sharp crisp inner stroke */}
            <path
              d={linePath}
              fill="none"
              stroke={isLatestBreached ? "#ef4444" : "#06b6d4"}
              strokeWidth={2.5}
              strokeLinecap="round"
              strokeLinejoin="round"
              clipPath="url(#waveformClip)"
            />

            {/* ── Live Endpoint Dot ────────────────────────────────────── */}
            {points.length > 0 && (
              <g>
                <circle
                  cx={points[points.length - 1].x}
                  cy={points[points.length - 1].y}
                  r={isLatestBreached ? 6 : 5}
                  fill={isLatestBreached ? "#ef4444" : "#06b6d4"}
                  stroke="#070A11"
                  strokeWidth={2}
                />
                <circle
                  cx={points[points.length - 1].x}
                  cy={points[points.length - 1].y}
                  r={isLatestBreached ? 12 : 9}
                  fill="none"
                  stroke={isLatestBreached ? "#ef4444" : "#06b6d4"}
                  strokeWidth={1.5}
                  opacity={0.65}
                  className="pulse-active"
                />
              </g>
            )}

            {/* ── Peak Marker Dot and Floating Breach Badge ─────────────── */}
            {hasPeakBreach && (
              <g>
                {/* Pointer guide from peak to badge */}
                <line
                  x1={peakPt.x}
                  y1={peakPt.y}
                  x2={peakPt.x}
                  y2={badgeY + badgeH}
                  stroke="#ef4444"
                  strokeWidth={1}
                  strokeDasharray="2 2"
                  opacity={0.6}
                />
                {/* Glowing marker dot at the highest peak */}
                <circle
                  cx={peakPt.x}
                  cy={peakPt.y}
                  r={5}
                  fill="#ef4444"
                  stroke="#ffffff"
                  strokeWidth={1.5}
                />
                <circle
                  cx={peakPt.x}
                  cy={peakPt.y}
                  r={11}
                  fill="none"
                  stroke="#ef4444"
                  strokeWidth={1.5}
                  className="pulse-active"
                />

                {/* Floating Badge above Peak */}
                <rect
                  x={badgeX}
                  y={badgeY}
                  width={badgeW}
                  height={badgeH}
                  rx={4}
                  fill="rgba(239,68,68,0.94)"
                  stroke="#ef4444"
                  strokeWidth={1}
                />
                <text
                  x={badgeX + badgeW / 2}
                  y={badgeY + 14.5}
                  fill="#ffffff"
                  fontSize="9"
                  fontWeight="700"
                  fontFamily="var(--font-mono)"
                  textAnchor="middle"
                  letterSpacing="0.04em"
                >
                  ⚠ 150µs THRESHOLD BREACH
                </text>
              </g>
            )}

            {/* ── Radar Sweep Beam ─────────────────────────────────────── */}
            <g clipPath="url(#waveformClip)">
              <rect
                x={sweepAbsPx - 26}
                y={PT}
                width={32}
                height={CH}
                fill="url(#sweepGrad)"
              />
              <line
                x1={sweepAbsPx}
                y1={PT}
                x2={sweepAbsPx}
                y2={PT + CH}
                stroke="rgba(6,182,212,0.65)"
                strokeWidth={1.5}
              />
            </g>

            {/* ── Rolling X-Axis Time Labels (HH:MM:SS) ────────────────── */}
            {[0, 15, 30, 45, points.length - 1].map((idx) => {
              const p = points[idx];
              if (!p) return null;
              return (
                <text
                  key={`time-label-${idx}`}
                  x={p.x}
                  y={H - 8}
                  fill="var(--text-muted)"
                  fontSize="8.5"
                  fontFamily="var(--font-mono)"
                  textAnchor={
                    idx === 0 ? "start" : idx === points.length - 1 ? "end" : "middle"
                  }
                >
                  {p.timestamp}
                </text>
              );
            })}
          </svg>
        </div>

        {/* Right: Dedicated HUD KPI Stats Sidebar */}
        <div
          style={{
            width: "182px",
            flexShrink: 0,
            background: isLatestBreached
              ? "rgba(239, 68, 68, 0.06)"
              : "rgba(6, 182, 212, 0.04)",
            border: isLatestBreached
              ? "1px solid rgba(239, 68, 68, 0.40)"
              : "1px solid rgba(6, 182, 212, 0.22)",
            borderRadius: "10px",
            padding: "14px 12px",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            boxShadow: isLatestBreached
              ? "0 0 20px rgba(239, 68, 68, 0.12)"
              : "0 0 16px rgba(6, 182, 212, 0.05)",
            transition: "all 0.3s ease",
          }}
        >
          {/* Header */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <Radio size={12} color="var(--color-cyan)" />
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "0.62rem",
                  fontWeight: 800,
                  color: "var(--text-muted)",
                  letterSpacing: "0.10em",
                }}
              >
                HUD KPI STATS
              </span>
            </div>
            <div
              style={{
                width: "7px",
                height: "7px",
                borderRadius: "50%",
                background: isLatestBreached
                  ? "var(--color-rose)"
                  : "var(--color-emerald)",
                boxShadow: `0 0 8px ${isLatestBreached ? "var(--color-rose)" : "var(--color-emerald)"}`,
              }}
              className="pulse-active"
            />
          </div>

          {/* KPI 1: Current Offset Big Bold Display */}
          <div style={{ marginTop: "4px", marginBottom: "4px" }}>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.60rem",
                color: "var(--text-muted)",
                letterSpacing: "0.08em",
                marginBottom: "2px",
                textTransform: "uppercase",
              }}
            >
              Current Offset
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "1.75rem",
                fontWeight: 900,
                color: isLatestBreached ? "#ef4444" : "#10b981",
                lineHeight: 1.05,
                letterSpacing: "-0.03em",
                filter: `drop-shadow(0 0 10px ${
                  isLatestBreached
                    ? "rgba(239,68,68,0.6)"
                    : "rgba(16,185,129,0.4)"
                })`,
              }}
            >
              {latestOffset.toFixed(1)}{" "}
              <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>µs</span>
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.64rem",
                color: "var(--text-muted)",
                marginTop: "4px",
              }}
            >
              Target:{" "}
              <span style={{ color: "var(--color-emerald)", fontWeight: 600 }}>
                ≤ 50.0 µs
              </span>
            </div>
            <div
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.60rem",
                color: isLatestBreached
                  ? "var(--color-rose)"
                  : "rgba(244,63,94,0.7)",
                marginTop: "1px",
              }}
            >
              Limit: {thresholdUs.toFixed(0)} µs Max
            </div>
          </div>

          {/* KPI 2: Pill Status Badge */}
          <div>
            {isLatestBreached ? (
              <div
                className="badge badge-critical pulse-active"
                style={{
                  width: "100%",
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  gap: "6px",
                  padding: "7px 10px",
                  fontSize: "0.76rem",
                  fontWeight: 800,
                  fontFamily: "var(--font-mono)",
                  letterSpacing: "0.08em",
                  borderRadius: "6px",
                  background: "rgba(239, 68, 68, 0.22)",
                  borderColor: "rgba(239, 68, 68, 0.60)",
                  color: "#fca5a5",
                }}
              >
                <AlertTriangle size={13} color="#ef4444" />
                BREACH
              </div>
            ) : (
              <div
                className="badge badge-nominal"
                style={{
                  width: "100%",
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  gap: "6px",
                  padding: "7px 10px",
                  fontSize: "0.76rem",
                  fontWeight: 800,
                  fontFamily: "var(--font-mono)",
                  letterSpacing: "0.08em",
                  borderRadius: "6px",
                  color: "#10b981",
                  borderColor: "rgba(16, 185, 129, 0.45)",
                  background: "rgba(16, 185, 129, 0.12)",
                }}
              >
                <ShieldCheck size={13} color="#10b981" />
                LOCKED
              </div>
            )}
          </div>

          {/* Secondary Telemetry Details */}
          <div
            style={{
              borderTop: "1px solid rgba(255, 255, 255, 0.08)",
              paddingTop: "10px",
              display: "flex",
              flexDirection: "column",
              gap: "5px",
              fontFamily: "var(--font-mono)",
              fontSize: "0.62rem",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>PTP Clock:</span>
              <span style={{ color: "var(--color-cyan)", fontWeight: 700 }}>
                Stratum-1
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Rate:</span>
              <span style={{ color: "var(--text-secondary)", fontWeight: 600 }}>
                60.000 Hz
              </span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <span style={{ color: "var(--text-muted)" }}>Jitter Var:</span>
              <span
                style={{
                  color: isLatestBreached
                    ? "var(--color-rose)"
                    : "var(--color-emerald)",
                  fontWeight: 700,
                }}
              >
                ±{(Math.abs(latestOffset - 44) * 0.05 + 1.2).toFixed(1)} µs
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* ── Cluster Health Section: 16-Node Status Matrix ─────────────────── */}
      <div
        style={{
          marginTop: "10px",
          paddingTop: "12px",
          borderTop: "1px solid var(--border-subtle)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "8px",
          }}
        >
          <div
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.68rem",
              fontWeight: 700,
              color: "var(--text-muted)",
              letterSpacing: "0.10em",
              textTransform: "uppercase",
            }}
          >
            nDisplay Cluster · Frame-Lock Status Matrix
          </div>
          <span
            className={`badge ${
              hasClusterBreach ? "badge-critical pulse-active" : "badge-nominal"
            }`}
            style={{ fontFamily: "var(--font-mono)", fontSize: "0.62rem" }}
          >
            {hasClusterBreach ? "SYNC BREACH ACTIVE" : "16/16 Nodes PTP-Synced"}
          </span>
        </div>

        {/* 16-Node Matrix: Always rendered in dedicated 8-col grid */}
        <div
          className="grid grid-cols-8 gap-2.5 py-2"
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(8, 1fr)",
            gap: "10px",
            paddingTop: "8px",
            paddingBottom: "8px",
          }}
        >
          {RENDER_NODES.map((name, i) => {
            const nodeIdLower = name.toLowerCase();
            const sample = latestByNode.find(
              (s) => s.node_id.toLowerCase() === nodeIdLower
            );
            const activeEvent = Object.values(activeDriftEvents || {}).find(
              (e) => e.node_id.toLowerCase() === nodeIdLower && e.status !== "resolved"
            );

            const isBreached =
              (sample && sample.sync_offset_us > thresholdUs) ||
              (activeEvent && activeEvent.sync_offset_us > thresholdUs);

            const nodeColor = isBreached
              ? "var(--color-rose)"
              : sample
                ? NODE_COLORS[sample.node_id] || "var(--color-cyan)"
                : "var(--color-emerald)";

            const displayOffset = isBreached
              ? (activeEvent?.sync_offset_us || sample?.sync_offset_us || latestOffset)
              : sample?.sync_offset_us;

            return (
              <div
                key={name}
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: "4px",
                  padding: "7px 4px",
                  background: isBreached
                    ? "rgba(244,63,94,0.12)"
                    : sample
                      ? "rgba(6,182,212,0.07)"
                      : "rgba(16,185,129,0.04)",
                  border: isBreached
                    ? "1px solid rgba(244,63,94,0.50)"
                    : sample
                      ? "1px solid rgba(6,182,212,0.30)"
                      : "1px solid rgba(16,185,129,0.14)",
                  borderRadius: "8px",
                  position: "relative",
                  overflow: "hidden",
                  transition: "all 0.25s ease",
                }}
              >
                {/* LED dot with pulse ring */}
                <div style={{ position: "relative", width: "12px", height: "12px" }}>
                  <div
                    style={{
                      position: "absolute",
                      inset: 0,
                      borderRadius: "50%",
                      background: nodeColor,
                      opacity: 0,
                      animationDelay: `${(i * 0.17) % LED_DURATIONS[i]}s`,
                      animationDuration: `${isBreached ? 0.9 : LED_DURATIONS[i]}s`,
                    }}
                    className={isBreached ? "pulse-active" : "led-ping-ring"}
                  />
                  <div
                    style={{
                      position: "absolute",
                      inset: "2px",
                      borderRadius: "50%",
                      background: nodeColor,
                      boxShadow: `0 0 6px ${nodeColor}`,
                      animationDelay: `${(i * 0.19) % 2.5}s`,
                      animationDuration: `${isBreached ? 0.9 : LED_DURATIONS[i]}s`,
                    }}
                    className="pulse-active"
                  />
                </div>
                <span
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.58rem",
                    color: nodeColor,
                    fontWeight: 800,
                    textAlign: "center",
                    letterSpacing: "0.02em",
                  }}
                >
                  {name.replace("Render-", "R")}
                </span>
                {displayOffset !== undefined && (
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.50rem",
                      color: isBreached ? "var(--color-rose)" : "var(--color-cyan)",
                      fontWeight: 700,
                    }}
                  >
                    {displayOffset.toFixed(0)}µs
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Active drift telemetry badge strip */}
        {latestByNode.length > 0 && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: "8px",
              marginTop: "4px",
              marginBottom: "8px",
            }}
          >
            {latestByNode.map((sample) => {
              const isBreach = sample.sync_offset_us > thresholdUs;
              const badgeColor = isBreach
                ? "var(--color-rose)"
                : NODE_COLORS[sample.node_id] || "var(--color-cyan)";
              return (
                <div
                  key={sample.node_id}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "5px 11px",
                    background: isBreach
                      ? "rgba(244,63,94,0.12)"
                      : "rgba(6,182,212,0.08)",
                    borderRadius: "6px",
                    border: isBreach
                      ? "1px solid rgba(244,63,94,0.40)"
                      : "1px solid rgba(6,182,212,0.25)",
                  }}
                >
                  <div
                    style={{
                      width: "7px",
                      height: "7px",
                      borderRadius: "50%",
                      background: badgeColor,
                      boxShadow: `0 0 6px ${badgeColor}`,
                    }}
                    className={isBreach ? "pulse-active" : ""}
                  />
                  <span
                    style={{
                      fontSize: "0.74rem",
                      fontWeight: 700,
                      fontFamily: "var(--font-mono)",
                      color: "var(--text-primary)",
                    }}
                  >
                    {sample.node_id}
                  </span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.74rem",
                      color: isBreach ? "var(--color-rose)" : "var(--color-cyan)",
                      fontWeight: 800,
                    }}
                  >
                    [{sample.sync_offset_us.toFixed(1)} µs]
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {/* Status bar */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "8px 12px",
            background: hasClusterBreach
              ? "rgba(244,63,94,0.08)"
              : "rgba(16,185,129,0.05)",
            border: hasClusterBreach
              ? "1px solid rgba(244,63,94,0.25)"
              : "1px solid rgba(16,185,129,0.15)",
            borderRadius: "8px",
          }}
        >
          <div
            style={{
              width: "6px",
              height: "6px",
              borderRadius: "50%",
              background: hasClusterBreach
                ? "var(--color-rose)"
                : "var(--color-emerald)",
              boxShadow: `0 0 8px ${
                hasClusterBreach ? "var(--color-rose)" : "var(--color-emerald)"
              }`,
            }}
            className="pulse-active"
          />
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.68rem",
              color: hasClusterBreach
                ? "var(--color-rose)"
                : "var(--color-emerald)",
              fontWeight: 700,
              letterSpacing: "0.06em",
            }}
          >
            {hasClusterBreach
              ? `CRITICAL DRIFT DETECTED (${thresholdUs.toFixed(0)}µs THRESHOLD BREACHED) · ADK WORKFLOW ACTIVE`
              : "ALL 16 NODES FRAME-LOCKED · 0 DRIFT DETECTED · STREAM WATCH ACTIVE"}
          </span>
        </div>
      </div>
    </div>
  );
};
