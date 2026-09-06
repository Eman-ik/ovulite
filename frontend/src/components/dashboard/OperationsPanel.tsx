import type { DashboardOperationsResponse } from "@/lib/types";

type Tile = { key: keyof DashboardOperationsResponse; label: string };

const ALL_TILES: Tile[] = [
  { key: "opu_sessions_today", label: "OPU Sessions Today" },
  { key: "ivf_batches_in_culture", label: "IVF Batches In Culture" },
  { key: "embryos_pending_grading", label: "Embryos Pending Grading" },
  { key: "transfers_scheduled_today", label: "Transfers Scheduled Today" },
  { key: "pregnancy_checks_due", label: "Pregnancy Checks Due" },
  { key: "predictions_pending_outcome", label: "Predictions Pending Outcome" },
];

export default function OperationsPanel({
  data,
  tileKeys,
}: {
  data: DashboardOperationsResponse | null;
  tileKeys?: Array<keyof DashboardOperationsResponse>;
}) {
  if (!data) return <div className="text-sm text-gray-500">Loading…</div>;
  const tiles = tileKeys ? ALL_TILES.filter((t) => tileKeys.includes(t.key)) : ALL_TILES;

  return (
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
      {tiles.map((tile) => (
        <div key={tile.key} className="rounded-xl border border-emerald-100 bg-emerald-50 p-3">
          <div className="flex items-start justify-between">
            <p className="text-xs font-medium uppercase tracking-wide text-emerald-700">{tile.label}</p>
            {data.estimated_fields.includes(tile.key) && (
              <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">
                estimated
              </span>
            )}
          </div>
          <p className="mt-1 text-2xl font-bold text-emerald-900">{data[tile.key] as number}</p>
        </div>
      ))}
    </div>
  );
}
