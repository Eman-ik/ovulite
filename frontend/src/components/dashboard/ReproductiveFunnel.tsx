import type { DashboardFunnelResponse } from "@/lib/types";
import RoleKey from "@/components/dashboard/RoleKey";
import { ROLE, textOn, type Role } from "@/lib/chartPalette";

/** Stage order is oocytes, mature, cleaved, blastocysts, transferable, transfers,
 *  pregnancies, ongoing, live births. Counts before transfer are volume; the
 *  transfer stage is the transfer role; outcome stages are positive. */
const STAGE_ROLES: Role[] = ["volume", "volume", "volume", "volume", "volume", "transfer", "positive", "positive", "positive"];
const STAGE_FILLS = STAGE_ROLES.map((r) => ROLE[r].fill);
const STAGE_GRADIENTS = STAGE_FILLS.map((c) => `linear-gradient(90deg, ${c}, ${c})`);

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

  // The steepest drop between consecutive stages, where the stages are comparable. Live births
  // are left out: no calving outcome is recorded for this programme, so a zero there is missing data.
  const drops = stages
    .map((s, i) => ({ s, prev: stages[i - 1] }))
    .filter(({ s, prev }) => prev && !s.cohort_break && s.name !== "Live Births" && s.conversion_pct_from_previous != null && prev.value > 0);
  const steepest = drops.reduce<(typeof drops)[number] | null>(
    (best, d) => (best == null || (d.s.conversion_pct_from_previous ?? 100) < (best.s.conversion_pct_from_previous ?? 100) ? d : best),
    null,
  );
  const funnelTakeaway = steepest
    ? `The steepest drop is from ${steepest.prev.name} to ${steepest.s.name}: ${steepest.s.conversion_pct_from_previous}% carry on (${steepest.s.value.toLocaleString()} of ${steepest.prev.value.toLocaleString()}).`
    : "Not enough comparable stages to name a steepest drop.";

  return (
    <div className="space-y-2.5">
      <p className="rounded-xl bg-white/65 px-3 py-2 text-[13px] leading-snug dash-heading" role="note">
        <span className="mr-1.5 font-semibold">What it shows:</span>
        {funnelTakeaway}
      </p>
      <RoleKey
        items={[
          { role: "volume", label: "Counts before transfer" },
          { role: "transfer", label: "Transfers" },
          { role: "positive", label: "Pregnancy outcomes" },
        ]}
      />
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
                  color: textOn(STAGE_FILLS[globalIndex % STAGE_FILLS.length]),
                  boxShadow: ROLE[STAGE_ROLES[globalIndex % STAGE_ROLES.length]].stroke
                    ? `inset 0 0 0 1.25px ${ROLE[STAGE_ROLES[globalIndex % STAGE_ROLES.length]].stroke}`
                    : undefined,
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
