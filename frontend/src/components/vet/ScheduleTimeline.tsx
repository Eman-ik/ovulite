import { Check, Clock, AlertTriangle, Syringe } from "lucide-react";
import type { ScheduledStep, StepState } from "@/lib/types";

/** Colour carries the same meaning everywhere on this page. */
export const STATE_STYLE: Record<StepState, { dot: string; text: string; chip: string }> = {
  Done: { dot: "#8EB69B", text: "text-[#235347]", chip: "bg-[rgba(142,182,155,0.2)] text-[#235347]" },
  Overdue: { dot: "#9d3730", text: "text-[#9d3730]", chip: "bg-[rgba(185,142,168,0.22)] text-[#9d3730]" },
  "Due today": { dot: "#235347", text: "text-[#7a5a12]", chip: "bg-[rgba(208,164,94,0.26)] text-[#7a5a12]" },
  Upcoming: { dot: "#b7c9bd", text: "dash-muted", chip: "bg-black/[0.05] dash-muted" },
};

function StateIcon({ state }: { state: StepState }) {
  if (state === "Done") return <Check className="h-3 w-3" strokeWidth={3} />;
  if (state === "Overdue") return <AlertTriangle className="h-3 w-3" strokeWidth={2.5} />;
  if (state === "Due today") return <Clock className="h-3 w-3" strokeWidth={2.5} />;
  return <Syringe className="h-2.5 w-2.5" strokeWidth={2.5} />;
}

export function relativeDay(days: number): string {
  if (days === 0) return "today";
  if (days === 1) return "tomorrow";
  if (days === -1) return "yesterday";
  return days > 0 ? `in ${days}d` : `${Math.abs(days)}d ago`;
}

/**
 * One enrollment's steps as a horizontal track. Reads left to right in
 * treatment order so the shape of the protocol is visible at a glance, with
 * the connector between two steps showing whether that gap is complete.
 */
export default function ScheduleTimeline({
  steps,
  onLog,
  busyStepId,
}: {
  steps: ScheduledStep[];
  onLog?: (step: ScheduledStep) => void;
  busyStepId?: number | null;
}) {
  if (steps.length === 0) {
    return <p className="text-xs dash-muted">No steps defined for this protocol.</p>;
  }

  return (
    <div className="custom-scrollbar overflow-x-auto pb-1">
      <div className="flex min-w-max items-start gap-0">
        {steps.map((step, i) => {
          const style = STATE_STYLE[step.state];
          const canLog = onLog && step.state !== "Done";
          return (
            <div key={step.step_id} className="flex items-start">
              <div className="flex w-[132px] flex-col items-center px-1 text-center">
                <div
                  className="flex h-6 w-6 items-center justify-center rounded-full text-white"
                  style={{ background: style.dot }}
                >
                  <StateIcon state={step.state} />
                </div>
                <p className="mt-1.5 text-[11px] font-medium leading-tight dash-heading">
                  {step.step_name}
                </p>
                {step.is_transfer_day && (
                  <span className="mt-0.5 rounded-full bg-[rgba(141,151,196,0.24)] px-1.5 py-px text-[9px] font-semibold text-[#5f6ba0]">
                    transfer
                  </span>
                )}
                <p className="mt-0.5 text-[10px] dash-muted">{step.due_date}</p>
                <p className={`text-[10px] ${style.text}`}>
                  {step.state === "Done"
                    ? step.completed_on
                      ? `done ${step.completed_on}`
                      : "done"
                    : relativeDay(step.days_from_today)}
                </p>
                {canLog && (
                  <button
                    type="button"
                    onClick={() => onLog(step)}
                    disabled={busyStepId === step.step_id}
                    className="mt-1.5 rounded-lg border border-[var(--border)] bg-[var(--card)] px-2 py-1 text-[10px] font-medium transition hover:bg-black/[0.04] disabled:opacity-50"
                  >
                    {busyStepId === step.step_id ? "Saving…" : "Log given"}
                  </button>
                )}
              </div>
              {i < steps.length - 1 && (
                <div
                  className="mt-3 h-0.5 w-6 shrink-0 rounded"
                  style={{
                    background: steps[i + 1].state === "Done" ? STATE_STYLE.Done.dot : "#cfe0d5",
                  }}
                />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
