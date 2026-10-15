import { useEffect, useMemo, useState, type ReactElement, type ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Pie,
  PieChart,
  Radar,
  RadarChart,
  RadialBar,
  RadialBarChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  Treemap,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import api from "@/lib/api";
import { ROLE, roleProps, textOn, vsProgramme, type Role } from "@/lib/chartPalette";
import RoleKey from "@/components/dashboard/RoleKey";

/*
 * Programme-wide charts, each a different type, built only from real transfer
 * records. The lab-side funnel (oocytes, embryos, live births) is left out on
 * purpose: those figures come from the demo seeder, not from recorded data.
 *
 * These use the whole programme, not the dashboard filters, and say so.
 * A bar, segment, bubble or point from fewer than SMALL_SAMPLE transfers is
 * drawn faded, so a thin sample never looks as solid as a large one.
 */

const SMALL_SAMPLE = 20;
const AXIS = "#8a9a92";
const GRID = "rgba(46, 54, 69, 0.07)";
const INK = "#2E3645";

interface Kpis {
  pregnant: number;
  open: number;
  with_outcome: number;
  total_transfers: number;
  fresh_vs_frozen: Record<string, { n: number; pregnant: number; rate: number }>;
}
interface TrendRow {
  month: string;
  n_transfers: number;
  n_pregnant: number;
  pregnancy_rate: number | null;
}
interface ProtocolRow {
  protocol_name: string;
  n_transfers: number;
  n_pregnant: number;
  pregnancy_rate: number;
  ci_lower: number;
  ci_upper: number;
}
interface BreedRow {
  donor_breed: string;
  n_transfers: number;
  pregnancy_rate: number;
}
interface DonorRow {
  donor_tag: string;
  breed: string | null;
  n_transfers: number;
  n_pregnant: number;
  pregnancy_rate: number;
}
interface BinRow {
  range: string;
  n: number;
  pregnancy_rate: number | null;
  ci_lower: number | null;
  ci_upper: number | null;
}

interface Data {
  kpis: Kpis | null;
  trends: TrendRow[] | null;
  protocols: ProtocolRow[] | null;
  breeds: BreedRow[] | null;
  donors: DonorRow[] | null;
  bins: BinRow[] | null;
}

const pct = (v: number | null | undefined) => (v == null ? "—" : `${(v * 100).toFixed(1)}%`);

// Legend and tooltip text takes the series colour by default, which fails on
// pale fills, so it is set in ink here.
const ink = (text: ReactNode) => <span style={{ color: INK }}>{text}</span>;

function Card({ title, caption, children, wide = false }: { title: string; caption: string; children: ReactNode; wide?: boolean }) {
  return (
    <div className={`dash-card ${wide ? "xl:col-span-2" : ""}`}>
      <h3 className="text-base font-semibold dash-heading">{title}</h3>
      <p className="mb-3 mt-1 text-xs dash-muted">{caption}</p>
      {children}
    </div>
  );
}

function Empty({ children }: { children: ReactNode }) {
  return <p className="py-10 text-center text-sm dash-muted">{children}</p>;
}

// Treemap cell: the label colour follows the block, since the blocks run from light to dark.
function TreemapCell(props: { x: number; y: number; width: number; height: number; name: string; fill: string; outline?: string }) {
  const { x, y, width, height, name, fill, outline } = props;
  const showLabel = width > 64 && height > 26;
  return (
    <g>
      <rect x={x} y={y} width={width} height={height} fill={fill} stroke={outline ?? "#ffffff"} strokeWidth={2} />
      {showLabel && (
        <text x={x + 8} y={y + 18} fill={textOn(fill)} stroke="none" fontSize={11} fontWeight={600}>
          {name}
        </text>
      )}
    </g>
  );
}

function Frame({ height, children }: { height: number; children: ReactElement }) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        {children}
      </ResponsiveContainer>
    </div>
  );
}

/** How the monthly chart is drawn: the same data as bars and a line, or either alone. */
type MonthlyView = "combo" | "bars" | "line";
const MONTHLY_VIEWS: { value: MonthlyView; label: string }[] = [
  { value: "combo", label: "Bars and line" },
  { value: "bars", label: "Transfers only" },
  { value: "line", label: "Pregnancy rate only" },
];

export default function ChartGallery() {
  const [data, setData] = useState<Data>({ kpis: null, trends: null, protocols: null, breeds: null, donors: null, bins: null });
  const [failed, setFailed] = useState(false);
  const [monthlyView, setMonthlyView] = useState<MonthlyView>("combo");

  useEffect(() => {
    Promise.allSettled([
      api.get<Kpis>("/analytics/kpis"),
      api.get<TrendRow[]>("/analytics/trends"),
      api.get<{ protocols: ProtocolRow[] }>("/analytics/protocols"),
      api.get<{ breeds: BreedRow[] }>("/analytics/breeds"),
      api.get<{ donors: DonorRow[] }>("/analytics/donors"),
      api.get<{ cl_measure: { bins: BinRow[] } }>("/analytics/biomarkers"),
    ]).then(([k, t, p, b, d, bi]) => {
      setData({
        kpis: k.status === "fulfilled" ? k.value.data : null,
        trends: t.status === "fulfilled" ? t.value.data : null,
        protocols: p.status === "fulfilled" ? p.value.data.protocols : null,
        breeds: b.status === "fulfilled" ? b.value.data.breeds : null,
        donors: d.status === "fulfilled" ? d.value.data.donors : null,
        bins: bi.status === "fulfilled" ? bi.value.data.cl_measure.bins : null,
      });
      if ([k, t, p, b, d, bi].every((r) => r.status === "rejected")) setFailed(true);
    });
  }, []);

  // The programme's pregnancy rate: the yardstick for every above/below colour.
  const programmeRate = data.kpis && data.kpis.with_outcome > 0 ? data.kpis.pregnant / data.kpis.with_outcome : null;

  // 1. Donut: outcome split.
  const outcome = useMemo(
    () => (data.kpis ? [{ name: "Pregnant", value: data.kpis.pregnant }, { name: "Open", value: data.kpis.open }] : null),
    [data.kpis],
  );

  // 2. Radial: fresh vs frozen.
  const freshFrozen = useMemo(() => {
    const f = data.kpis?.fresh_vs_frozen;
    if (!f) return null;
    return Object.entries(f).map(([name, v]) => ({
      name,
      rate: v.rate * 100,
      n: v.n,
      role: vsProgramme(v.rate, programmeRate),
    }));
  }, [data.kpis, programmeRate]);

  // 3. Combo: monthly volume (bars) and pregnancy rate (line).
  const monthly = useMemo(
    () => data.trends?.map((r) => ({ month: r.month, transfers: r.n_transfers, rate: r.pregnancy_rate == null ? null : r.pregnancy_rate * 100 })) ?? null,
    [data.trends],
  );

  // 4. Stacked area: pregnant vs not, per month.
  const stackedMonthly = useMemo(
    () => data.trends?.map((r) => ({ month: r.month, pregnant: r.n_pregnant, notPregnant: r.n_transfers - r.n_pregnant })) ?? null,
    [data.trends],
  );

  // 5. Waterfall: transfers down to pregnancies. Each step is a real count.
  const waterfall = useMemo(() => {
    const k = data.kpis;
    if (!k) return null;
    const noOutcome = k.total_transfers - k.with_outcome;
    return [
      { name: "Transfers", base: 0, value: k.total_transfers, kind: "volume" },
      { name: "No outcome yet", base: k.with_outcome, value: noOutcome, kind: "pending" },
      { name: "With outcome", base: 0, value: k.with_outcome, kind: "volume" },
      { name: "Open", base: k.pregnant, value: k.open, kind: "negative" },
      { name: "Pregnant", base: 0, value: k.pregnant, kind: "positive" },
    ];
  }, [data.kpis]);

  // 6. Radar: main protocols on rate, lower bound and share of volume.
  const radar = useMemo(() => {
    if (!data.protocols) return null;
    const rows = data.protocols.filter((p) => p.n_transfers >= 5);
    const total = rows.reduce((s, p) => s + p.n_transfers, 0) || 1;
    const series = rows.map((p, i) => ({
      key: `p${i}`,
      label: p.protocol_name.length > 22 ? `${p.protocol_name.slice(0, 21)}…` : p.protocol_name,
      n: p.n_transfers,
      color: ROLE[vsProgramme(p.pregnancy_rate, programmeRate)].ink,
    }));
    const axes = [
      { axis: "Pregnancy rate", ...Object.fromEntries(rows.map((p, i) => [`p${i}`, p.pregnancy_rate * 100])) },
      { axis: "Lower 95% bound", ...Object.fromEntries(rows.map((p, i) => [`p${i}`, p.ci_lower * 100])) },
      { axis: "Share of transfers", ...Object.fromEntries(rows.map((p, i) => [`p${i}`, (p.n_transfers / total) * 100])) },
    ];
    return { axes, series };
  }, [data.protocols, programmeRate]);

  // 7. Bubble scatter: donors, transfers against pregnancy rate.
  const donors = useMemo(
    () =>
      data.donors
        ?.filter((d) => d.n_transfers > 0)
        .map((d) => ({
          x: d.n_transfers,
          y: d.pregnancy_rate * 100,
          z: d.n_transfers,
          tag: d.donor_tag,
          breed: d.breed ?? "Unknown",
          role: vsProgramme(d.pregnancy_rate, programmeRate),
        })) ?? null,
    [data.donors, programmeRate],
  );

  // 8. Treemap: share of transfers by breed.
  const treemap = useMemo(
    () =>
      data.breeds
        ?.filter((b) => b.n_transfers > 0)
        .sort((a, b) => b.n_transfers - a.n_transfers)
        .map((b) => ({ name: b.donor_breed, size: b.n_transfers, rate: b.pregnancy_rate * 100, fill: ROLE[vsProgramme(b.pregnancy_rate, programmeRate)].fill, outline: ROLE[vsProgramme(b.pregnancy_rate, programmeRate)].stroke ?? "#ffffff" })) ?? null,
    [data.breeds, programmeRate],
  );

  // 9. Stacked horizontal bar: protocol outcome counts.
  const protocolStack = useMemo(
    () =>
      data.protocols
        ?.filter((p) => p.n_transfers > 0)
        .map((p) => ({
          label: p.protocol_name.length > 26 ? `${p.protocol_name.slice(0, 25)}…` : p.protocol_name,
          full: p.protocol_name,
          pregnant: p.n_pregnant,
          notPregnant: p.n_transfers - p.n_pregnant,
          n: p.n_transfers,
        }))
        .sort((a, b) => b.n - a.n) ?? null,
    [data.protocols],
  );

  // 10. Column: pregnancy rate by corpus luteum size.
  const bins = useMemo(
    () =>
      data.bins
        ?.filter((b) => b.n > 0)
        .map((b) => ({
          range: b.range,
          rate: b.pregnancy_rate == null ? null : b.pregnancy_rate * 100,
          n: b.n,
          ci: b.ci_lower == null || b.ci_upper == null ? "—" : `${(b.ci_lower * 100).toFixed(0)}–${(b.ci_upper * 100).toFixed(0)}%`,
        })) ?? null,
    [data.bins],
  );

  if (failed) {
    return (
      <div className="dash-card">
        <h3 className="text-base font-semibold dash-heading">Programme charts</h3>
        <Empty>These charts could not be loaded. Try refreshing the page.</Empty>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-5 xl:grid-cols-2">
      <div className="dash-card flex flex-wrap items-center gap-x-5 gap-y-2 text-xs dash-muted xl:col-span-2">
        <span className="font-semibold dash-heading">Colour key</span>
        <RoleKey items={[
          { role: "positive", label: "Pregnant, or at or above the programme rate" },
          { role: "negative", label: "Open or not pregnant, or below the programme rate" },
          { role: "volume", label: "Transfers or oocytes counted (a volume, not an outcome)" },
          { role: "transfer", label: "Transfer event" },
          { role: "pending", label: "No outcome recorded yet" },
        ]} />
        {programmeRate != null && (
          <span className="dash-heading">Programme rate: {(programmeRate * 100).toFixed(1)}% (pregnant ÷ transfers with an outcome)</span>
        )}
      </div>
      {/* 1. Donut */}
      <Card
        title="Outcome split"
        caption={data.kpis ? `Pregnant vs open, of ${data.kpis.with_outcome} transfers with a recorded outcome (${data.kpis.total_transfers} in total). Periwinkle is pregnant, pink is open.` : "Loading outcomes…"}
      >
        {outcome ? (
          <div className="relative">
            <Frame height={260}>
              <PieChart>
                <Pie data={outcome} dataKey="value" nameKey="name" innerRadius={62} outerRadius={96} paddingAngle={2} stroke="none">
                  <Cell {...roleProps("positive")} />
                  <Cell {...roleProps("negative")} />
                </Pie>
                <Tooltip />
                <Legend verticalAlign="bottom" height={28} formatter={(v) => ink(v)} />
              </PieChart>
            </Frame>
            <div className="pointer-events-none absolute inset-0 flex items-center justify-center pb-7">
              <div className="text-center">
                <div className="text-2xl font-semibold dash-heading">{pct(data.kpis!.pregnant / data.kpis!.with_outcome)}</div>
                <div className="text-[11px] dash-muted">pregnant</div>
              </div>
            </div>
          </div>
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 2. Radial */}
      <Card
        title="Transfer type"
        caption="Pregnancy rate for fresh and frozen embryos. Each ring is one group; the legend gives its number of transfers. Faded rings have fewer than 20."
      >
        {freshFrozen ? (
          <Frame height={260}>
            <RadialBarChart innerRadius="30%" outerRadius="95%" data={freshFrozen} startAngle={180} endAngle={-180}>
              <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
              <RadialBar dataKey="rate" background={{ fill: "rgba(46, 54, 69, 0.05)" }} cornerRadius={8}>
                {freshFrozen.map((f) => (
                  <Cell key={f.name} {...roleProps(f.role)} fillOpacity={f.n < SMALL_SAMPLE ? 0.45 : 1} />
                ))}
              </RadialBar>
              <Tooltip formatter={(v, _n, item) => [`${Number(v).toFixed(1)}% (n=${(item.payload as { n: number }).n})`, (item.payload as { name: string }).name]} />
              <Legend iconSize={10} verticalAlign="bottom" formatter={(_v, entry) => ink(`${(entry.payload as { name: string; n: number }).name} · n=${(entry.payload as { n: number }).n}`)} />
            </RadialBarChart>
          </Frame>
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 3. Combo */}
      <Card
        wide
        title="Monthly volume and pregnancy rate"
        caption="Light blue bars are the embryos transferred each month; the periwinkle line is that month's pregnancy rate. Months with few transfers carry little weight."
      >
        {monthly ? (
          <>
            <div className="mb-2 flex flex-wrap gap-2 text-xs">
              {MONTHLY_VIEWS.map((v) => (
                <button
                  key={v.value}
                  type="button"
                  onClick={() => setMonthlyView(v.value)}
                  aria-pressed={monthlyView === v.value}
                  className={`rounded-full px-3 py-1 font-semibold transition ${
                    monthlyView === v.value ? "bg-white shadow-sm dash-heading" : "bg-black/[0.045] dash-muted hover:bg-white/70"
                  }`}
                >
                  {v.label}
                </button>
              ))}
            </div>
            <Frame height={280}>
              <ComposedChart data={monthly} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
                <XAxis dataKey="month" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
                <YAxis yAxisId="left" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} allowDecimals={false} />
                <YAxis yAxisId="right" orientation="right" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} unit="%" domain={[0, 100]} />
                <Tooltip formatter={(v, name) => (name === "rate" ? `${Number(v).toFixed(1)}%` : v)} />
                <Legend verticalAlign="top" height={28} formatter={(v) => ink(v === "transfers" ? "Transfers" : "Pregnancy rate")} />
                {monthlyView !== "line" && (
                  <Bar yAxisId="left" dataKey="transfers" {...roleProps("volume")} radius={[6, 6, 0, 0]} name="transfers" />
                )}
                {monthlyView !== "bars" && (
                  <Line yAxisId="right" type="monotone" dataKey="rate" stroke={ROLE.positive.fill} strokeWidth={2.2} dot={{ r: 4 }} connectNulls name="rate" />
                )}
              </ComposedChart>
            </Frame>
          </>
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 4. Stacked area */}
      <Card
        title="Monthly pregnant vs not pregnant"
        caption="Each month's transfers split into pregnant (periwinkle) and not pregnant or no record (pink). Stacked, so the top edge is the month's total."
      >
        {stackedMonthly ? (
          <Frame height={250}>
            <AreaChart data={stackedMonthly} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
              <XAxis dataKey="month" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
              <YAxis stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} allowDecimals={false} />
              <Tooltip />
              <Legend verticalAlign="top" height={26} formatter={(v) => ink(v === "pregnant" ? "Pregnant" : "Not pregnant / no record")} />
              <Area type="monotone" dataKey="notPregnant" stackId="m" stroke={ROLE.negative.stroke} fill={ROLE.negative.fill} fillOpacity={1} name="notPregnant" />
              <Area type="monotone" dataKey="pregnant" stackId="m" stroke={ROLE.positive.fill} fill={ROLE.positive.fill} fillOpacity={0.85} name="pregnant" />
            </AreaChart>
          </Frame>
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 5. Waterfall */}
      <Card
        title="From transfers to pregnancies"
        caption="Light blue steps are totals. The dashed step is transfers with no outcome yet, and pink steps are open transfers. What remains, in periwinkle, is the pregnant count."
      >
        <RoleKey items={[
          { role: "volume", label: "Totals" },
          { role: "pending", label: "No outcome yet" },
          { role: "negative", label: "Open" },
          { role: "positive", label: "Pregnant" },
        ]} />
        {waterfall ? (
          <Frame height={250}>
            <BarChart data={waterfall} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
              <XAxis dataKey="name" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} interval={0} />
              <YAxis stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} allowDecimals={false} />
              <Tooltip formatter={(v) => [v, "Count"]} />
              <Bar dataKey="base" stackId="w" fill="transparent" isAnimationActive={false} />
              <Bar dataKey="value" stackId="w" radius={[6, 6, 0, 0]} name="value">
                {waterfall.map((w) => (
                  <Cell key={w.name} {...roleProps(w.kind as Role)} />
                ))}
              </Bar>
            </BarChart>
          </Frame>
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 6. Radar */}
      <Card
        wide
        title="Protocol profile"
        caption="Each protocol with at least 5 transfers, on pregnancy rate, the lower bound of its 95% interval, and its share of all transfers. Further out is better on the first two; on the third, further out means more used. The scale runs 0–60%. A violet outline is at or above the programme rate, rose is below it."
      >
        {radar && radar.series.length > 0 ? (
          <Frame height={320}>
            <RadarChart data={radar.axes} outerRadius="72%">
              <PolarGrid stroke={GRID} />
              <PolarAngleAxis dataKey="axis" tick={{ fill: INK, fontSize: 11 }} />
              <PolarRadiusAxis angle={90} domain={[0, 60]} tick={false} axisLine={false} />
              {radar.series.map((s) => (
                <Radar key={s.key} name={`${s.label} (n=${s.n})`} dataKey={s.key} stroke={s.color} fill={s.color} fillOpacity={0.18} strokeWidth={2} />
              ))}
              <Tooltip />
              <Legend layout="vertical" verticalAlign="middle" align="right" formatter={(v) => ink(v)} wrapperStyle={{ fontSize: 11, paddingLeft: 8 }} />
            </RadarChart>
          </Frame>
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 7. Bubble scatter */}
      <Card
        title="Donor performance"
        caption="One bubble per donor: how many transfers it has had (across) against its pregnancy rate (up). Bigger bubbles have more transfers. Periwinkle bubbles are at or above the programme rate, pink below it. Donors with fewer than 20 transfers are faded."
      >
        <RoleKey items={[
          { role: "positive", label: "At or above the programme rate" },
          { role: "negative", label: "Below the programme rate" },
        ]} />
        {donors ? (
          <Frame height={280}>
            <ScatterChart margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} />
              <XAxis type="number" dataKey="x" name="transfers" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} allowDecimals={false} />
              <YAxis type="number" dataKey="y" name="pregnancy rate" unit="%" domain={[0, 100]} stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
              <ZAxis type="number" dataKey="z" range={[60, 360]} />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const d = payload[0].payload as { tag: string; breed: string; x: number; y: number };
                  return (
                    <div className="rounded-xl border border-white/80 bg-white/95 px-3 py-2 text-xs shadow" style={{ color: INK }}>
                      <div className="font-semibold">Donor {d.tag}</div>
                      <div>{d.breed}</div>
                      <div>
                        {d.x} transfers · {d.y.toFixed(1)}% pregnant
                      </div>
                    </div>
                  );
                }}
              />
              <Scatter data={donors} name="donors">
                {donors.map((d) => (
                  <Cell key={d.tag} {...roleProps(d.role)} fillOpacity={d.x < SMALL_SAMPLE ? 0.45 : 0.85} />
                ))}
              </Scatter>
            </ScatterChart>
          </Frame>
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 8. Treemap */}
      <Card
        title="Transfers by donor breed"
        caption="Each block is a breed, sized by its number of transfers. Periwinkle blocks are at or above the programme rate, pink below it. The tooltip gives its pregnancy rate. Small blocks have fewer than 20 transfers."
      >
        <RoleKey items={[
          { role: "positive", label: "At or above the programme rate" },
          { role: "negative", label: "Below the programme rate" },
        ]} />
        {treemap ? (
          <Frame height={280}>
            <Treemap data={treemap} dataKey="size" aspectRatio={4 / 3} stroke="#ffffff" isAnimationActive={false} content={<TreemapCell x={0} y={0} width={0} height={0} name="" fill="" />}>
              <Tooltip formatter={(v, _n, item) => [`${v} transfers · ${Number((item.payload as { rate: number }).rate).toFixed(1)}% pregnant`, (item.payload as { name: string }).name]} />
            </Treemap>
          </Frame>
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 9. Stacked horizontal bar */}
      <Card
        title="Outcomes by protocol"
        caption="Pregnant (periwinkle) and not-pregnant (pink) transfer counts for each protocol, so the sample behind every rate is visible."
      >
        {protocolStack ? (
          <Frame height={250}>
            <BarChart data={protocolStack} layout="vertical" margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} horizontal={false} />
              <XAxis type="number" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} allowDecimals={false} />
              <YAxis type="category" dataKey="label" width={170} stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
              <Tooltip
                formatter={(v, name) => [v, name === "pregnant" ? "Pregnant" : "Not pregnant / no record"]}
                labelFormatter={(_l, payload) => (payload?.[0]?.payload as { full?: string } | undefined)?.full ?? ""}
              />
              <Legend verticalAlign="top" height={26} formatter={(v) => ink(v === "pregnant" ? "Pregnant" : "Not pregnant / no record")} />
              <Bar dataKey="pregnant" stackId="p" {...roleProps("positive")} name="pregnant" />
              <Bar dataKey="notPregnant" stackId="p" {...roleProps("negative")} radius={[0, 6, 6, 0]} name="notPregnant" />
            </BarChart>
          </Frame>
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 10. Column */}
      <Card
        title="Pregnancy rate by corpus luteum size"
        caption="Ultrasound CL size at transfer, in millimetres. Periwinkle columns are at or above the programme rate, pink below it. The tooltip gives the 95% interval and the number of transfers. Faded columns have fewer than 20."
      >
        <RoleKey items={[
          { role: "positive", label: "At or above the programme rate" },
          { role: "negative", label: "Below the programme rate" },
        ]} />
        {bins ? (
          <Frame height={250}>
            <BarChart data={bins} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
              <XAxis dataKey="range" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
              <YAxis stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} unit="%" domain={[0, 100]} />
              <Tooltip formatter={(v, _n, item) => [`${Number(v).toFixed(1)}% · n=${(item.payload as { n: number }).n} · CI ${(item.payload as { ci: string }).ci}`, "Pregnancy rate"]} />
              <Bar dataKey="rate" radius={[6, 6, 0, 0]} name="rate">
                {bins.map((b) => (
                  <Cell key={b.range} {...roleProps(vsProgramme(b.rate == null ? null : b.rate / 100, programmeRate))} fillOpacity={b.n < SMALL_SAMPLE ? 0.45 : 1} />
                ))}
              </Bar>
            </BarChart>
          </Frame>
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>
    </div>
  );
}
