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
  color = "#8fb8de",
}: {
  data: DashboardTrendResponse | null;
  title: string;
  color?: string;
}) {
  if (!data) return <div className="text-sm dash-muted">Loading trend…</div>;

  const points = data.points.map((p) => ({ label: p.bucket_label, value: p.value, n: p.n }));
  const gradientId = `trend-fill-${title.replace(/\s+/g, "-")}`;

  return (
    <div>
      <p className="mb-3 text-xs dash-muted">
        Granularity: {data.granularity} · points with few underlying records read as noisier
      </p>
      <div className="h-60">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={points} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.45} />
                <stop offset="95%" stopColor={color} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(22,24,26,0.07)" vertical={false} />
            <XAxis dataKey="label" stroke="#9aa1aa" tickLine={false} axisLine={false} fontSize={11} />
            <YAxis
              stroke="#9aa1aa"
              tickLine={false}
              axisLine={false}
              fontSize={11}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              formatter={
                ((value: unknown, _name: unknown, item: { payload?: { n?: number } }) => [
                  value === null || value === undefined ? "No data" : `${value}% (n=${item?.payload?.n ?? 0})`,
                  title,
                ]) as (value: unknown, name: unknown, item: unknown) => [string, string]
              }
              contentStyle={{
                borderRadius: 14,
                border: "1px solid rgba(22,24,26,0.1)",
                background: "#ffffff",
                boxShadow: "0 12px 32px -18px rgba(22,24,26,0.35)",
                color: "#16181a",
              }}
              labelStyle={{ color: "#6f7680" }}
              cursor={{ stroke: "rgba(22,24,26,0.18)" }}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2.5}
              dot={{ r: 3, fill: color, stroke: "#ffffff", strokeWidth: 1.5 }}
              activeDot={{ r: 5, fill: color, stroke: "#ffffff", strokeWidth: 2 }}
              fill={`url(#${gradientId})`}
              connectNulls
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
