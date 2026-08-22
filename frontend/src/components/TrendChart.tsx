import type { LabFlag, TrendPoint } from "../types";

const FLAG_COLOR: Record<LabFlag, string> = {
  normal: "#16a34a",
  high: "#dc2626",
  low: "#d97706",
  review: "#ca8a04",
};

export default function TrendChart({ points }: { points: TrendPoint[] }) {
  const w = 560;
  const h = 180;
  const pad = { l: 40, r: 16, t: 14, b: 24 };

  if (points.length === 0) {
    return <p className="text-sm text-slate-400">No readings.</p>;
  }

  const values = points.map((p) => p.value);
  const refs = points.flatMap((p) => [p.ref_low, p.ref_high].filter((v): v is number => v != null));
  const lo = Math.min(...values, ...(refs.length ? refs : values));
  const hi = Math.max(...values, ...(refs.length ? refs : values));
  const span = hi - lo || 1;

  const x = (i: number) =>
    pad.l + (i * (w - pad.l - pad.r)) / Math.max(points.length - 1, 1);
  const y = (v: number) => pad.t + ((hi - v) / span) * (h - pad.t - pad.b);

  const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i)},${y(p.value)}`).join(" ");
  const band =
    refs.length >= 2
      ? `M${x(0)},${y(Math.max(...(points.map((p) => p.ref_high).filter((v): v is number => v != null))))} L${x(points.length - 1)},${y(Math.max(...(points.map((p) => p.ref_high).filter((v): v is number => v != null))))}`
      : null;
  const refHigh = points.find((p) => p.ref_high != null)?.ref_high ?? null;
  const refLow = points.find((p) => p.ref_low != null)?.ref_low ?? null;

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full">
      {refHigh != null && (
        <line
          x1={pad.l}
          x2={w - pad.r}
          y1={y(refHigh)}
          y2={y(refHigh)}
          stroke="#dc2626"
          strokeDasharray="4 4"
          strokeWidth="1"
        />
      )}
      {refLow != null && (
        <line
          x1={pad.l}
          x2={w - pad.r}
          y1={y(refLow)}
          y2={y(refLow)}
          stroke="#d97706"
          strokeDasharray="4 4"
          strokeWidth="1"
        />
      )}
      <path d={path} fill="none" stroke="#2563eb" strokeWidth="2" />
      {points.map((p, i) => (
        <g key={i}>
          <circle cx={x(i)} cy={y(p.value)} r="4" fill={FLAG_COLOR[p.flag]} />
          <text x={x(i)} y={h - 6} fontSize="10" textAnchor="middle" fill="#94a3b8">
            {p.taken_at}
          </text>
          <text
            x={x(i)}
            y={y(p.value) - 8}
            fontSize="11"
            textAnchor="middle"
            fill="#334155"
          >
            {p.value}
          </text>
        </g>
      ))}
      <text x={4} y={y(hi) + 4} fontSize="10" fill="#94a3b8">
        {hi}
      </text>
      <text x={4} y={y(lo) + 4} fontSize="10" fill="#94a3b8">
        {lo}
      </text>
      {band && null}
    </svg>
  );
}
