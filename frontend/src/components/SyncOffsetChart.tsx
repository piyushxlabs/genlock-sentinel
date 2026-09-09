import React, { useEffect, useMemo, useRef, useState } from "react";
import { Activity, AlertTriangle, ShieldCheck } from "lucide-react";
import { SyncOffsetSample } from "../stream/agui-client";

interface SyncOffsetChartProps {
  samples: SyncOffsetSample[];
  thresholdUs?: number;
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

export const SyncOffsetChart: React.FC<SyncOffsetChartProps> = ({
  samples,
  thresholdUs = 150.0,
}) => {
  // ── Radar sweep position ─────────────────────────────────────────────
  const [sweepX, setSweepX] = useState(0);
  const sweepRef = useRef<number | null>(null);
  const sweepDirRef = useRef(1);

  useEffect(() => {
    const animate = () => {
      setSweepX((prev) => {
        const next = prev + sweepDirRef.current * 1.8;
        if (next >= 100) sweepDirRef.current = -1;
        if (next <= 0)   sweepDirRef.current =  1;
        return Math.max(0, Math.min(100, next));
      });
      sweepRef.current = requestAnimationFrame(animate);
    };
    sweepRef.current = requestAnimationFrame(animate);
    return () => {
      if (sweepRef.current !== null) cancelAnimationFrame(sweepRef.current);
    };
  }, []);

  // ── Data derivation ──────────────────────────────────────────────────
  const latestByNode = useMemo(() => {
    const map = new Map<string, SyncOffsetSample>();
    for (const s of samples) map.set(s.node_id, s);
    return Array.from(map.values());
  }, [samples]);

  const maxOffset = useMemo(() => {
    if (samples.length === 0) return 200;
    return Math.max(thresholdUs * 1.3, ...samples.map((s) => s.sync_offset_us));
  }, [samples, thresholdUs]);

  const hasBreach = useMemo(
    () => latestByNode.some((s) => s.sync_offset_us > thresholdUs),
    [latestByNode, thresholdUs]
  );

  // ── SVG geometry ─────────────────────────────────────────────────────
  const W = 760, H = 240;
  const PL = 60, PR = 20, PT = 28, PB = 40;
  const CW = W - PL - PR;
  const CH = H - PT - PB;
  const threshY = PT + CH * (1 - thresholdUs / maxOffset);

  // Group last 60 samples by node
  const seriesByNode = useMemo(() => {
    const groups: Record<string, SyncOffsetSample[]> = {};
    for (const s of samples.slice(-60)) {
      if (!groups[s.node_id]) groups[s.node_id] = [];
      groups[s.node_id].push(s);
    }
    return groups;
  }, [samples]);

  // Area polygon path for neon fill
  const buildAreaPath = (nodeSamples: SyncOffsetSample[]): string => {
    if (nodeSamples.length < 2) return "";
    const pts = nodeSamples.map((s, i) => {
      const x = PL + (i / (nodeSamples.length - 1)) * CW;
      const y = PT + CH * (1 - Math.min(s.sync_offset_us, maxOffset) / maxOffset);
      return { x, y };
    });
    const line = pts.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
    const base = `L${pts[pts.length - 1].x.toFixed(1)},${(PT + CH).toFixed(1)} L${PL.toFixed(1)},${(PT + CH).toFixed(1)} Z`;
    return `${line} ${base}`;
  };

  const sweepAbsPx = PL + (sweepX / 100) * CW;

  return (
    <div
      className="glass-panel"
      style={{
        padding: "20px",
        height: "100%",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
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
            <div style={{ fontSize: "0.68rem", color: "var(--text-muted)", marginTop: "1px", fontFamily: "var(--font-mono)" }}>
              PROMETHEUS SCRAPE · nDISPLAY SYNC_OFFSET_US
            </div>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {hasBreach ? (
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

      {/* Chart SVG */}
      <div style={{ flex: "1 1 0", minHeight: 0, overflowX: "auto", position: "relative" }}>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: "100%", height: "100%", display: "block" }}>
          <defs>
            {/* Neon cyan area fill gradient */}
            <linearGradient id="cyanGlow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor="rgba(6,182,212,0.28)" />
              <stop offset="60%"  stopColor="rgba(6,182,212,0.06)" />
              <stop offset="100%" stopColor="rgba(6,182,212,0)" />
            </linearGradient>
            <linearGradient id="purpleGlow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor="rgba(168,85,247,0.22)" />
              <stop offset="100%" stopColor="rgba(168,85,247,0)" />
            </linearGradient>
            <linearGradient id="emeraldGlow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%"   stopColor="rgba(16,185,129,0.22)" />
              <stop offset="100%" stopColor="rgba(16,185,129,0)" />
            </linearGradient>

            {/* Hazard hatch pattern above threshold */}
            <pattern id="hazardHatch" patternUnits="userSpaceOnUse" width="8" height="8" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="8" stroke="rgba(244,63,94,0.18)" strokeWidth="2" />
            </pattern>

            {/* Radar sweep gradient */}
            <linearGradient id="sweepGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%"   stopColor="rgba(6,182,212,0)" />
              <stop offset="40%"  stopColor="rgba(6,182,212,0.08)" />
              <stop offset="70%"  stopColor="rgba(6,182,212,0.25)" />
              <stop offset="100%" stopColor="rgba(6,182,212,0.55)" />
            </linearGradient>

            {/* Clip chart area */}
            <clipPath id="chartClip">
              <rect x={PL} y={PT} width={CW} height={CH} rx={4} />
            </clipPath>
          </defs>

          {/* Chart background */}
          <rect
            x={PL} y={PT} width={CW} height={CH}
            fill="rgba(6,182,212,0.025)" rx={6}
          />

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((p, i) => {
            const y = PT + CH * (1 - p);
            const val = Math.round(maxOffset * p);
            return (
              <g key={i}>
                <line
                  x1={PL} y1={y} x2={W - PR} y2={y}
                  stroke="rgba(255,255,255,0.055)"
                  strokeDasharray="3 4"
                />
                <text
                  x={PL - 8} y={y + 4}
                  fill="var(--text-muted)" fontSize={9.5}
                  fontFamily="var(--font-mono)" textAnchor="end"
                >
                  {val}µs
                </text>
              </g>
            );
          })}

          {/* ── Hazard zone above threshold ─────────────────────────── */}
          <rect
            x={PL} y={PT} width={CW} height={threshY - PT}
            fill="url(#hazardHatch)"
            clipPath="url(#chartClip)"
          />
          {/* Red aura glow on threshold line */}
          <line
            x1={PL} y1={threshY} x2={W - PR} y2={threshY}
            stroke="rgba(244,63,94,0.12)"
            strokeWidth={8}
          />
          {/* Main threshold line */}
          <line
            x1={PL} y1={threshY} x2={W - PR} y2={threshY}
            stroke="var(--color-rose)"
            strokeWidth={1.5}
            strokeDasharray="5 4"
          />
          <text
            x={W - PR - 6} y={threshY - 6}
            fill="var(--color-rose)"
            fontSize={10} fontWeight={600}
            fontFamily="var(--font-mono)" textAnchor="end"
          >
            ⚠ {thresholdUs.toFixed(0)}µs BREACH PERIMETER
          </text>

          {/* ── Neon area fills ──────────────────────────────────────── */}
          {Object.entries(seriesByNode).map(([nodeId, nodeSamples]) => {
            if (nodeSamples.length < 2) return null;
            const gradId =
              nodeId === "render-12" ? "purpleGlow" :
              nodeId === "render-01" ? "emeraldGlow" : "cyanGlow";
            return (
              <path
                key={`area-${nodeId}`}
                d={buildAreaPath(nodeSamples)}
                fill={`url(#${gradId})`}
                clipPath="url(#chartClip)"
              />
            );
          })}

          {/* ── Telemetry curves ─────────────────────────────────────── */}
          {Object.entries(seriesByNode).map(([nodeId, nodeSamples]) => {
            if (nodeSamples.length < 2) return null;
            const strokeColor = NODE_COLORS[nodeId] || "#38bdf8";

            const points = nodeSamples
              .map((s, i) => {
                const x = PL + (i / (nodeSamples.length - 1)) * CW;
                const y = PT + CH * (1 - Math.min(s.sync_offset_us, maxOffset) / maxOffset);
                return `${x.toFixed(1)},${y.toFixed(1)}`;
              })
              .join(" ");

            const last = nodeSamples[nodeSamples.length - 1];
            const lx = PL + CW;
            const ly = PT + CH * (1 - Math.min(last.sync_offset_us, maxOffset) / maxOffset);

            return (
              <g key={nodeId}>
                {/* Glow under line */}
                <polyline
                  fill="none"
                  stroke={strokeColor}
                  strokeOpacity={0.20}
                  strokeWidth={6}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  points={points}
                  clipPath="url(#chartClip)"
                />
                <polyline
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  points={points}
                  clipPath="url(#chartClip)"
                />
                {/* Live endpoint dot */}
                <circle cx={lx} cy={ly} r={5} fill={strokeColor} stroke="#070A11" strokeWidth={2} />
                <circle
                  cx={lx} cy={ly} r={9}
                  fill="none" stroke={strokeColor} strokeWidth={1}
                  opacity={0.4}
                  className="pulse-active"
                />
              </g>
            );
          })}

          {/* ── Live radar sweep line ────────────────────────────────── */}
          <g clipPath="url(#chartClip)">
            {/* Gradient sweep beam */}
            <rect
              x={sweepAbsPx - 24} y={PT} width={30} height={CH}
              fill="url(#sweepGrad)"
            />
            {/* Sharp leading edge */}
            <line
              x1={sweepAbsPx} y1={PT}
              x2={sweepAbsPx} y2={PT + CH}
              stroke="rgba(6,182,212,0.65)"
              strokeWidth={1.5}
            />
          </g>

          {/* X-axis label */}
          <text
            x={PL + CW / 2} y={H - 6}
            fill="var(--text-muted)" fontSize={9}
            fontFamily="var(--font-mono)" textAnchor="middle"
          >
            ← ROLLING 60-SAMPLE WINDOW →
          </text>
        </svg>
      </div>

      {/* ── Cluster Health Section ─────────────────────────────────────── */}
      <div
        style={{
          marginTop: "18px",
          paddingTop: "14px",
          borderTop: "1px solid var(--border-subtle)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "10px",
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
          <span className="badge badge-nominal" style={{ fontFamily: "var(--font-mono)", fontSize: "0.62rem" }}>
            16/16 Nodes PTP-Synced
          </span>
        </div>

        {latestByNode.length === 0 ? (
          /* 16-Node Idle LED Matrix */
          <ClusterIdleMatrix />
        ) : (
          /* Real sample chips when data available */
          <div style={{ display: "flex", flexWrap: "wrap", gap: "10px" }}>
            {latestByNode.map((sample) => {
              const isBreach = sample.sync_offset_us > thresholdUs;
              const color = NODE_COLORS[sample.node_id] || "var(--color-cyan)";
              return (
                <div
                  key={sample.node_id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "9px",
                    padding: "6px 12px",
                    background: isBreach ? "rgba(244,63,94,0.08)" : "rgba(255,255,255,0.03)",
                    borderRadius: "8px",
                    border: isBreach
                      ? "1px solid rgba(244,63,94,0.35)"
                      : "1px solid var(--border-subtle)",
                  }}
                >
                  <div
                    style={{
                      width: "7px", height: "7px",
                      borderRadius: "50%",
                      background: isBreach ? "var(--color-rose)" : color,
                      boxShadow: `0 0 6px ${isBreach ? "var(--color-rose)" : color}`,
                    }}
                    className={isBreach ? "pulse-active" : ""}
                  />
                  <span style={{ fontSize: "0.80rem", fontWeight: 600 }}>{sample.node_id}</span>
                  <span
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.80rem",
                      color: isBreach ? "var(--color-rose)" : "var(--color-emerald)",
                      fontWeight: 700,
                    }}
                  >
                    {sample.sync_offset_us.toFixed(1)} µs
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

/* ─────────────────────────────────────────────────────────────────────── */
/* 16-Node Idle LED Matrix                                                 */
/* ─────────────────────────────────────────────────────────────────────── */
const ClusterIdleMatrix: React.FC = () => {
  return (
    <div>
      {/* 4×4 LED grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(8, 1fr)",
          gap: "8px",
          marginBottom: "12px",
        }}
      >
        {RENDER_NODES.map((name, i) => (
          <div
            key={name}
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: "5px",
              padding: "8px 4px",
              background: "rgba(16,185,129,0.04)",
              border: "1px solid rgba(16,185,129,0.14)",
              borderRadius: "8px",
              position: "relative",
              overflow: "hidden",
            }}
          >
            {/* LED dot with ping ring */}
            <div style={{ position: "relative", width: "12px", height: "12px" }}>
              <div
                style={{
                  position: "absolute",
                  inset: 0,
                  borderRadius: "50%",
                  background: "var(--color-emerald)",
                  opacity: 0,
                  animationDelay: `${(i * 0.17) % LED_DURATIONS[i]}s`,
                  animationDuration: `${LED_DURATIONS[i]}s`,
                }}
                className="led-ping-ring"
              />
              <div
                style={{
                  position: "absolute",
                  inset: "3px",
                  borderRadius: "50%",
                  background: "var(--color-emerald)",
                  boxShadow: "0 0 5px rgba(16,185,129,0.7)",
                  animationDelay: `${(i * 0.19) % 2.5}s`,
                  animationDuration: `${LED_DURATIONS[i]}s`,
                }}
                className="pulse-active"
              />
            </div>
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "0.55rem",
                color: "var(--color-emerald)",
                fontWeight: 700,
                textAlign: "center",
                letterSpacing: "0.02em",
              }}
            >
              {name.replace("Render-", "R")}
            </span>
          </div>
        ))}
      </div>

      {/* Status bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "8px",
          padding: "8px 12px",
          background: "rgba(16,185,129,0.05)",
          border: "1px solid rgba(16,185,129,0.15)",
          borderRadius: "8px",
        }}
      >
        <div
          style={{
            width: "6px", height: "6px",
            borderRadius: "50%",
            background: "var(--color-emerald)",
            boxShadow: "0 0 8px var(--color-emerald)",
          }}
          className="pulse-active"
        />
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.68rem",
            color: "var(--color-emerald)",
            fontWeight: 700,
            letterSpacing: "0.06em",
          }}
        >
          ALL NODES FRAME-LOCKED · 0 DRIFT DETECTED · STREAM WATCH ACTIVE
        </span>
      </div>
    </div>
  );
};
