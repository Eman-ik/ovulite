import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { DashboardTrendResponse } from "@/lib/types";
import { ROLE, verdict } from "@/lib/chartPalette";

export default function TrendChart({
  data,
  title,
  color = ROLE.positive.fill,
}: {
  data: DashboardTrendResponse | null;
  title: string;
  color?: string;
}) {
  if (!data) return <div className="text-sm dash-muted">Loading trend…</div>;

  const points = data.points.map((p) => ({ label: p.bucket_label, value: p.value, n: p.n }));
  const gradientId = `trend-fill-${title.replace(/\s+/g, "-")}`;

  // What the line shows: the overall rate over buckets with 20+ transfers, the range, and
  // which buckets are clearly off that overall rate (whole 95% interval on one side of it).
  const eligible = data.points.filter((p) => p.value != null && p.n >= 20);
  const counted = eligible.map((p) => ({ label: p.bucket_label, rate: (p.value ?? 0) / 100, n: p.n, k: Math.round(((p.value ?? 0) / 100) * p.n) }));
  const totalN = counted.reduce((s, c) => s + c.n, 0);
  const overall = totalN ? counted.reduce((s, c) => s + c.k, 0) / totalN : null;
  const sorted = [...counted].sort((a, b) => a.rate - b.rate);
  const off = overall == null ? [] : counted.filter((c) => verdict(c.k, c.n, overall) !== "volume");
  const takeaway =
    overall == null || sorted.length === 0
      ? `No ${data.granularity} has 20 or more transfers with a result in this range.`
      : `Across ${sorted.length} ${data.granularity}${sorted.length === 1 ? "" : "s"} with 20 or more transfers, the rate averages ${(overall * 100).toFixed(1)}%, ranging from ${(sorted[0].rate * 100).toFixed(1)}% (${sorted[0].label}) to ${(sorted[sorted.length - 1].rate * 100).toFixed(1)}% (${sorted[sorted.length - 1].label}). ${
          off.length === 0 ? "No single period is clearly different from that average." : `${off.length} ${off.length === 1 ? "period is" : "periods are"} clearly different from it: ${off.map((c) => c.label).join(", ")}.`
        }`;

  return (
    <div>
      <p className="mb-2 text-xs dash-muted">
        Granularity: {data.granularity} · points with few underlying records read as noisier
      </p>
      <p className="mb-3 rounded-xl bg-white/65 px-3 py-2 text-[13px] leading-snug dash-heading" role="note">
        <span className="mr-1.5 font-semibold">What it shows:</span>
        {takeaway}
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
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(46, 54, 69,0.07)" vertical={false} />
            <XAxis dataKey="label" stroke="#94A9BE" tickLine={false} axisLine={false} fontSize={11} />
            <YAxis
              stroke="#94A9BE"
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
                border: "1px solid rgba(46, 54, 69,0.1)",
                background: "#ffffff",
                boxShadow: "0 12px 32px -18px rgba(46, 54, 69,0.35)",
                color: "#2E3645",
              }}
              labelStyle={{ color: "#596070" }}
              cursor={{ stroke: "rgba(46, 54, 69,0.18)" }}
            />
            <Legend
              verticalAlign="top"
              height={28}
              formatter={(v) => <span style={{ color: "#2E3645" }}>{v}</span>}
            />
            <Area
              type="monotone"
              dataKey="value"
              name={title}
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
