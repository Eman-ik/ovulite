import type { ReactNode } from "react";

export type KpiSparklinePoint = { bucket: string; value: number | null };
export type KpiDelta = { pct: number; direction: "up" | "down" | "flat"; suffix?: string };

/** Soft pastels — each metric gets its own identity without shouting. */
export const KPI_COLORS = {
  rose: { solid: "#FFA7D7", soft: "rgba(255, 167, 215, 0.2)", ink: "#FFA7D7" },
  blue: { solid: "#66CAC8", soft: "rgba(102, 202, 200, 0.2)", ink: "#66CAC8" },
  green: { solid: "#C8E6A0", soft: "rgba(200, 230, 160, 0.2)", ink: "#C8E6A0" },
  violet: { solid: "#D8BBF1", soft: "rgba(216, 187, 241, 0.2)", ink: "#D8BBF1" },
  amber: { solid: "#FFB598", soft: "rgba(255, 181, 152, 0.2)", ink: "#FFB598" },
  teal: { solid: "#CFE8FF", soft: "rgba(207, 232, 255, 0.2)", ink: "#CFE8FF" },
  pink: { solid: "#C08081", soft: "rgba(192, 128, 129, 0.2)", ink: "#C08081" },
  olive: { solid: "#D8C3A5", soft: "rgba(216, 195, 165, 0.2)", ink: "#D8C3A5" },
};

function Sparkline({ points, color }: { points: KpiSparklinePoint[]; color: string }) {
  const values = points.map((p) => p.value).filter((v): v is number => v !== null);
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const w = 100;
  const h = 26;
  const step = w / (points.length - 1);
  const coords = points.map((p, i) => ({
    x: i * step,
    y: p.value === null ? null : h - ((p.value - min) / range) * h,
  }));

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
    <svg viewBox={`0 0 ${w} ${h}`} className="mt-3 h-6 w-full" preserveAspectRatio="none">
      {segments.map((seg, i) => (
        <polyline
          key={i}
          points={seg}
          fill="none"
          stroke={color}
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
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
  color = "green",
}: KpiCardProps) {
  const palette = KPI_COLORS[color];

  return (
    <div className="dash-card ov-hover-lift !p-5">
      <div className="flex items-start justify-between">
        <div
          className="flex h-11 w-11 items-center justify-center rounded-2xl"
          style={{ background: palette.soft, color: "#596070" }}
        >
          {icon}
        </div>
        {delta ? (
          <span
            className={`inline-flex items-center gap-0.5 rounded-full px-2 py-1 text-[11px] font-semibold ${
              delta.direction === "up"
                ? "bg-[rgba(148, 169, 190,0.22)] text-[#596070]"
                : delta.direction === "down"
                ? "bg-[rgba(117, 127, 153,0.24)] text-[#9d3730]"
                : "bg-black/[0.05] text-[var(--muted-foreground)]"
            }`}
          >
            {delta.direction === "up" ? "↑" : delta.direction === "down" ? "↓" : "→"}
            {Math.abs(delta.pct).toFixed(1)}
            {delta.suffix ?? "%"}
          </span>
        ) : null}
      </div>

      <p className="mt-5 text-xs font-medium uppercase tracking-wide dash-muted">{title}</p>
      <h2 className="mt-1.5 text-[32px] font-semibold leading-none dash-heading">{value}</h2>
      <p className="mt-2 text-xs dash-muted">{comparisonLabel ?? subtitle}</p>
      {sparkline && sparkline.length > 1 ? <Sparkline points={sparkline} color={palette.ink} /> : null}
    </div>
  );
}
