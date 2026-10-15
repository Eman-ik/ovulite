import { CHART_SERIES } from "@/lib/chartPalette";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import api from "@/lib/api";
import type { DashboardFilterValues, DashboardPerformanceResponse } from "@/lib/types";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";

type Dimension = DashboardPerformanceResponse["dimension"];

const DIMENSION_LABEL: Record<Dimension, string> = {
  donor: "Donors",
  sire: "Sires",
  protocol: "Protocols",
  technician: "Technicians",
};

/** Green shades cycled across bars so rows stay separable. */
const BAR_COLORS = CHART_SERIES;

export default function PerformancePanel({
  filters,
  dimensions,
}: {
  filters: DashboardFilterValues;
  dimensions: Dimension[];
}) {
  const [active, setActive] = useState<Dimension>(dimensions[0]);
  const [data, setData] = useState<Record<string, DashboardPerformanceResponse | null>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!dimensions.includes(active)) setActive(dimensions[0]);
  }, [dimensions, active]);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api
      .get<DashboardPerformanceResponse>("/dashboard/performance", {
        params: { dimension: active, limit: 8, ...filters },
      })
      .then((res) => {
        if (!cancelled) setData((prev) => ({ ...prev, [active]: res.data }));
      })
      .catch(() => {
        if (!cancelled) setData((prev) => ({ ...prev, [active]: null }));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [active, filters]);

  const current = data[active];
  const chartRows = current?.rows.filter((r) => !r.insufficient_data) ?? [];

  return (
    <Tabs value={active} onValueChange={(v) => setActive(v as Dimension)}>
      <TabsList className="bg-black/[0.045]">
        {dimensions.map((d) => (
          <TabsTrigger key={d} value={d} className="data-[state=active]:bg-white data-[state=active]:shadow-sm">
            {DIMENSION_LABEL[d]}
          </TabsTrigger>
        ))}
      </TabsList>
      {dimensions.map((d) => (
        <TabsContent key={d} value={d}>
          {loading && !current ? (
            <div className="py-6 text-center text-sm dash-muted">Loading…</div>
          ) : !current || current.rows.length === 0 ? (
            <div className="py-6 text-center text-sm dash-muted">No data for this filter selection.</div>
          ) : (
            <div className="grid gap-6 lg:grid-cols-2">
              {chartRows.length > 1 && (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={chartRows} layout="vertical" margin={{ top: 4, right: 16, left: 8, bottom: 4 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" horizontal={false} />
                      <XAxis
                        type="number"
                        stroke="#94A9BE"
                        tickLine={false}
                        axisLine={false}
                        fontSize={11}
                        tickFormatter={(v) => `${v}%`}
                      />
                      <YAxis
                        type="category"
                        dataKey="label"
                        width={92}
                        stroke="#94A9BE"
                        tickLine={false}
                        axisLine={false}
                        fontSize={11}
                      />
                      <Tooltip
                        formatter={((value: unknown) => [`${value}%`, "Pregnancy Rate"]) as (value: unknown) => [string, string]}
                        contentStyle={{
                          borderRadius: 14,
                          border: "1px solid rgba(46, 54, 69,0.1)",
                          background: "#ffffff",
                          boxShadow: "0 12px 32px -18px rgba(46, 54, 69,0.35)",
                          color: "#2E3645",
                        }}
                        cursor={{ fill: "rgba(255,255,255,0.04)" }}
                      />
                      <Bar dataKey="pregnancy_rate" radius={[0, 8, 8, 0]}>
                        {chartRows.map((r, i) => (
                          <Cell key={r.id} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}

              <table className="w-full self-start text-sm">
                <thead>
                  <tr className="border-b border-[var(--border)] text-left text-[11px] uppercase tracking-wide dash-muted">
                    <th className="py-2 pr-3 font-medium">{DIMENSION_LABEL[d].slice(0, -1)}</th>
                    <th className="py-2 pr-3 font-medium">Transfers</th>
                    <th className="py-2 pr-3 font-medium">Pregnancy Rate</th>
                  </tr>
                </thead>
                <tbody>
                  {current.rows.map((r) => (
                    <tr key={r.id} className="border-b border-[var(--border)] last:border-0">
                      <td className="py-2.5 pr-3 font-medium dash-heading">{r.label}</td>
                      <td className="py-2.5 pr-3 dash-muted">{r.n_transfers}</td>
                      <td className="py-2.5 pr-3">
                        {r.insufficient_data ? (
                          <span className="italic dash-muted opacity-70">insufficient data (n&lt;5)</span>
                        ) : (
                          <span className="font-semibold text-[var(--primary)]">{r.pregnancy_rate}%</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </TabsContent>
      ))}
    </Tabs>
  );
}
