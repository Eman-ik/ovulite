import { ROLE, roleProps, vsProgramme } from "@/lib/chartPalette";
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

/** The dashboard filter each dimension slices by. Row ids are the entity ids those filters take. */
const DIMENSION_FILTER: Record<Dimension, keyof DashboardFilterValues> = {
  donor: "donor_id",
  sire: "sire_id",
  protocol: "protocol_id",
  technician: "technician_id",
};

export default function PerformancePanel({
  filters,
  dimensions,
  onSlice,
  visibleFilters,
}: {
  filters: DashboardFilterValues;
  dimensions: Dimension[];
  /** Set or clear the filter for a row. */
  onSlice?: (filterKey: keyof DashboardFilterValues, id: number | null) => void;
  /** Filters this role can see; a row is only clickable when its filter is among them. */
  visibleFilters?: Array<keyof DashboardFilterValues>;
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
  // Yardstick for the bar colours: the transfer-weighted average of the bars on screen.
  const rated = chartRows.filter((r) => r.pregnancy_rate != null);
  const shownTransfers = rated.reduce((s, r) => s + r.n_transfers, 0);
  const shownAverage =
    shownTransfers > 0 ? rated.reduce((s, r) => s + (r.pregnancy_rate ?? 0) * r.n_transfers, 0) / shownTransfers : null;
  // Slicing: clicking a row filters the dashboard to it; clicking the selected row clears it.
  const sliceKey = DIMENSION_FILTER[active];
  const selectedId = filters[sliceKey] ?? null;
  const sliceable = onSlice && (!visibleFilters || visibleFilters.includes(sliceKey));
  const slice = sliceable ? (id: number) => onSlice(sliceKey, selectedId === id ? null : id) : undefined;

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
                        {chartRows.map((r) => (
                          <Cell
                            key={r.id}
                            {...roleProps(vsProgramme(r.pregnancy_rate, shownAverage))}
                            {...(selectedId === r.id ? { stroke: "#2E3645", strokeWidth: 2 } : {})}
                            cursor={slice ? "pointer" : undefined}
                            onClick={slice ? () => slice(r.id) : undefined}
                          />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                  <p className="mt-1 flex flex-wrap items-center gap-x-4 text-[11px] dash-muted">
                    <span className="inline-flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: ROLE.positive.fill }} />
                      At or above the average of these bars
                    </span>
                    <span className="inline-flex items-center gap-1.5">
                      <span className="h-2.5 w-2.5 rounded-full" style={{ background: ROLE.negative.fill, boxShadow: `inset 0 0 0 1px ${ROLE.negative.stroke}` }} />
                      Below it
                    </span>
                  </p>
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
                    <tr
                      key={r.id}
                      className={`border-b border-[var(--border)] last:border-0 ${selectedId === r.id ? "bg-white/60" : ""}`}
                    >
                      <td className="py-2.5 pr-3 font-medium dash-heading">
                        {slice ? (
                          <button
                            type="button"
                            onClick={() => slice(r.id)}
                            aria-pressed={selectedId === r.id}
                            className="text-left underline-offset-4 hover:underline"
                          >
                            {r.label}
                          </button>
                        ) : (
                          r.label
                        )}
                      </td>
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
