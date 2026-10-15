import type { ReactNode } from "react";
import { ROLE, type Role } from "@/lib/chartPalette";

export type KpiSparklinePoint = { bucket: string; value: number | null };
export type KpiDelta = { pct: number; direction: "up" | "down" | "flat"; suffix?: string };
export type KpiColor = Role;

interface KpiCardProps {
  title: string;
  value: ReactNode;
  subtitle?: string;
  comparisonLabel?: string;
  icon?: ReactNode;
  delta?: KpiDelta;
  sparkline?: KpiSparklinePoint[] | null;
  color?: KpiColor;
}

/**
 * KPI card colours carry meaning (see MEANING in lib/chartPalette.ts).
 * solid: the role colour. ink: a darker shade of it for the sparkline, since the
 * light swatches fail 3:1 on white. icon: text on the solid, chosen for contrast.
 */
export const KPI_COLORS = Object.fromEntries(
  (Object.keys(ROLE) as Role[]).map((role) => [
    role,
    { solid: ROLE[role].fill, soft: `${ROLE[role].fill}55`, ink: ROLE[role].ink, icon: ROLE[role].icon },
  ]),
) as Record<Role, { solid: string; soft: string; ink: string; icon: string }>;

/** Names the sparkline's granularity from its bucket labels: 2026-W27, 2026-07-04 or 2026-07. */
function sparklineLabel(points: KpiSparklinePoint[]): string {
  const bucket = points[0]?.bucket ?? "";
  const grain = bucket.includes("W") ? "weekly" : bucket.length === 10 ? "daily" : "monthly";
  return `${grain} trend, last ${points.length} ${grain === "daily" ? "days" : grain === "weekly" ? "weeks" : "months"}`;
}

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
  color = "volume",
}: KpiCardProps) {
  const palette = KPI_COLORS[color];

  return (
    <div
      className="dash-card ov-hover-lift !p-5"
      style={{ background: `linear-gradient(135deg, ${palette.soft}, rgba(255, 255, 255, 0.74))` }}
    >
      <div className="flex items-start justify-between">
        <div
          className="flex h-11 w-11 items-center justify-center rounded-2xl"
          style={{
            background: palette.solid,
            color: palette.icon,
            boxShadow: ROLE[color].stroke ? `inset 0 0 0 1.25px ${ROLE[color].stroke}` : undefined,
            borderStyle: ROLE[color].dash ? "dashed" : undefined,
          }}
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
      {sparkline && sparkline.length > 1 ? (
        <>
          <Sparkline points={sparkline} color={palette.ink} />
          <p className="mt-1 flex items-center gap-1.5 text-[11px] dash-muted">
            <span aria-hidden className="inline-block h-0.5 w-4 rounded" style={{ background: palette.ink }} />
            {sparklineLabel(sparkline)}
          </p>
        </>
      ) : null}
    </div>
  );
}
