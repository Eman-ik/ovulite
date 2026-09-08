import type { DashboardOperationsResponse } from "@/lib/types";
import { KPI_COLORS, type KpiColor } from "@/components/dashboard/KpiCard";

type Tile = { key: keyof DashboardOperationsResponse; label: string; color: KpiColor };

const ALL_TILES: Tile[] = [
  { key: "opu_sessions_today", label: "OPU Sessions Today", color: "blue" },
  { key: "ivf_batches_in_culture", label: "IVF In Culture", color: "teal" },
  { key: "embryos_pending_grading", label: "Pending Grading", color: "violet" },
  { key: "transfers_scheduled_today", label: "Transfers Today", color: "amber" },
  { key: "pregnancy_checks_due", label: "PC Due", color: "rose" },
  { key: "predictions_pending_outcome", label: "Predictions Pending", color: "olive" },
];

export default function OperationsPanel({
  data,
  tileKeys,
}: {
  data: DashboardOperationsResponse | null;
  tileKeys?: Array<keyof DashboardOperationsResponse>;
}) {
  if (!data) return <div className="text-sm dash-muted">Loading…</div>;
  const tiles = tileKeys ? ALL_TILES.filter((t) => tileKeys.includes(t.key)) : ALL_TILES;

  return (
    <div className="grid grid-cols-2 gap-3">
      {tiles.map((tile) => {
        const palette = KPI_COLORS[tile.color];
        return (
          <div key={tile.key} className="dash-tile p-3">
            <div className="flex items-start justify-between gap-2">
              <p className="text-[11px] font-medium uppercase tracking-wide dash-muted">{tile.label}</p>
              {data.estimated_fields.includes(tile.key) && (
                <span className="shrink-0 rounded-full bg-[rgba(234,186,107,0.22)] px-1.5 py-0.5 text-[9px] font-semibold text-[#a1741c]">
                  est.
                </span>
              )}
            </div>
            <p className="mt-1.5 text-2xl font-semibold" style={{ color: palette.ink }}>
              {data[tile.key] as number}
            </p>
          </div>
        );
      })}
    </div>
  );
}
