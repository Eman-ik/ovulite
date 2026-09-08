import type { ReactNode } from "react";

export type KpiSparklinePoint = { bucket: string; value: number | null };
export type KpiDelta = { pct: number; direction: "up" | "down" | "flat"; suffix?: string };

/** Shades of green, distinct enough to give each metric its own identity. */
export const KPI_COLORS = {
  sage: { solid: "#a8cba0", soft: "rgba(168, 203, 160, 0.14)" },
  leaf: { solid: "#7fb069", soft: "rgba(127, 176, 105, 0.14)" },
  emerald: { solid: "#4f9d69", soft: "rgba(79, 157, 105, 0.14)" },
  pine: { solid: "#2f7d5c", soft: "rgba(47, 125, 92, 0.18)" },
  lime: { solid: "#cfe3b8", soft: "rgba(207, 227, 184, 0.14)" },
  mint: { solid: "#5fbf9f", soft: "rgba(95, 191, 159, 0.14)" },
  olive: { solid: "#8aa872", soft: "rgba(138, 168, 114, 0.16)" },
  teal: { solid: "#35836d", soft: "rgba(53, 131, 109, 0.18)" },
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
  color = "sage",
}: KpiCardProps) {
  const palette = KPI_COLORS[color];

  return (
    <div className="dash-card ov-hover-lift !p-5">
      <div className="flex items-start justify-between">
        <div
          className="flex h-11 w-11 items-center justify-center rounded-2xl"
          style={{ background: palette.soft, color: palette.solid }}
        >
          {icon}
        </div>
        {delta ? (
          <span
            className={`inline-flex items-center gap-0.5 rounded-full px-2 py-1 text-[11px] font-semibold ${
              delta.direction === "up"
                ? "bg-[rgba(127,176,105,0.16)] text-[#a8cba0]"
                : delta.direction === "down"
                ? "bg-[rgba(224,101,111,0.15)] text-[#f0a4aa]"
                : "bg-white/[0.06] text-[var(--muted-foreground)]"
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
      {sparkline && sparkline.length > 1 ? <Sparkline points={sparkline} color={palette.solid} /> : null}
    </div>
  );
}
