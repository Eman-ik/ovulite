import type { ReactNode } from "react";

export type KpiSparklinePoint = { bucket: string; value: number | null };
export type KpiDelta = { pct: number; direction: "up" | "down" | "flat"; suffix?: string };

/** Soft pastels — each metric gets its own identity without shouting. */
export const KPI_COLORS = {
  rose: { solid: "#e79a9a", soft: "rgba(231, 154, 154, 0.18)", ink: "#b25f5f" },
  blue: { solid: "#8fb8de", soft: "rgba(143, 184, 222, 0.18)", ink: "#4d7ba6" },
  green: { solid: "#86c5a4", soft: "rgba(134, 197, 164, 0.18)", ink: "#3f8a68" },
  violet: { solid: "#c3a6e0", soft: "rgba(195, 166, 224, 0.18)", ink: "#8663a8" },
  amber: { solid: "#eaba6b", soft: "rgba(234, 186, 107, 0.22)", ink: "#a97a1e" },
  teal: { solid: "#79c6bb", soft: "rgba(121, 198, 187, 0.18)", ink: "#3d8a80" },
  pink: { solid: "#e3a3c4", soft: "rgba(227, 163, 196, 0.18)", ink: "#ac6489" },
  olive: { solid: "#adbb84", soft: "rgba(173, 187, 132, 0.22)", ink: "#74814d" },
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
                ? "bg-[rgba(134,197,164,0.22)] text-[#2f7d5c]"
                : delta.direction === "down"
                ? "bg-[rgba(231,154,154,0.24)] text-[#b8433d]"
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
