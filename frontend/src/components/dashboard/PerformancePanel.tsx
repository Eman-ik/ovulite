import { useEffect, useState } from "react";
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

  return (
    <Tabs value={active} onValueChange={(v) => setActive(v as Dimension)}>
      <TabsList>
        {dimensions.map((d) => (
          <TabsTrigger key={d} value={d}>
            {DIMENSION_LABEL[d]}
          </TabsTrigger>
        ))}
      </TabsList>
      {dimensions.map((d) => (
        <TabsContent key={d} value={d}>
          {loading && !current ? (
            <div className="py-6 text-center text-sm text-gray-400">Loading…</div>
          ) : !current || current.rows.length === 0 ? (
            <div className="py-6 text-center text-sm text-gray-400">No data for this filter selection.</div>
          ) : (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-left text-xs uppercase tracking-wide text-gray-500">
                  <th className="py-2 pr-3">{DIMENSION_LABEL[d].slice(0, -1)}</th>
                  <th className="py-2 pr-3">Transfers</th>
                  <th className="py-2 pr-3">Pregnancy Rate</th>
                </tr>
              </thead>
              <tbody>
                {current.rows.map((r) => (
                  <tr key={r.id} className="border-b border-gray-50 last:border-0">
                    <td className="py-2 pr-3 font-medium text-gray-800">{r.label}</td>
                    <td className="py-2 pr-3 text-gray-600">{r.n_transfers}</td>
                    <td className="py-2 pr-3">
                      {r.insufficient_data ? (
                        <span className="italic text-gray-400">insufficient data (n&lt;5)</span>
                      ) : (
                        <span className="font-semibold text-emerald-700">{r.pregnancy_rate}%</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </TabsContent>
      ))}
    </Tabs>
  );
}
