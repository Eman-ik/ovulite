import type { DashboardDataQualityResponse } from "@/lib/types";

export default function DataQualityPanel({ data }: { data: DashboardDataQualityResponse | null }) {
  if (!data) return <div className="text-sm dash-muted">Loading…</div>;

  return (
    <div className="space-y-2">
      {data.rows.map((row) => {
        const tone =
          row.missing_pct > 20 ? "#f0a4aa" : row.missing_pct > 0 ? "#ddc07a" : "#a8cba0";
        return (
          <div
            key={`${row.table}.${row.field}`}
            className="dash-tile flex items-center justify-between gap-3 px-3.5 py-2.5"
          >
            <div className="min-w-0">
              <p className="truncate text-sm font-medium dash-heading">
                {row.table}.{row.field}
                {row.stale && (
                  <span className="ml-2 rounded-full bg-[rgba(214,178,92,0.16)] px-1.5 py-0.5 text-[9px] font-semibold text-[#ddc07a]">
                    stale &gt;45d
                  </span>
                )}
              </p>
              <p className="text-xs dash-muted">
                {row.missing} of {row.total} records missing
              </p>
            </div>

            <div className="flex shrink-0 items-center gap-2">
              <div className="h-1.5 w-16 overflow-hidden rounded-full bg-white/[0.07]">
                <div
                  className="h-full rounded-full"
                  style={{ width: `${Math.min(100, row.missing_pct)}%`, background: tone }}
                />
              </div>
              <span className="w-11 text-right text-sm font-semibold" style={{ color: tone }}>
                {row.missing_pct}%
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
