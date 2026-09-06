import {
  Droplets,
  FlaskConical,
  Dna,
  Sparkles,
  ArrowRightLeft,
  HeartPulse,
  Brain,
} from "lucide-react";
import KpiCard from "@/components/dashboard/KpiCard";
import type { DashboardKpiItem } from "@/lib/types";

const ICONS: Record<string, React.ReactNode> = {
  oocytes_recovered: <Droplets className="h-6 w-6" />,
  maturation_rate: <FlaskConical className="h-6 w-6" />,
  cleavage_rate: <Dna className="h-6 w-6" />,
  blastocyst_rate: <Sparkles className="h-6 w-6" />,
  transferable_embryos: <Dna className="h-6 w-6" />,
  transfers_completed: <ArrowRightLeft className="h-6 w-6" />,
  pregnancy_rate: <HeartPulse className="h-6 w-6" />,
  model_auc: <Brain className="h-6 w-6" />,
};

function formatValue(kpi: DashboardKpiItem): string {
  if (kpi.value === null) return "No data";
  return kpi.unit === "percent" ? `${kpi.value}%` : kpi.value.toLocaleString();
}

export default function KpiRow({ kpis, keys }: { kpis: DashboardKpiItem[]; keys?: string[] }) {
  const visible = keys ? kpis.filter((k) => keys.includes(k.key)) : kpis;

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {visible.map((kpi) => (
        <KpiCard
          key={kpi.key}
          title={kpi.label}
          value={formatValue(kpi)}
          subtitle={kpi.comparison_label}
          comparisonLabel={kpi.value === null ? "No data for this selection" : kpi.comparison_label}
          icon={ICONS[kpi.key]}
          delta={
            kpi.delta_pct !== null && kpi.delta_direction
              ? { pct: kpi.delta_pct, direction: kpi.delta_direction, suffix: kpi.unit === "percent" ? "pp" : "%" }
              : undefined
          }
          sparkline={kpi.sparkline}
        />
      ))}
    </div>
  );
}
