import type { DashboardAlertItem } from "@/lib/types";
import { AlertTriangle, AlertOctagon, Info, CheckCircle2 } from "lucide-react";

const SEVERITY_STYLE: Record<DashboardAlertItem["severity"], { icon: typeof AlertTriangle; classes: string }> = {
  critical: { icon: AlertOctagon, classes: "border-[rgba(179,69,63,0.28)] bg-[rgba(185,142,168,0.16)] text-[#9d3730]" },
  warning: { icon: AlertTriangle, classes: "border-[rgba(35,131,111,0.32)] bg-[rgba(208,164,94,0.18)] text-[#7a5a12]" },
  info: { icon: Info, classes: "border-[rgba(79,143,125,0.32)] bg-[rgba(79,143,125,0.16)] text-[#2f6b5c]" },
};

export default function AlertsPanel({
  alerts,
  extra,
}: {
  alerts: DashboardAlertItem[];
  extra?: { title: string; detail: string }[];
}) {
  if (alerts.length === 0 && (!extra || extra.length === 0)) {
    return (
      <div className="flex items-start gap-3 rounded-2xl border border-[rgba(142,182,155,0.34)] bg-[rgba(142,182,155,0.16)] px-4 py-3 text-sm text-[#235347]">
        <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
        <span>No active alerts — the program is within expected thresholds.</span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {alerts.map((a, i) => {
        const { icon: Icon, classes } = SEVERITY_STYLE[a.severity];
        return (
          <div key={i} className={`flex items-start gap-3 rounded-2xl border px-4 py-3 text-sm ${classes}`}>
            <Icon className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-semibold">{a.title}</p>
              <p className="mt-0.5 text-xs opacity-90">{a.detail}</p>
            </div>
          </div>
        );
      })}
      {extra?.map((a, i) => (
        <div
          key={`extra-${i}`}
          className="flex items-start gap-3 rounded-2xl border border-[rgba(79,143,125,0.32)] bg-[rgba(79,143,125,0.16)] px-4 py-3 text-sm text-[#2f6b5c]"
        >
          <Info className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-semibold">{a.title}</p>
            <p className="mt-0.5 text-xs opacity-90">{a.detail}</p>
          </div>
        </div>
      ))}
    </div>
  );
}
