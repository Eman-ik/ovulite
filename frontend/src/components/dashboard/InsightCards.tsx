import type { DashboardKpiItem } from "@/lib/types";
import { Lightbulb } from "lucide-react";

function describeDelta(kpi: DashboardKpiItem): string | null {
  if (kpi.value === null || kpi.delta_pct === null || kpi.delta_direction === "flat" || !kpi.delta_direction) {
    return null;
  }
  const verb = kpi.delta_direction === "up" ? "improved" : "declined";
  const amount =
    kpi.unit === "percent"
      ? `${Math.abs(kpi.delta_pct).toFixed(1)} percentage points`
      : `${Math.abs(kpi.delta_pct).toFixed(1)}%`;
  return `${kpi.label} ${verb} by ${amount} ${kpi.comparison_label}.`;
}

export default function InsightCards({ kpis }: { kpis: DashboardKpiItem[] }) {
  const insights = kpis
    .map(describeDelta)
    .filter((s): s is string => Boolean(s))
    .slice(0, 3);

  if (insights.length === 0) {
    return (
      <p className="text-sm dash-muted">
        Not enough period-over-period data yet to generate insights for this selection.
      </p>
    );
  }

  return (
    <div className="grid gap-3 sm:grid-cols-3">
      {insights.map((text, i) => (
        <div key={i} className="dash-tile flex items-start gap-2.5 p-3.5 text-sm dash-muted">
          <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-[var(--primary)]" />
          <span>{text}</span>
        </div>
      ))}
    </div>
  );
}
