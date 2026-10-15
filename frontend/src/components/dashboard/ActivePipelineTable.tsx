import type { DashboardPipelineRow } from "@/lib/types";

const STAGE_LABEL: Record<DashboardPipelineRow["stage"], string> = {
  opu: "OPU",
  ivf: "IVF Batch",
  grading: "Grading",
  transfer_scheduled: "Transfer",
  pending_pc: "Pregnancy Check",
};

const STAGE_COLOR: Record<DashboardPipelineRow["stage"], string> = {
  opu: "#94A9BE",
  ivf: "#757F99",
  grading: "#596070",
  transfer_scheduled: "#B2CDDF",
  pending_pc: "#94A9BE",
};

export default function ActivePipelineTable({
  rows,
  stages,
}: {
  rows: DashboardPipelineRow[];
  stages?: Array<DashboardPipelineRow["stage"]>;
}) {
  const filtered = stages ? rows.filter((r) => stages.includes(r.stage)) : rows;

  if (filtered.length === 0) {
    return <div className="py-6 text-center text-sm dash-muted">No active pipeline items for this selection.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-[var(--border)] text-left text-[11px] uppercase tracking-wide dash-muted">
            <th className="py-2 pr-3 font-medium">Stage</th>
            <th className="py-2 pr-3 font-medium">Item</th>
            <th className="py-2 pr-3 font-medium">Date</th>
            <th className="py-2 pr-3 font-medium">Detail</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((r) => (
            <tr key={`${r.stage}-${r.entity_id}`} className="border-b border-[var(--border)] last:border-0">
              <td className="py-2.5 pr-3">
                <span
                  className="inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-medium"
                  style={{
                    background: `${STAGE_COLOR[r.stage]}22`,
                    color: STAGE_COLOR[r.stage],
                  }}
                >
                  {STAGE_LABEL[r.stage]}
                </span>
              </td>
              <td className="py-2.5 pr-3 font-medium dash-heading">{r.label}</td>
              <td className="py-2.5 pr-3 dash-muted">{r.date ?? "—"}</td>
              <td className="py-2.5 pr-3 dash-muted">{r.detail ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
