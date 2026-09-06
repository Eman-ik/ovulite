import type { DashboardDataQualityResponse } from "@/lib/types";

export default function DataQualityPanel({ data }: { data: DashboardDataQualityResponse | null }) {
  if (!data) return <div className="text-sm text-gray-500">Loading…</div>;

  return (
    <div className="space-y-2">
      {data.rows.map((row) => (
        <div key={`${row.table}.${row.field}`} className="flex items-center justify-between rounded-lg border border-gray-100 px-3 py-2">
          <div>
            <p className="text-sm font-medium text-gray-800">
              {row.table}.{row.field}
              {row.stale && <span className="ml-2 rounded-full bg-amber-100 px-1.5 py-0.5 text-[10px] font-semibold text-amber-700">stale &gt;45d</span>}
            </p>
            <p className="text-xs text-gray-500">{row.missing} of {row.total} records missing</p>
          </div>
          <span className={`text-sm font-semibold ${row.missing_pct > 20 ? "text-rose-600" : row.missing_pct > 0 ? "text-amber-600" : "text-emerald-600"}`}>
            {row.missing_pct}%
          </span>
        </div>
      ))}
    </div>
  );
}
