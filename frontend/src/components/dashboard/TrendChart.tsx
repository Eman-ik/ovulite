import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardTrendResponse } from "@/lib/types";

export default function TrendChart({
  data,
  title,
  color = "#059669",
}: {
  data: DashboardTrendResponse | null;
  title: string;
  color?: string;
}) {
  if (!data) return <div className="text-sm text-gray-500">Loading trend…</div>;

  const points = data.points.map((p) => ({ label: p.bucket_label, value: p.value, n: p.n }));
  const gradientId = `trend-fill-${title.replace(/\s+/g, "-")}`;

  return (
    <div>
      <p className="mb-2 text-xs text-gray-500">
        Granularity: {data.granularity} · grayed points have few underlying records
      </p>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={points} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.4} />
                <stop offset="95%" stopColor={color} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
            <XAxis dataKey="label" stroke="#6B7280" tickLine={false} axisLine={false} fontSize={11} />
            <YAxis stroke="#6B7280" tickLine={false} axisLine={false} tickFormatter={(v) => `${v}%`} />
            <Tooltip
              formatter={((value: unknown, _name: unknown, item: { payload?: { n?: number } }) => [
                value === null || value === undefined ? "No data" : `${value}% (n=${item?.payload?.n ?? 0})`,
                title,
              ]) as (value: unknown, name: unknown, item: unknown) => [string, string]}
              contentStyle={{ borderRadius: 16, border: "1px solid #E5E7EB", background: "rgba(255,255,255,0.98)" }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={3}
              dot={{ r: 4, fill: color }}
              fill={`url(#${gradientId})`}
              connectNulls
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
