import type { DashboardAlertItem } from "@/lib/types";
import { AlertTriangle, AlertOctagon, Info } from "lucide-react";

const SEVERITY_STYLE: Record<DashboardAlertItem["severity"], { icon: typeof AlertTriangle; classes: string }> = {
  critical: { icon: AlertOctagon, classes: "border-rose-200 bg-rose-50 text-rose-800" },
  warning: { icon: AlertTriangle, classes: "border-amber-200 bg-amber-50 text-amber-800" },
  info: { icon: Info, classes: "border-sky-200 bg-sky-50 text-sky-800" },
};

export default function AlertsPanel({
  alerts,
  extra,
}: {
  alerts: DashboardAlertItem[];
  extra?: { title: string; detail: string }[];
}) {
  const items = [...alerts];
  if (items.length === 0 && (!extra || extra.length === 0)) {
    return (
      <div className="rounded-xl border border-emerald-100 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
        No active alerts — the program is within expected thresholds.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {items.map((a, i) => {
        const { icon: Icon, classes } = SEVERITY_STYLE[a.severity];
        return (
          <div key={i} className={`flex items-start gap-3 rounded-xl border px-4 py-3 text-sm ${classes}`}>
            <Icon className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-semibold">{a.title}</p>
              <p className="mt-0.5 text-xs opacity-90">{a.detail}</p>
            </div>
          </div>
        );
      })}
      {extra?.map((a, i) => (
        <div key={`extra-${i}`} className="flex items-start gap-3 rounded-xl border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">
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
