import type { DashboardAlertItem } from "@/lib/types";
import { AlertTriangle, AlertOctagon, Info, CheckCircle2 } from "lucide-react";

const SEVERITY_STYLE: Record<DashboardAlertItem["severity"], { icon: typeof AlertTriangle; classes: string }> = {
  critical: { icon: AlertOctagon, classes: "border-[rgba(224,101,111,0.3)] bg-[rgba(224,101,111,0.12)] text-[#f0a4aa]" },
  warning: { icon: AlertTriangle, classes: "border-[rgba(214,178,92,0.3)] bg-[rgba(214,178,92,0.12)] text-[#ddc07a]" },
  info: { icon: Info, classes: "border-[rgba(95,191,159,0.28)] bg-[rgba(95,191,159,0.12)] text-[#8fd8c2]" },
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
      <div className="flex items-start gap-3 rounded-2xl border border-[rgba(127,176,105,0.28)] bg-[rgba(127,176,105,0.12)] px-4 py-3 text-sm text-[#a8cba0]">
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
          className="flex items-start gap-3 rounded-2xl border border-[rgba(95,191,159,0.28)] bg-[rgba(95,191,159,0.12)] px-4 py-3 text-sm text-[#8fd8c2]"
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
