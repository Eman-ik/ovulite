import { Check, Clock, AlertTriangle, Syringe } from "lucide-react";
import type { ScheduledStep, StepState } from "@/lib/types";

/** Colour carries the same meaning everywhere on this page. */
export const STATE_STYLE: Record<StepState, { dot: string; text: string; chip: string }> = {
  Done: { dot: "#86c5a4", text: "text-[#2f7d5c]", chip: "bg-[rgba(134,197,164,0.2)] text-[#2f7d5c]" },
  Overdue: { dot: "#d2564f", text: "text-[#b8433d]", chip: "bg-[rgba(231,154,154,0.22)] text-[#b8433d]" },
  "Due today": { dot: "#e0ab35", text: "text-[#a1741c]", chip: "bg-[rgba(234,186,107,0.26)] text-[#a1741c]" },
  Upcoming: { dot: "#c9c6bf", text: "dash-muted", chip: "bg-black/[0.05] dash-muted" },
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
                  <span className="mt-0.5 rounded-full bg-[rgba(195,166,224,0.24)] px-1.5 py-px text-[9px] font-semibold text-[#8663a8]">
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
                    background: steps[i + 1].state === "Done" ? STATE_STYLE.Done.dot : "#e2ded6",
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
