import type { DashboardFunnelResponse } from "@/lib/types";

export default function ReproductiveFunnel({
  data,
  stageNames,
}: {
  data: DashboardFunnelResponse | null;
  stageNames?: string[];
}) {
  if (!data) {
    return <div className="text-sm text-gray-500">Loading funnel…</div>;
  }
  const stages = stageNames ? data.stages.filter((s) => stageNames.includes(s.name)) : data.stages;
  const omitted = stageNames ? data.omitted_stages.filter((s) => stageNames.includes(s.name)) : data.omitted_stages;
  const maxValue = Math.max(1, ...stages.map((s) => s.value));

  return (
    <div className="space-y-3">
      {stages.map((stage, i) => {
        const widthPct = Math.max(4, (stage.value / maxValue) * 100);
        return (
          <div key={stage.name} className="flex items-center gap-4">
            <div className="w-40 shrink-0 text-sm font-medium text-gray-700">{stage.name}</div>
            <div className="relative h-9 flex-1 rounded-lg bg-emerald-50">
              <div
                className="flex h-9 items-center rounded-lg bg-gradient-to-r from-emerald-500 to-emerald-400 px-3 text-sm font-semibold text-white transition-all"
                style={{ width: `${widthPct}%` }}
              >
                {stage.value.toLocaleString()}
              </div>
            </div>
            <div className="w-32 shrink-0 text-right text-xs text-gray-500">
              {i === 0 ? (
                <span>&nbsp;</span>
              ) : stage.conversion_pct_from_previous !== null ? (
                <span>{stage.conversion_pct_from_previous}% of prior stage</span>
              ) : (
                <span className="italic text-gray-400">no data</span>
              )}
            </div>
          </div>
        );
      })}
      {omitted.map((stage) => (
        <div key={stage.name} className="flex items-center gap-4 opacity-60">
          <div className="w-40 shrink-0 text-sm font-medium text-gray-500">{stage.name}</div>
          <div className="flex-1 rounded-lg border border-dashed border-gray-300 px-3 py-2 text-xs italic text-gray-400">
            {stage.reason}
          </div>
        </div>
      ))}
    </div>
  );
}
