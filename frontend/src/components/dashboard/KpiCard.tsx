import type { ReactNode } from "react";

export type KpiSparklinePoint = { bucket: string; value: number | null };
export type KpiDelta = { pct: number; direction: "up" | "down" | "flat"; suffix?: string };

/** Soft pastels — each metric gets its own identity without shouting. */
export const KPI_COLORS = {
  rose: { solid: "#b98ea8", soft: "rgba(185, 142, 168, 0.18)", ink: "#8c5a70" },
  blue: { solid: "#6aa5b8", soft: "rgba(106, 165, 184, 0.18)", ink: "#3f7c91" },
  green: { solid: "#8EB69B", soft: "rgba(142, 182, 155, 0.18)", ink: "#235347" },
  violet: { solid: "#8d97c4", soft: "rgba(141, 151, 196, 0.18)", ink: "#5f6ba0" },
  amber: { solid: "#d0a45e", soft: "rgba(208, 164, 94, 0.22)", ink: "#7a5a12" },
  teal: { solid: "#4f8f7d", soft: "rgba(79, 143, 125, 0.18)", ink: "#2f6b5c" },
  pink: { solid: "#c98fae", soft: "rgba(227, 163, 196, 0.18)", ink: "#96546f" },
  olive: { solid: "#a8b87e", soft: "rgba(173, 187, 132, 0.22)", ink: "#6b7a44" },
} as const;

export type KpiColor = keyof typeof KPI_COLORS;

type KpiCardProps = {
  title: string;
  value: string | number;
  subtitle: string;
  icon?: ReactNode;
  delta?: KpiDelta;
  sparkline?: KpiSparklinePoint[];
  comparisonLabel?: string;
  color?: KpiColor;
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
          style={{ background: palette.soft, color: palette.ink }}
        >
          {icon}
        </div>
        {delta ? (
          <span
            className={`inline-flex items-center gap-0.5 rounded-full px-2 py-1 text-[11px] font-semibold ${
              delta.direction === "up"
                ? "bg-[rgba(142,182,155,0.22)] text-[#235347]"
                : delta.direction === "down"
                ? "bg-[rgba(185,142,168,0.24)] text-[#9d3730]"
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
