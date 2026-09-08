import type { DashboardAlertItem } from "@/lib/types";
import { AlertTriangle, AlertOctagon, Info, CheckCircle2 } from "lucide-react";

const SEVERITY_STYLE: Record<DashboardAlertItem["severity"], { icon: typeof AlertTriangle; classes: string }> = {
  critical: { icon: AlertOctagon, classes: "border-[rgba(210,86,79,0.28)] bg-[rgba(231,154,154,0.16)] text-[#b8433d]" },
  warning: { icon: AlertTriangle, classes: "border-[rgba(224,171,53,0.32)] bg-[rgba(234,186,107,0.18)] text-[#a1741c]" },
  info: { icon: Info, classes: "border-[rgba(121,198,187,0.32)] bg-[rgba(121,198,187,0.16)] text-[#3d8a80]" },
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
      <div className="flex items-start gap-3 rounded-2xl border border-[rgba(134,197,164,0.34)] bg-[rgba(134,197,164,0.16)] px-4 py-3 text-sm text-[#2f7d5c]">
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
          className="flex items-start gap-3 rounded-2xl border border-[rgba(121,198,187,0.32)] bg-[rgba(121,198,187,0.16)] px-4 py-3 text-sm text-[#3d8a80]"
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
