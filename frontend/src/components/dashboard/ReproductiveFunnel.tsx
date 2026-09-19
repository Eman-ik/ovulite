import type { DashboardFunnelResponse } from "@/lib/types";

/** Pale sage deepening to forest as the funnel narrows, so the visual weight
 *  tracks the drop-off instead of cycling unrelated hues. Bars carry a dark
 *  label on the light end and a cream one once the fill goes dark. */
const STAGE_GRADIENTS = [
  "linear-gradient(90deg, #DAF1DE, #B6D9C0)",
  "linear-gradient(90deg, #B6D9C0, #A0CBAC)",
  "linear-gradient(90deg, #A0CBAC, #8EB69B)",
  "linear-gradient(90deg, #8EB69B, #74A386)",
  "linear-gradient(90deg, #74A386, #5F9078)",
  "linear-gradient(90deg, #5F9078, #4A7C68)",
  "linear-gradient(90deg, #4A7C68, #356A57)",
  "linear-gradient(90deg, #356A57, #235347)",
  "linear-gradient(90deg, #235347, #163832)",
];

/** Index at which the fill is dark enough to need light text. */
const DARK_FILL_FROM = 5;

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
                {i === 0 ? null : stage.cohort_break ? (
                  <span className="italic opacity-70">new cohort</span>
                ) : stage.conversion_pct_from_previous !== null ? (
                  `${stage.conversion_pct_from_previous}%`
                ) : (
                  <span className="italic opacity-60">no data</span>
                )}
              </span>
            </div>

            <div className="relative h-9 min-w-0 flex-1 rounded-xl bg-black/[0.045]">
              <div
                className="flex h-9 items-center rounded-xl px-3 text-[13px] font-semibold transition-all"
                style={{
                  width: `${widthPct}%`,
                  background: STAGE_GRADIENTS[globalIndex % STAGE_GRADIENTS.length],
                  color: globalIndex >= DARK_FILL_FROM ? "#DAF1DE" : "#051F20",
                }}
              >
                {stage.value.toLocaleString()}
              </div>
            </div>

            <div className="hidden shrink-0 text-right text-xs dash-muted sm:block sm:w-32">
              {i === 0 ? (
                <span>&nbsp;</span>
              ) : stage.cohort_break ? (
                <span className="italic opacity-70" title={stage.cohort_note ?? undefined}>
                  new cohort
                </span>
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
