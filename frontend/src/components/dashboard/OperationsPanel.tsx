import type { DashboardOperationsResponse } from "@/lib/types";
import { KPI_COLORS, type KpiColor } from "@/components/dashboard/KpiCard";
import { ROLE } from "@/lib/chartPalette";

type Tile = { key: keyof DashboardOperationsResponse; label: string; color: KpiColor };

const ALL_TILES: Tile[] = [
  { key: "opu_sessions_today", label: "OPU Sessions Today", color: "volume" },
  { key: "ivf_batches_in_culture", label: "IVF In Culture", color: "volume" },
  { key: "embryos_pending_grading", label: "Pending Grading", color: "volume" },
  { key: "transfers_scheduled_today", label: "Transfers Today", color: "transfer" },
  { key: "pregnancy_checks_due", label: "PC Due", color: "pending" },
  { key: "predictions_pending_outcome", label: "Predictions Pending", color: "pending" },
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
              <p className="flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide dash-muted">
                <span
                  aria-hidden
                  className="inline-block h-2.5 w-2.5 shrink-0 rounded-full"
                  style={{
                    background: palette.solid,
                    border: `1.25px ${ROLE[tile.color].dash ? "dashed" : "solid"} ${ROLE[tile.color].stroke ?? "transparent"}`,
                  }}
                />
                {tile.label}
              </p>
              {data.estimated_fields.includes(tile.key) && (
                <span className="shrink-0 rounded-full bg-[rgba(148, 169, 190,0.22)] px-1.5 py-0.5 text-[9px] font-semibold text-[#7a5a12]">
                  est.
                </span>
              )}
            </div>
            <p className="mt-1.5 text-2xl font-semibold" style={{ color: "#2E3645" }}>
              {data[tile.key] as number}
            </p>
          </div>
        );
      })}
    </div>
  );
}
