import type { DashboardFunnelResponse } from "@/lib/types";

/** Warm gold → cool teal as the funnel narrows, so each stage reads distinctly. */
const STAGE_GRADIENTS = [
  "linear-gradient(90deg, #8EB69B, #d0a45e)",
  "linear-gradient(90deg, #d0a45e, #e3b48a)",
  "linear-gradient(90deg, #e6b0a0, #b98ea8)",
  "linear-gradient(90deg, #b98ea8, #c98fae)",
  "linear-gradient(90deg, #c98fae, #8d97c4)",
  "linear-gradient(90deg, #8d97c4, #a8b6e4)",
  "linear-gradient(90deg, #6aa5b8, #4f8f7d)",
  "linear-gradient(90deg, #4f8f7d, #8EB69B)",
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

            <div className="relative h-9 min-w-0 flex-1 rounded-xl bg-black/[0.045]">
              <div
                className="flex h-9 items-center rounded-xl px-3 text-[13px] font-semibold text-[#051F20] transition-all"
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
