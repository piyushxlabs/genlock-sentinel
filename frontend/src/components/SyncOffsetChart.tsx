import React, { useMemo } from "react";
import { Activity, AlertTriangle, ShieldCheck } from "lucide-react";
import { SyncOffsetSample } from "../stream/agui-client";

interface SyncOffsetChartProps {
  samples: SyncOffsetSample[];
  thresholdUs?: number;
}

export const SyncOffsetChart: React.FC<SyncOffsetChartProps> = ({
  samples,
  thresholdUs = 150.0,
}) => {
  // Extract latest sample per node
  const latestByNode = useMemo(() => {
    const map = new Map<string, SyncOffsetSample>();
    for (const s of samples) {
      map.set(s.node_id, s);
    }
    return Array.from(map.values());
  }, [samples]);

  // Overall maximum offset
  const maxOffset = useMemo(() => {
    if (samples.length === 0) return 200;
    return Math.max(
      thresholdUs * 1.3,
      ...samples.map((s) => s.sync_offset_us)
    );
  }, [samples, thresholdUs]);

  const hasBreach = useMemo(() => {
    return latestByNode.some((s) => s.sync_offset_us > thresholdUs);
  }, [latestByNode, thresholdUs]);

  // SVG Chart Geometry
  const width = 760;
  const height = 240;
  const padLeft = 60;
  const padRight = 20;
  const padTop = 30;
  const padBottom = 40;

  const chartWidth = width - padLeft - padRight;
  const chartHeight = height - padTop - padBottom;

  const thresholdY = padTop + chartHeight * (1 - thresholdUs / maxOffset);

  // Group last 30 samples by node for polyline rendering
  const seriesByNode = useMemo(() => {
    const groups: Record<string, SyncOffsetSample[]> = {};
    for (const s of samples.slice(-60)) {
      if (!groups[s.node_id]) groups[s.node_id] = [];
      groups[s.node_id].push(s);
    }
    return groups;
  }, [samples]);

  const nodeColors: Record<string, string> = {
    "render-07": "#06b6d4",
    "render-12": "#a855f7",
    "render-01": "#10b981",
  };

  return (
    <div className="glass-panel" style={{ padding: "20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Activity size={20} color="var(--color-cyan)" />
          <h2 style={{ fontSize: "1.05rem", fontWeight: 700, letterSpacing: "-0.01em" }}>
            Real-Time Frame-Sync Telemetry (Prometheus)
          </h2>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {hasBreach ? (
            <span className="badge badge-critical pulse-active">
              <AlertTriangle size={13} /> Threshold Breach ({thresholdUs}µs)
            </span>
          ) : (
            <span className="badge badge-nominal">
              <ShieldCheck size={13} /> Frame-Sync Locked (60.000 Hz)
            </span>
          )}
        </div>
      </div>

      {/* Chart SVG */}
      <div style={{ width: "100%", overflowX: "auto" }}>
        <svg
          viewBox={`0 0 ${width} ${height}`}
          style={{ width: "100%", height: "auto", display: "block" }}
        >
          <defs>
            <linearGradient id="grid-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgba(255,255,255,0.04)" />
              <stop offset="100%" stopColor="rgba(255,255,255,0.01)" />
            </linearGradient>
          </defs>

          {/* Background area */}
          <rect
            x={padLeft}
            y={padTop}
            width={chartWidth}
            height={chartHeight}
            fill="url(#grid-grad)"
            rx={6}
          />

          {/* Grid lines */}
          {[0, 0.25, 0.5, 0.75, 1].map((p, idx) => {
            const y = padTop + chartHeight * (1 - p);
            const val = Math.round(maxOffset * p);
            return (
              <g key={idx}>
                <line
                  x1={padLeft}
                  y1={y}
                  x2={width - padRight}
                  y2={y}
                  stroke="rgba(255,255,255,0.07)"
                  strokeDasharray="3 3"
                />
                <text
                  x={padLeft - 10}
                  y={y + 4}
                  fill="var(--text-muted)"
                  fontSize={10}
                  fontFamily="var(--font-mono)"
                  textAnchor="end"
                >
                  {val}µs
                </text>
              </g>
            );
          })}

          {/* 150µs Threshold Reference Line */}
          <line
            x1={padLeft}
            y1={thresholdY}
            x2={width - padRight}
            y2={thresholdY}
            stroke="var(--color-rose)"
            strokeWidth={1.5}
            strokeDasharray="4 4"
          />
          <text
            x={width - padRight - 6}
            y={thresholdY - 6}
            fill="var(--color-rose)"
            fontSize={11}
            fontWeight={600}
            fontFamily="var(--font-mono)"
            textAnchor="end"
          >
            Threshold: {thresholdUs.toFixed(0)}µs
          </text>

          {/* Telemetry Curves per node */}
          {Object.entries(seriesByNode).map(([nodeId, nodeSamples]) => {
            if (nodeSamples.length < 2) return null;
            const strokeColor = nodeColors[nodeId] || "#38bdf8";

            const points = nodeSamples
              .map((s, idx) => {
                const x = padLeft + (idx / (nodeSamples.length - 1)) * chartWidth;
                const y = padTop + chartHeight * (1 - Math.min(s.sync_offset_us, maxOffset) / maxOffset);
                return `${x.toFixed(1)},${y.toFixed(1)}`;
              })
              .join(" ");

            const lastPoint = nodeSamples[nodeSamples.length - 1];
            const lastX = padLeft + chartWidth;
            const lastY = padTop + chartHeight * (1 - Math.min(lastPoint.sync_offset_us, maxOffset) / maxOffset);

            return (
              <g key={nodeId}>
                <polyline
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth={2}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  points={points}
                />
                <circle
                  cx={lastX}
                  cy={lastY}
                  r={4}
                  fill={strokeColor}
                  stroke="#070a12"
                  strokeWidth={2}
                />
              </g>
            );
          })}
        </svg>
      </div>

      {/* Cluster Node Status Chips */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "12px", marginTop: "16px" }}>
        {latestByNode.length === 0 ? (
          <div style={{ fontSize: "0.825rem", color: "var(--text-muted)", fontStyle: "italic" }}>
            Awaiting metric samples from Stream Watch node...
          </div>
        ) : (
          latestByNode.map((sample) => {
            const isBreach = sample.sync_offset_us > thresholdUs;
            const color = nodeColors[sample.node_id] || "var(--color-cyan)";
            return (
              <div
                key={sample.node_id}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "8px 14px",
                  background: "var(--bg-secondary)",
                  borderRadius: "8px",
                  border: isBreach
                    ? "1px solid rgba(244, 63, 94, 0.4)"
                    : "1px solid var(--border-subtle)",
                }}
              >
                <div
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    backgroundColor: color,
                  }}
                />
                <span style={{ fontSize: "0.85rem", fontWeight: 600 }}>{sample.node_id}</span>
                <span
                  style={{
                    fontSize: "0.85rem",
                    fontFamily: "var(--font-mono)",
                    color: isBreach ? "var(--color-rose)" : "var(--color-emerald)",
                    fontWeight: 600,
                  }}
                >
                  {sample.sync_offset_us.toFixed(1)} µs
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
