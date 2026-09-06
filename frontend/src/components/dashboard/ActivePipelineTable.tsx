import type { DashboardPipelineRow } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

const STAGE_LABEL: Record<DashboardPipelineRow["stage"], string> = {
  opu: "OPU",
  ivf: "IVF Batch",
  grading: "Grading",
  transfer_scheduled: "Transfer",
  pending_pc: "Pregnancy Check",
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
    return <div className="py-6 text-center text-sm text-gray-400">No active pipeline items for this selection.</div>;
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-100 text-left text-xs uppercase tracking-wide text-gray-500">
            <th className="py-2 pr-3">Stage</th>
            <th className="py-2 pr-3">Item</th>
            <th className="py-2 pr-3">Date</th>
            <th className="py-2 pr-3">Detail</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((r) => (
            <tr key={`${r.stage}-${r.entity_id}`} className="border-b border-gray-50 last:border-0">
              <td className="py-2 pr-3">
                <Badge variant="outline">{STAGE_LABEL[r.stage]}</Badge>
              </td>
              <td className="py-2 pr-3 font-medium text-gray-800">{r.label}</td>
              <td className="py-2 pr-3 text-gray-500">{r.date ?? "—"}</td>
              <td className="py-2 pr-3 text-gray-500">{r.detail ?? "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
