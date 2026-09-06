import type { ReactNode } from "react";

export type KpiSparklinePoint = { bucket: string; value: number | null };
export type KpiDelta = { pct: number; direction: "up" | "down" | "flat"; suffix?: string };

type KpiCardProps = {
  title: string;
  value: string | number;
  subtitle: string;
  icon?: ReactNode;
  delta?: KpiDelta;
  sparkline?: KpiSparklinePoint[];
  comparisonLabel?: string;
};

function Sparkline({ points }: { points: KpiSparklinePoint[] }) {
  const values = points.map((p) => p.value).filter((v): v is number => v !== null);
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const w = 100;
  const h = 28;
  const step = w / (points.length - 1);
  const coords = points.map((p, i) => {
    const x = i * step;
    const y = p.value === null ? null : h - ((p.value - min) / range) * h;
    return { x, y };
  });
  const segments: string[] = [];
  let current: string[] = [];
  coords.forEach(({ x, y }) => {
    if (y === null) {
      if (current.length > 1) segments.push(current.join(" "));
      current = [];
      return;
    }
    current.push(`${x},${y.toFixed(1)}`);
  });
  if (current.length > 1) segments.push(current.join(" "));

  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="mt-2 h-7 w-full" preserveAspectRatio="none">
      {segments.map((points, i) => (
        <polyline
          key={i}
          points={points}
          fill="none"
          stroke="currentColor"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
          className="text-emerald-400"
        />
      ))}
    </svg>
  );
}

export default function KpiCard({
  title,
  value,
  subtitle,
  icon,
  delta,
  sparkline,
  comparisonLabel,
}: KpiCardProps) {
  return (
    <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
      <div className="flex items-center justify-between">
        <div className="h-12 w-12 rounded-2xl bg-emerald-100 flex items-center justify-center text-emerald-600">
          {icon}
        </div>
        {delta ? (
          <span
            className={`inline-flex items-center gap-1 rounded-full px-2 py-1 text-xs font-semibold ${
              delta.direction === "up"
                ? "bg-emerald-50 text-emerald-700"
                : delta.direction === "down"
                ? "bg-rose-50 text-rose-700"
                : "bg-gray-100 text-gray-600"
            }`}
          >
            {delta.direction === "up" ? "↑" : delta.direction === "down" ? "↓" : "→"}
            {Math.abs(delta.pct).toFixed(1)}
            {delta.suffix ?? "%"}
          </span>
        ) : null}
      </div>

      <p className="mt-6 text-sm font-medium text-gray-600">{title}</p>
      <h2 className="mt-2 text-4xl font-bold text-gray-900">{value}</h2>
      <p className="mt-2 text-sm text-gray-500">{comparisonLabel ?? subtitle}</p>
      {sparkline && sparkline.length > 1 ? <Sparkline points={sparkline} /> : null}
    </div>
  );
}
