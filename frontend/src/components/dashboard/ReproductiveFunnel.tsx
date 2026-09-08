import type { DashboardFunnelResponse } from "@/lib/types";

/** Light sage → deep pine as the funnel narrows. */
const STAGE_GRADIENTS = [
  "linear-gradient(90deg, #cfe3b8, #a8cba0)",
  "linear-gradient(90deg, #a8cba0, #8aa872)",
  "linear-gradient(90deg, #8aa872, #7fb069)",
  "linear-gradient(90deg, #7fb069, #5fbf9f)",
  "linear-gradient(90deg, #5fbf9f, #4f9d69)",
  "linear-gradient(90deg, #4f9d69, #35836d)",
  "linear-gradient(90deg, #35836d, #2f7d5c)",
  "linear-gradient(90deg, #2f7d5c, #24614a)",
];

export default function ReproductiveFunnel({
  data,
  stageNames,
}: {
  data: DashboardFunnelResponse | null;
  stageNames?: string[];
}) {
  if (!data) return <div className="text-sm dash-muted">Loading funnel…</div>;

  const allStages = data.stages;
  const stages = stageNames ? allStages.filter((s) => stageNames.includes(s.name)) : allStages;
  const omitted = stageNames ? data.omitted_stages.filter((s) => stageNames.includes(s.name)) : data.omitted_stages;
  const maxValue = Math.max(1, ...stages.map((s) => s.value));

  return (
    <div className="space-y-2.5">
      {stages.map((stage, i) => {
        const globalIndex = allStages.findIndex((s) => s.name === stage.name);
        const widthPct = Math.max(5, (stage.value / maxValue) * 100);
        return (
          <div key={stage.name} className="flex flex-col gap-1.5 sm:flex-row sm:items-center sm:gap-4">
            <div className="flex items-center justify-between sm:block sm:w-40 sm:shrink-0">
              <span className="text-[13px] font-medium dash-muted">{stage.name}</span>
              <span className="text-xs dash-muted sm:hidden">
                {i === 0 ? null : stage.conversion_pct_from_previous !== null ? (
                  `${stage.conversion_pct_from_previous}%`
                ) : (
                  <span className="italic opacity-60">no data</span>
                )}
              </span>
            </div>

            <div className="relative h-9 min-w-0 flex-1 rounded-xl bg-white/[0.04]">
              <div
                className="flex h-9 items-center rounded-xl px-3 text-[13px] font-semibold text-[#0b140d] transition-all"
                style={{
                  width: `${widthPct}%`,
                  background: STAGE_GRADIENTS[globalIndex % STAGE_GRADIENTS.length],
                }}
              >
                {stage.value.toLocaleString()}
              </div>
            </div>

            <div className="hidden shrink-0 text-right text-xs dash-muted sm:block sm:w-32">
              {i === 0 ? (
                <span>&nbsp;</span>
              ) : stage.conversion_pct_from_previous !== null ? (
                <span>{stage.conversion_pct_from_previous}% of prior</span>
              ) : (
                <span className="italic opacity-60">no data</span>
              )}
            </div>
          </div>
        );
      })}

      {omitted.map((stage) => (
        <div key={stage.name} className="flex flex-col gap-1.5 opacity-60 sm:flex-row sm:items-center sm:gap-4">
          <div className="text-[13px] font-medium dash-muted sm:w-40 sm:shrink-0">{stage.name}</div>
          <div className="flex-1 rounded-xl border border-dashed border-[var(--border)] px-3 py-2 text-xs italic dash-muted">
            {stage.reason}
          </div>
        </div>
      ))}
    </div>
  );
}
