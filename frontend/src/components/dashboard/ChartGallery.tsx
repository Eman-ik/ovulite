import { useEffect, useMemo, useState, type ReactElement, type ReactNode } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  LabelList,
  Legend,
  Line,
  LineChart,
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
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import api from "@/lib/api";
import type { DashboardFilterValues } from "@/lib/types";
import { ROLE, roleProps, verdict, wilson, type Role } from "@/lib/chartPalette";
import RoleKey from "@/components/dashboard/RoleKey";

/*
 * Programme charts. Data comes from /dashboard/charts under the dashboard filters.
 *
 * Colour is a verdict, not a ranking: a group is coloured positive or negative only
 * when its whole 95% interval sits above or below the programme rate. Otherwise it
 * is the neutral "no clear difference" colour, however far its point estimate
 * wanders. Each card states its finding in a takeaway line, computed from the data.
 *
 * Clicking a bar, slice, bubble or period sets the dashboard filter, so every panel
 * on the page follows. Clicking the active item again clears it.
 */

const SMALL_SAMPLE = 20;
const AXIS = "#8a9a92";
const GRID = "rgba(46, 54, 69, 0.07)";
const INK = "#2E3645";
const FADE = 0.35;

interface Group {
  n_with_outcome: number;
  pregnant: number;
  rate: number | null;
}
interface ChartsData {
  start: string | null;
  end: string | null;
  kpis: {
    pregnant: number;
    open: number;
    with_outcome: number;
    total_transfers: number;
    fresh_vs_frozen: Record<string, Group>;
  };
  trends: { month: string; n_transfers: number; n_with_outcome: number; n_pregnant: number; pregnancy_rate: number | null }[];
  protocols: {
    protocol_id: number | null;
    protocol_name: string;
    n_transfers: number;
    n_with_outcome: number;
    n_pregnant: number;
    pregnancy_rate: number | null;
    ci_lower: number | null;
    ci_upper: number | null;
  }[];
  breeds: { donor_breed: string; n_transfers: number; n_with_outcome: number; n_pregnant: number; pregnancy_rate: number | null }[];
  donors: {
    donor_id: number | null;
    donor_tag: string;
    breed: string | null;
    n_transfers: number;
    n_with_outcome: number;
    n_pregnant: number;
    pregnancy_rate: number | null;
  }[];
  bins: {
    range: string;
    n_transfers: number;
    n_with_outcome: number;
    n_pregnant: number;
    pregnancy_rate: number | null;
    ci_lower: number | null;
    ci_upper: number | null;
  }[];
}

type Period = "month" | "quarter";
type Measure = "rate" | "transfers";

const ink = (text: ReactNode) => <span style={{ color: INK }}>{text}</span>;
const pctText = (v: number) => `${(v * 100).toFixed(1)}%`;
const toPct = (v: number | null | undefined) => (v == null ? null : v * 100);
const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** Monthly rows folded to quarters when the viewer drills up. Rates recompute from counts. */
function regroup(rows: ChartsData["trends"], period: Period) {
  const byKey = new Map<string, { transfers: number; out: number; pregnant: number }>();
  for (const r of rows) {
    const key =
      period === "month"
        ? r.month
        : `${r.month.slice(0, 4)}-Q${Math.floor((Number(r.month.slice(5, 7)) - 1) / 3) + 1}`;
    const cur = byKey.get(key) ?? { transfers: 0, out: 0, pregnant: 0 };
    cur.transfers += r.n_transfers;
    cur.out += r.n_with_outcome;
    cur.pregnant += r.n_pregnant;
    byKey.set(key, cur);
  }
  return [...byKey.entries()].map(([label, v]) => ({
    label,
    transfers: v.transfers,
    out: v.out,
    pregnant: v.pregnant,
    rate: v.out ? v.pregnant / v.out : null,
  }));
}

/** First and last day of a month ("2026-03") or quarter ("2026-Q2"), as ISO dates. */
function periodRange(label: string): { from: string; to: string } {
  const year = Number(label.slice(0, 4));
  let startMonth: number;
  let endMonth: number;
  if (label.includes("Q")) {
    const q = Number(label.slice(-1));
    startMonth = (q - 1) * 3 + 1;
    endMonth = startMonth + 2;
  } else {
    startMonth = Number(label.slice(5, 7));
    endMonth = startMonth;
  }
  const lastDay = new Date(year, endMonth, 0).getDate();
  const pad = (n: number) => String(n).padStart(2, "0");
  return {
    from: `${year}-${pad(startMonth)}-01`,
    to: `${year}-${pad(endMonth)}-${pad(lastDay)}`,
  };
}

/** Two intervals overlap, so neither group is clearly different from the other. */
function overlap(a: [number, number], b: [number, number]) {
  return a[0] <= b[1] && b[0] <= a[1];
}

function Card({
  title,
  caption,
  takeaway,
  controls,
  children,
  wide = false,
}: {
  title: string;
  caption: string;
  takeaway?: string | null;
  controls?: ReactNode;
  children: ReactNode;
  wide?: boolean;
}) {
  return (
    <div className={`dash-card ${wide ? "xl:col-span-2" : ""}`}>
      <h3 className="text-base font-semibold dash-heading">{title}</h3>
      <p className="mb-2 mt-1 text-xs dash-muted">{caption}</p>
      {takeaway && (
        <p className="mb-3 rounded-xl bg-white/65 px-3 py-2 text-[13px] leading-snug dash-heading" role="note">
          <span className="mr-1.5 font-semibold">What it shows:</span>
          {takeaway}
        </p>
      )}
      {controls && <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-2">{controls}</div>}
      {children}
    </div>
  );
}

function Seg<T extends string | number>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5 text-xs">
      <span className="font-medium dash-muted">{label}</span>
      {options.map((o) => (
        <button
          key={String(o.value)}
          type="button"
          onClick={() => onChange(o.value)}
          aria-pressed={value === o.value}
          className={`rounded-full px-3 py-1 font-semibold transition ${
            value === o.value ? "bg-white shadow-sm dash-heading" : "bg-black/[0.045] dash-muted hover:bg-white/70"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
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

function Empty({ children }: { children: ReactNode }) {
  return <p className="py-10 text-center text-sm dash-muted">{children}</p>;
}

const MIN_OPTIONS = [
  { value: 1, label: "All" },
  { value: 5, label: "5+" },
  { value: 10, label: "10+" },
  { value: 20, label: "20+" },
];
const PERIOD_OPTIONS: { value: Period; label: string }[] = [
  { value: "month", label: "Month" },
  { value: "quarter", label: "Quarter" },
];
const MEASURE_OPTIONS: { value: Measure; label: string }[] = [
  { value: "rate", label: "Pregnancy rate" },
  { value: "transfers", label: "Transfers" },
];

export default function ChartGallery({
  filters,
  onFilter,
}: {
  filters: DashboardFilterValues;
  onFilter: (patch: Partial<DashboardFilterValues>) => void;
}) {
  const [data, setData] = useState<ChartsData | null>(null);
  const [failed, setFailed] = useState(false);
  const filterKey = JSON.stringify(filters);

  // Per-chart controls. The viewer's choice of how to draw; nothing here changes the data.
  const [outcomeView, setOutcomeView] = useState<"donut" | "bars">("donut");
  const [radialView, setRadialView] = useState<"radial" | "bars">("radial");
  const [monthlyView, setMonthlyView] = useState<"combo" | "bars" | "line">("combo");
  const [monthlyPeriod, setMonthlyPeriod] = useState<Period>("month");
  const [stackPeriod, setStackPeriod] = useState<Period>("month");
  const [stackMode, setStackMode] = useState<"counts" | "share">("counts");
  const [waterfallView, setWaterfallView] = useState<"waterfall" | "bars">("waterfall");
  const [waterfallMeasure, setWaterfallMeasure] = useState<"count" | "share">("count");
  const [radarView, setRadarView] = useState<"radar" | "bars">("radar");
  const [radarMin, setRadarMin] = useState(5);
  const [donorMin, setDonorMin] = useState(20);
  const [breedMeasure, setBreedMeasure] = useState<Measure>("rate");
  const [breedMin, setBreedMin] = useState(5);
  const [protocolMode, setProtocolMode] = useState<"counts" | "share">("counts");
  const [protocolMin, setProtocolMin] = useState(5);
  const [clView, setClView] = useState<"columns" | "line">("columns");
  const [clMeasure, setClMeasure] = useState<Measure>("rate");

  useEffect(() => {
    let cancelled = false;
    setFailed(false);
    api
      .get<ChartsData>("/dashboard/charts", { params: filters })
      .then((res) => {
        if (!cancelled) setData(res.data);
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
    // filterKey is the serialised filters; the object itself changes identity on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filterKey]);

  // The programme's pregnancy rate under the current filters: the yardstick for every verdict.
  const programmeRate = data && data.kpis.with_outcome > 0 ? data.kpis.pregnant / data.kpis.with_outcome : null;
  const k = data?.kpis;

  /** Click handlers. A click on the active item clears that filter. */
  const toggle = <K extends keyof DashboardFilterValues>(key: K, value: DashboardFilterValues[K]) =>
    onFilter({ [key]: filters[key] === value ? undefined : value } as Partial<DashboardFilterValues>);
  const togglePeriod = (label: string) => {
    const { from, to } = periodRange(label);
    const active = filters.date_from === from && filters.date_to === to;
    onFilter(active ? { date_from: undefined, date_to: undefined } : { date_from: from, date_to: to });
  };
  const isPeriodActive = (label: string) => {
    const { from, to } = periodRange(label);
    return filters.date_from === from && filters.date_to === to;
  };

  // 1. Outcome split. Counts, so pregnant and open are fixed roles.
  const outcome = useMemo(
    () =>
      k
        ? [
            { name: "Pregnant", value: k.pregnant, role: "positive" as Role },
            { name: "Open", value: k.open, role: "negative" as Role },
          ]
        : null,
    [k],
  );

  // 2. Fresh vs frozen: verdict on each group's own interval.
  const freshFrozen = useMemo(() => {
    if (!k) return null;
    return Object.entries(k.fresh_vs_frozen)
      .filter(([, g]) => g.rate != null)
      .map(([name, g]) => ({
        name,
        rate: (g.rate ?? 0) * 100,
        n: g.n_with_outcome,
        k: g.pregnant,
        role: verdict(g.pregnant, g.n_with_outcome, programmeRate),
        active: filters.fresh_or_frozen === name,
      }));
  }, [k, programmeRate, filters.fresh_or_frozen]);

  // 3. Monthly volume and rate, per month or per quarter.
  const monthly = useMemo(
    () =>
      data
        ? regroup(data.trends, monthlyPeriod).map((r) => ({
            period: r.label,
            transfers: r.transfers,
            rate: toPct(r.rate),
            k: r.pregnant,
            n: r.out,
          }))
        : null,
    [data, monthlyPeriod],
  );

  // 4. Pregnant vs not, per period.
  const stacked = useMemo(
    () =>
      data
        ? regroup(data.trends, stackPeriod).map((r) => ({
            period: r.label,
            pregnant: r.pregnant,
            notPregnant: r.transfers - r.pregnant,
          }))
        : null,
    [data, stackPeriod],
  );

  // 5. From transfers to pregnancies. Counts, or shares of all transfers.
  const waterfall = useMemo(() => {
    if (!k) return null;
    const noOutcome = k.total_transfers - k.with_outcome;
    const scale = (v: number) => (waterfallMeasure === "share" && k.total_transfers > 0 ? (v / k.total_transfers) * 100 : v);
    return [
      { name: "Transfers", base: 0, value: scale(k.total_transfers), kind: "volume" as Role },
      { name: "No outcome yet", base: scale(k.with_outcome), value: scale(noOutcome), kind: "pending" as Role },
      { name: "With outcome", base: 0, value: scale(k.with_outcome), kind: "volume" as Role },
      { name: "Open", base: scale(k.pregnant), value: scale(k.open), kind: "negative" as Role },
      { name: "Pregnant", base: 0, value: scale(k.pregnant), kind: "positive" as Role },
    ];
  }, [k, waterfallMeasure]);

  // 6. Protocols with enough transfers. Verdict on each protocol's own interval.
  const protocolRows = useMemo(
    () =>
      (data?.protocols ?? [])
        .filter((p) => p.n_with_outcome >= radarMin && p.pregnancy_rate != null)
        .map((p) => ({
          ...p,
          role: verdict(p.n_pregnant, p.n_with_outcome, programmeRate),
          ci: wilson(p.n_pregnant, p.n_with_outcome),
        })),
    [data, radarMin, programmeRate],
  );
  const radar = useMemo(() => {
    const total = protocolRows.reduce((s, p) => s + p.n_with_outcome, 0) || 1;
    const series = protocolRows.map((p, i) => ({
      key: `p${i}`,
      label: p.protocol_name.length > 22 ? `${p.protocol_name.slice(0, 21)}…` : p.protocol_name,
      n: p.n_with_outcome,
      color: ROLE[p.role].ink,
      protocolId: p.protocol_id,
    }));
    const axes = [
      { axis: "Pregnancy rate", ...Object.fromEntries(protocolRows.map((p, i) => [`p${i}`, (p.pregnancy_rate ?? 0) * 100])) },
      { axis: "Lower 95% bound", ...Object.fromEntries(protocolRows.map((p, i) => [`p${i}`, (p.ci?.[0] ?? 0) * 100])) },
      { axis: "Share of transfers", ...Object.fromEntries(protocolRows.map((p, i) => [`p${i}`, (p.n_with_outcome / total) * 100])) },
    ];
    return { axes, series };
  }, [protocolRows]);
  const protocolRanked = useMemo(
    () =>
      [...protocolRows]
        .sort((a, b) => (b.pregnancy_rate ?? 0) - (a.pregnancy_rate ?? 0))
        .map((p) => ({
          id: p.protocol_id,
          label: p.protocol_name.length > 26 ? `${p.protocol_name.slice(0, 25)}…` : p.protocol_name,
          rate: toPct(p.pregnancy_rate) ?? 0,
          n: p.n_with_outcome,
          role: p.role,
          active: filters.protocol_id === p.protocol_id,
          ci: p.ci == null ? "—" : `${(p.ci[0] * 100).toFixed(0)}–${(p.ci[1] * 100).toFixed(0)}%`,
        })),
    [protocolRows, filters.protocol_id],
  );

  // 7. Donor bubbles. Verdict on each donor's interval; only donors with enough transfers.
  const donors = useMemo(
    () =>
      (data?.donors ?? [])
        .filter((d) => d.n_with_outcome >= donorMin && d.pregnancy_rate != null)
        .map((d) => ({
          x: d.n_transfers,
          y: (d.pregnancy_rate ?? 0) * 100,
          z: d.n_transfers,
          donorId: d.donor_id,
          tag: d.donor_tag,
          breed: d.breed ?? "Unknown",
          n: d.n_with_outcome,
          role: verdict(d.n_pregnant, d.n_with_outcome, programmeRate),
          active: filters.donor_id === d.donor_id,
        })),
    [data, donorMin, programmeRate, filters.donor_id],
  );

  // 8. Breeds, ranked as bars. Pregnancy rate gets a verdict; transfers are a volume.
  const breedRanked = useMemo(() => {
    const rows = (data?.breeds ?? []).filter((b) => b.n_with_outcome >= breedMin);
    return rows
      .map((b) => ({
        name: b.donor_breed,
        value: breedMeasure === "rate" ? toPct(b.pregnancy_rate) ?? 0 : b.n_transfers,
        n: b.n_with_outcome,
        rate: toPct(b.pregnancy_rate),
        role: breedMeasure === "rate" ? verdict(b.n_pregnant, b.n_with_outcome, programmeRate) : ("volume" as Role),
        active: filters.breed === b.donor_breed,
      }))
      .sort((a, b) => b.value - a.value);
  }, [data, breedMeasure, breedMin, programmeRate, filters.breed]);

  // 9. Protocol outcomes: counts, or share of each protocol's transfers.
  const protocolStack = useMemo(
    () =>
      (data?.protocols ?? [])
        .filter((p) => p.n_transfers >= protocolMin)
        .map((p) => ({
          id: p.protocol_id,
          label: p.protocol_name.length > 26 ? `${p.protocol_name.slice(0, 25)}…` : p.protocol_name,
          full: p.protocol_name,
          pregnant: p.n_pregnant,
          notPregnant: p.n_transfers - p.n_pregnant,
          n: p.n_transfers,
        }))
        .sort((a, b) => b.n - a.n),
    [data, protocolMin],
  );

  // 10. Corpus luteum size. Verdict on each band's interval; transfers are a volume.
  const bins = useMemo(
    () =>
      (data?.bins ?? []).map((b) => ({
        range: b.range,
        rate: toPct(b.pregnancy_rate),
        transfers: b.n_transfers,
        n: b.n_with_outcome,
        ci: b.ci_lower == null || b.ci_upper == null ? "—" : `${(b.ci_lower * 100).toFixed(0)}–${(b.ci_upper * 100).toFixed(0)}%`,
        role: verdict(b.n_pregnant, b.n_with_outcome, programmeRate),
      })),
    [data, programmeRate],
  );

  // ---- Takeaways. Each is computed from the rows the chart shows. ----

  const outcomeTake =
    k && k.with_outcome > 0
      ? `${k.pregnant.toLocaleString()} of ${k.with_outcome.toLocaleString()} transfers with a first-check result were pregnant (${pctText(programmeRate ?? 0)}). ${(k.total_transfers - k.with_outcome).toLocaleString()} transfers have no result yet.`
      : null;

  const freshTake = (() => {
    if (!freshFrozen || freshFrozen.length < 2) return null;
    const [a, b] = freshFrozen;
    const ca = wilson(a.k, a.n);
    const cb = wilson(b.k, b.n);
    if (!ca || !cb) return null;
    const gap = Math.abs(a.rate - b.rate).toFixed(1);
    const verdictText = overlap(ca, cb)
      ? `The intervals overlap, so this gap of ${gap} points is not a clear difference.`
      : `${a.rate > b.rate ? a.name : b.name} is clearly higher.`;
    return `${a.name} ${a.rate.toFixed(1)}% (n=${a.n.toLocaleString()}) against ${b.name} ${b.rate.toFixed(1)}% (n=${b.n.toLocaleString()}). ${verdictText}`;
  })();

  const monthlyTake = (() => {
    if (!monthly || programmeRate == null) return null;
    const eligible = monthly.filter((m) => m.n >= SMALL_SAMPLE && m.rate != null);
    if (eligible.length === 0) return `No ${monthlyPeriod} has ${SMALL_SAMPLE} or more transfers with a result.`;
    const sorted = [...eligible].sort((a, b) => (a.rate ?? 0) - (b.rate ?? 0));
    const low = sorted[0];
    const high = sorted[sorted.length - 1];
    const lowerClearly = eligible.filter((m) => verdict(m.k, m.n, programmeRate) === "negative");
    const higherClearly = eligible.filter((m) => verdict(m.k, m.n, programmeRate) === "positive");
    const clear =
      lowerClearly.length || higherClearly.length
        ? ` Clearly below the programme rate: ${lowerClearly.length ? lowerClearly.map((m) => m.period).join(", ") : "none"}. Clearly above: ${higherClearly.length ? higherClearly.map((m) => m.period).join(", ") : "none"}.`
        : " No period is clearly different from the programme rate.";
    return `Rates run from ${(low.rate ?? 0).toFixed(1)}% (${low.period}) to ${(high.rate ?? 0).toFixed(1)}% (${high.period}), across ${plural(eligible.length, monthlyPeriod, `${monthlyPeriod}s`)} with ${SMALL_SAMPLE} or more transfers.${clear}`;
  })();

  const stackTake =
    k && k.total_transfers > 0
      ? `${(k.total_transfers - k.with_outcome).toLocaleString()} of ${k.total_transfers.toLocaleString()} transfers (${pctText((k.total_transfers - k.with_outcome) / k.total_transfers)}) have no first-check result, so they count with "not pregnant" here. Read the share view for the mix among transfers with a result.`
      : null;

  const waterfallTake =
    k && k.with_outcome > 0
      ? `${(k.total_transfers - k.with_outcome).toLocaleString()} transfers (${pctText((k.total_transfers - k.with_outcome) / k.total_transfers)}) are still waiting for a result. Of the ${k.with_outcome.toLocaleString()} that have one, ${k.pregnant.toLocaleString()} (${pctText(programmeRate ?? 0)}) are pregnant.`
      : null;

  const radarTake = (() => {
    if (protocolRows.length === 0) return null;
    const clear = protocolRows.filter((p) => p.role !== "volume");
    const names = clear.map((p) => `${p.protocol_name} (${pctText(p.pregnancy_rate ?? 0)})`);
    return clear.length
      ? `Of ${plural(protocolRows.length, "protocol", "protocols")} with ${radarMin} or more transfers, ${names.join("; ")} ${clear.length === 1 ? "is" : "are"} clearly different from the programme rate. The rest overlap it.`
      : `None of the ${plural(protocolRows.length, "protocol", "protocols")} with ${radarMin} or more transfers is clearly different from the programme rate. Their intervals overlap it.`;
  })();

  const donorTake = (() => {
    if (!data) return null;
    const eligible = data.donors.filter((d) => d.n_with_outcome >= donorMin && d.pregnancy_rate != null);
    if (eligible.length === 0) return `No donor has ${donorMin} or more transfers with a result.`;
    const above = eligible.filter((d) => verdict(d.n_pregnant, d.n_with_outcome, programmeRate) === "positive").length;
    const below = eligible.filter((d) => verdict(d.n_pregnant, d.n_with_outcome, programmeRate) === "negative").length;
    const chance = Math.round(0.05 * eligible.length);
    return `${above} donor${above === 1 ? "" : "s"} clearly above and ${below} clearly below the programme rate, out of ${eligible.length} with ${donorMin} or more transfers. Testing that many donors, about ${chance} would look different by chance alone, so treat the few outliers as leads to check, not findings.`;
  })();

  const breedTake = (() => {
    if (breedRanked.length === 0) return null;
    const top = breedRanked[0];
    const clear = breedRanked.filter((b) => b.role !== "volume" && breedMeasure === "rate");
    const topText =
      breedMeasure === "rate"
        ? `${top.name} is highest at ${top.value.toFixed(1)}% (n=${top.n.toLocaleString()}).`
        : `${top.name} has the most transfers (${top.value.toLocaleString()}).`;
    if (breedMeasure === "transfers") return `${topText} Volume only: switch to pregnancy rate to see whether the breeds differ.`;
    return clear.length
      ? `${topText} Clearly different from the programme rate: ${clear.map((b) => b.name).join(", ")}.`
      : `${topText} No breed is clearly different from the programme rate; the intervals overlap it.`;
  })();

  const protocolStackTake = (() => {
    if (protocolStack.length === 0) return null;
    const largest = protocolStack[0];
    const smallest = protocolStack[protocolStack.length - 1];
    return `${largest.full} carries the most transfers (${largest.n.toLocaleString()}). ${
      smallest.n < SMALL_SAMPLE ? `${smallest.full} has only ${smallest.n}, so its rate is uncertain.` : "Every protocol shown has at least 20 transfers."
    }`;
  })();

  const clTake = (() => {
    const eligible = (data?.bins ?? []).filter((b) => b.n_with_outcome >= SMALL_SAMPLE && b.pregnancy_rate != null);
    if (eligible.length === 0) return null;
    const above = eligible.filter((b) => verdict(b.n_pregnant, b.n_with_outcome, programmeRate) === "positive");
    const below = eligible.filter((b) => verdict(b.n_pregnant, b.n_with_outcome, programmeRate) === "negative");
    const parts = [];
    if (above.length) parts.push(`${above.map((b) => `${b.range} mm (${pctText(b.pregnancy_rate ?? 0)})`).join(", ")} clearly above`);
    if (below.length) parts.push(`${below.map((b) => `${b.range} mm (${pctText(b.pregnancy_rate ?? 0)})`).join(", ")} clearly below`);
    return parts.length
      ? `${parts.join("; ")} the programme rate. Other size bands overlap it.`
      : "No corpus luteum size band is clearly different from the programme rate. Their intervals overlap it.";
  })();

  // ---- Active filters, shown above the charts so a click is never a mystery. ----
  const chips: { label: string; clear: () => void }[] = [];
  if (filters.breed) chips.push({ label: `Breed: ${filters.breed}`, clear: () => onFilter({ breed: undefined }) });
  if (filters.fresh_or_frozen)
    chips.push({ label: `Embryos: ${filters.fresh_or_frozen}`, clear: () => onFilter({ fresh_or_frozen: undefined }) });
  if (filters.protocol_id) {
    const name = data?.protocols.find((p) => p.protocol_id === filters.protocol_id)?.protocol_name ?? `#${filters.protocol_id}`;
    chips.push({ label: `Protocol: ${name}`, clear: () => onFilter({ protocol_id: undefined }) });
  }
  if (filters.donor_id) {
    const tag = data?.donors.find((d) => d.donor_id === filters.donor_id)?.donor_tag ?? `#${filters.donor_id}`;
    chips.push({ label: `Donor: ${tag}`, clear: () => onFilter({ donor_id: undefined }) });
  }
  if (filters.date_from && filters.date_to)
    chips.push({ label: `Dates: ${filters.date_from} to ${filters.date_to}`, clear: () => onFilter({ date_from: undefined, date_to: undefined }) });

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
        <RoleKey
          items={[
            { role: "positive", label: "Clearly above the programme rate (whole 95% interval above it)" },
            { role: "negative", label: "Clearly below it (whole interval below it)" },
            { role: "volume", label: "No clear difference (the interval includes the programme rate), or a plain count" },
            { role: "pending", label: "Still waiting for a result" },
          ]}
        />
        {programmeRate != null && (
          <span className="dash-heading">
            Programme rate for these filters: {pctText(programmeRate)} ({k?.with_outcome.toLocaleString()} transfers with a result)
          </span>
        )}
        {data?.start && data?.end && (
          <span className="w-full">
            Transfers from {data.start} to {data.end}. Click a bar, slice, bubble or period to filter the whole dashboard; click it again to clear.
          </span>
        )}
        {chips.length > 0 && (
          <span className="flex w-full flex-wrap items-center gap-2">
            <span className="font-medium dash-heading">Filtered to:</span>
            {chips.map((c) => (
              <button
                key={c.label}
                type="button"
                onClick={c.clear}
                className="rounded-full bg-white px-3 py-1 font-semibold dash-heading shadow-sm hover:bg-white/80"
              >
                {c.label} ×
              </button>
            ))}
          </span>
        )}
      </div>

      {/* 1. Outcome split */}
      <Card
        title="Outcome split"
        caption={k ? `Pregnant vs open at the first check, for transfers with a result.` : "Loading outcomes…"}
        takeaway={outcomeTake}
        controls={<Seg label="View" value={outcomeView} onChange={setOutcomeView} options={[{ value: "donut", label: "Donut" }, { value: "bars", label: "Bars" }]} />}
      >
        {outcome ? (
          outcomeView === "donut" ? (
            <div className="relative">
              <Frame height={260}>
                <PieChart>
                  <Pie data={outcome} dataKey="value" nameKey="name" innerRadius={62} outerRadius={96} paddingAngle={2} stroke="none">
                    {outcome.map((o) => (
                      <Cell key={o.name} {...roleProps(o.role)} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend verticalAlign="bottom" height={28} formatter={(v) => ink(v)} />
                </PieChart>
              </Frame>
              {k && k.with_outcome > 0 && (
                <div className="pointer-events-none absolute inset-0 flex items-center justify-center pb-7">
                  <div className="text-center">
                    <div className="text-2xl font-semibold dash-heading">{pctText(k.pregnant / k.with_outcome)}</div>
                    <div className="text-[11px] dash-muted">pregnant</div>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <>
              <RoleKey items={[{ role: "positive", label: "Pregnant" }, { role: "negative", label: "Open" }]} />
              <Frame height={220}>
                <BarChart data={outcome} layout="vertical" margin={{ top: 8, right: 24, left: 8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID} horizontal={false} />
                  <XAxis type="number" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} allowDecimals={false} />
                  <YAxis type="category" dataKey="name" width={70} stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
                  <Tooltip />
                  <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                    {outcome.map((o) => (
                      <Cell key={o.name} {...roleProps(o.role)} />
                    ))}
                    <LabelList dataKey="value" position="right" fill={INK} fontSize={11} />
                  </Bar>
                </BarChart>
              </Frame>
            </>
          )
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 2. Fresh vs frozen */}
      <Card
        title="Transfer type"
        caption="Pregnancy rate for fresh and frozen embryos. Click a group to filter the dashboard to it. Faded groups have fewer than 20 transfers with a result."
        takeaway={freshTake}
        controls={<Seg label="View" value={radialView} onChange={setRadialView} options={[{ value: "radial", label: "Radial" }, { value: "bars", label: "Bars" }]} />}
      >
        {freshFrozen ? (
          <>
            <RoleKey items={[{ role: "positive", label: "Clearly above the programme rate" }, { role: "negative", label: "Clearly below it" }, { role: "volume", label: "No clear difference" }]} />
            {radialView === "radial" ? (
              <Frame height={240}>
                <RadialBarChart innerRadius="30%" outerRadius="95%" data={freshFrozen} startAngle={180} endAngle={-180}>
                  <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                  <RadialBar dataKey="rate" background={{ fill: "rgba(46, 54, 69, 0.05)" }} cornerRadius={8}>
                    {freshFrozen.map((f) => (
                      <Cell
                        key={f.name}
                        {...roleProps(f.role)}
                        fillOpacity={filters.fresh_or_frozen && !f.active ? FADE : f.n < SMALL_SAMPLE ? 0.45 : 1}
                        cursor="pointer"
                        onClick={() => toggle("fresh_or_frozen", f.name)}
                      />
                    ))}
                  </RadialBar>
                  <Tooltip formatter={(v, _n, item) => [`${Number(v).toFixed(1)}% (n=${(item.payload as { n: number }).n})`, (item.payload as { name: string }).name]} />
                  <Legend iconSize={10} verticalAlign="bottom" formatter={(_v, entry) => ink(`${(entry.payload as { name: string; n: number }).name} · n=${(entry.payload as { n: number }).n}`)} />
                </RadialBarChart>
              </Frame>
            ) : (
              <Frame height={240}>
                <BarChart data={freshFrozen} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
                  <XAxis dataKey="name" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
                  <YAxis stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} unit="%" domain={[0, 100]} />
                  <Tooltip formatter={(v, _n, item) => [`${Number(v).toFixed(1)}% (n=${(item.payload as { n: number }).n})`, "Pregnancy rate"]} />
                  <Bar dataKey="rate" radius={[6, 6, 0, 0]}>
                    {freshFrozen.map((f) => (
                      <Cell
                        key={f.name}
                        {...roleProps(f.role)}
                        fillOpacity={filters.fresh_or_frozen && !f.active ? FADE : f.n < SMALL_SAMPLE ? 0.45 : 1}
                        cursor="pointer"
                        onClick={() => toggle("fresh_or_frozen", f.name)}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </Frame>
            )}
          </>
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 3. Monthly volume and rate */}
      <Card
        wide
        title="Monthly volume and pregnancy rate"
        caption="Bars are transfers in each period; the line is that period's pregnancy rate. Click a period to filter the dashboard to its dates. Quarters pool their months."
        takeaway={monthlyTake}
        controls={
          <>
            <Seg label="Period" value={monthlyPeriod} onChange={setMonthlyPeriod} options={PERIOD_OPTIONS} />
            <Seg
              label="Show"
              value={monthlyView}
              onChange={setMonthlyView}
              options={[
                { value: "combo", label: "Bars and line" },
                { value: "bars", label: "Transfers only" },
                { value: "line", label: "Pregnancy rate only" },
              ]}
            />
          </>
        }
      >
        {monthly ? (
          <Frame height={280}>
            <ComposedChart data={monthly} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
              <XAxis dataKey="period" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
              <YAxis yAxisId="left" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} allowDecimals={false} />
              <YAxis yAxisId="right" orientation="right" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} unit="%" domain={[0, 100]} />
              <Tooltip formatter={(v, name) => (name === "rate" ? `${Number(v).toFixed(1)}%` : v)} />
              <Legend verticalAlign="top" height={28} formatter={(v) => ink(v === "transfers" ? "Transfers" : "Pregnancy rate")} />
              {monthlyView !== "line" && (
                <Bar yAxisId="left" dataKey="transfers" {...roleProps("volume")} radius={[6, 6, 0, 0]} name="transfers" cursor="pointer" onClick={(d: unknown) => togglePeriod((d as { payload: { period: string } }).payload.period)} />
              )}
              {monthlyView !== "bars" && (
                <Line yAxisId="right" type="monotone" dataKey="rate" stroke={ROLE.positive.fill} strokeWidth={2.2} dot={{ r: 4 }} connectNulls name="rate" />
              )}
            </ComposedChart>
          </Frame>
        ) : (
          <Empty>Loading…</Empty>
        )}
        {monthly && (
          <p className="mt-2 text-[11px] dash-muted">
            Selected periods are pinned by the date filter.{" "}
            {monthly.some((m) => isPeriodActive(m.period)) ? "Current selection: " + monthly.filter((m) => isPeriodActive(m.period)).map((m) => m.period).join(", ") : ""}
          </p>
        )}
      </Card>

      {/* 4. Pregnant vs not */}
      <Card
        title="Pregnant vs not pregnant"
        caption="Each period's transfers split into pregnant and not pregnant or no result yet. Counts stack to the period total; share mode stacks each period to 100%."
        takeaway={stackTake}
        controls={
          <>
            <Seg label="Period" value={stackPeriod} onChange={setStackPeriod} options={PERIOD_OPTIONS} />
            <Seg
              label="Measure"
              value={stackMode}
              onChange={setStackMode}
              options={[
                { value: "counts", label: "Counts" },
                { value: "share", label: "Share" },
              ]}
            />
          </>
        }
      >
        {stacked ? (
          <Frame height={250}>
            <AreaChart data={stacked} stackOffset={stackMode === "share" ? "expand" : "none"} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
              <XAxis dataKey="period" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
              <YAxis
                stroke={AXIS}
                tickLine={false}
                axisLine={false}
                fontSize={11}
                allowDecimals={false}
                tickFormatter={(v) => (stackMode === "share" ? `${Math.round(Number(v) * 100)}%` : String(v))}
              />
              <Tooltip />
              <Legend verticalAlign="top" height={26} formatter={(v) => ink(v === "pregnant" ? "Pregnant" : "Not pregnant / no result yet")} />
              <Area type="monotone" dataKey="notPregnant" stackId="m" stroke={ROLE.negative.stroke} fill={ROLE.negative.fill} fillOpacity={1} name="notPregnant" />
              <Area type="monotone" dataKey="pregnant" stackId="m" stroke={ROLE.positive.fill} fill={ROLE.positive.fill} fillOpacity={0.85} name="pregnant" />
            </AreaChart>
          </Frame>
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 5. From transfers to pregnancies */}
      <Card
        title="From transfers to pregnancies"
        caption="Totals, then the steps that leave them. Counts, or each step as a share of all transfers."
        takeaway={waterfallTake}
        controls={
          <>
            <Seg label="View" value={waterfallView} onChange={setWaterfallView} options={[{ value: "waterfall", label: "Waterfall" }, { value: "bars", label: "Bars" }]} />
            <Seg
              label="Measure"
              value={waterfallMeasure}
              onChange={setWaterfallMeasure}
              options={[
                { value: "count", label: "Count" },
                { value: "share", label: "% of transfers" },
              ]}
            />
          </>
        }
      >
        <RoleKey
          items={[
            { role: "volume", label: "Totals" },
            { role: "pending", label: "No result yet" },
            { role: "negative", label: "Open" },
            { role: "positive", label: "Pregnant" },
          ]}
        />
        {waterfall ? (
          <Frame height={250}>
            <BarChart data={waterfall} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
              <XAxis dataKey="name" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} interval={0} />
              <YAxis stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} allowDecimals={false} unit={waterfallMeasure === "share" ? "%" : undefined} />
              <Tooltip formatter={(v) => [waterfallMeasure === "share" ? `${Number(v).toFixed(1)}%` : v, waterfallMeasure === "share" ? "Share" : "Count"]} />
              {waterfallView === "waterfall" && <Bar dataKey="base" stackId="w" fill="transparent" isAnimationActive={false} />}
              <Bar dataKey="value" stackId={waterfallView === "waterfall" ? "w" : undefined} radius={[6, 6, 0, 0]} name="value">
                {waterfall.map((w) => (
                  <Cell key={w.name} {...roleProps(w.kind)} />
                ))}
              </Bar>
            </BarChart>
          </Frame>
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 6. Protocol profile */}
      <Card
        wide
        title="Protocol profile"
        caption="Protocols with enough transfers, against the programme rate. Radar shows rate, lower bound and share of transfers; bars rank them by rate. Click a protocol to filter the dashboard to it."
        takeaway={radarTake}
        controls={
          <>
            <Seg label="View" value={radarView} onChange={setRadarView} options={[{ value: "radar", label: "Radar" }, { value: "bars", label: "Ranked bars" }]} />
            <Seg label="Min transfers" value={radarMin} onChange={setRadarMin} options={MIN_OPTIONS} />
          </>
        }
      >
        {radarView === "radar" ? (
          radar.series.length > 0 ? (
            <>
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
              <div className="mt-1 flex flex-wrap gap-2">
                {radar.series.map((s) => (
                  <button
                    key={s.key}
                    type="button"
                    onClick={() => toggle("protocol_id", s.protocolId ?? undefined)}
                    className="rounded-full bg-white/70 px-3 py-1 text-xs font-semibold dash-heading hover:bg-white"
                  >
                    Filter to {s.label}
                  </button>
                ))}
              </div>
            </>
          ) : (
            <Empty>No protocol has {radarMin} or more transfers with a result.</Empty>
          )
        ) : protocolRanked.length > 0 ? (
          <>
            <RoleKey items={[{ role: "positive", label: "Clearly above the programme rate" }, { role: "negative", label: "Clearly below it" }, { role: "volume", label: "No clear difference" }]} />
            <Frame height={Math.max(180, protocolRanked.length * 44)}>
              <BarChart data={protocolRanked} layout="vertical" margin={{ top: 4, right: 56, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} horizontal={false} />
                <XAxis type="number" domain={[0, 100]} unit="%" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
                <YAxis type="category" dataKey="label" width={170} stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
                <Tooltip formatter={(v, _n, item) => [`${Number(v).toFixed(1)}% · n=${(item.payload as { n: number }).n} · CI ${(item.payload as { ci: string }).ci}`, "Pregnancy rate"]} />
                <Bar dataKey="rate" radius={[0, 6, 6, 0]}>
                  {protocolRanked.map((p) => (
                    <Cell
                      key={p.label}
                      {...roleProps(p.role)}
                      fillOpacity={filters.protocol_id && !p.active ? FADE : 1}
                      cursor="pointer"
                      onClick={() => toggle("protocol_id", p.id ?? undefined)}
                    />
                  ))}
                  <LabelList dataKey="rate" position="right" formatter={(v: unknown) => `${Number(v).toFixed(1)}%`} fill={INK} fontSize={11} />
                </Bar>
              </BarChart>
            </Frame>
          </>
        ) : (
          <Empty>No protocol has {radarMin} or more transfers with a result.</Empty>
        )}
      </Card>

      {/* 7. Donor performance */}
      <Card
        title="Donor performance"
        caption="One bubble per donor: transfers (across) against pregnancy rate (up). Bigger bubbles have more transfers. Click a bubble to filter the dashboard to that donor."
        takeaway={donorTake}
        controls={<Seg label="Min transfers with a result" value={donorMin} onChange={setDonorMin} options={[{ value: 5, label: "5+" }, { value: 10, label: "10+" }, { value: 20, label: "20+" }]} />}
      >
        <RoleKey items={[{ role: "positive", label: "Clearly above the programme rate" }, { role: "negative", label: "Clearly below it" }, { role: "volume", label: "No clear difference" }]} />
        {data ? (
          donors.length > 0 ? (
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
                    const d = payload[0].payload as { tag: string; breed: string; x: number; y: number; n: number };
                    return (
                      <div className="rounded-xl border border-white/80 bg-white/95 px-3 py-2 text-xs shadow" style={{ color: INK }}>
                        <div className="font-semibold">Donor {d.tag}</div>
                        <div>{d.breed}</div>
                        <div>
                          {d.x} transfers · {d.n} with a result · {d.y.toFixed(1)}% pregnant
                        </div>
                      </div>
                    );
                  }}
                />
                <Scatter data={donors} name="donors">
                  {donors.map((d) => (
                    <Cell
                      key={d.tag}
                      {...roleProps(d.role)}
                      fillOpacity={filters.donor_id && !d.active ? FADE : d.n < SMALL_SAMPLE ? 0.45 : 0.85}
                      cursor="pointer"
                      onClick={() => toggle("donor_id", d.donorId ?? undefined)}
                    />
                  ))}
                </Scatter>
              </ScatterChart>
            </Frame>
          ) : (
            <Empty>No donor matches these filters.</Empty>
          )
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 8. Breeds, ranked */}
      <Card
        title="Transfers by donor breed"
        caption="Breeds ranked by the measure you choose. Click a breed to filter the dashboard to it. Faded bars have fewer than 20 transfers with a result."
        takeaway={breedTake}
        controls={
          <>
            <Seg label="Measure" value={breedMeasure} onChange={setBreedMeasure} options={MEASURE_OPTIONS} />
            <Seg label="Min transfers" value={breedMin} onChange={setBreedMin} options={MIN_OPTIONS} />
          </>
        }
      >
        {breedMeasure === "rate" ? (
          <RoleKey items={[{ role: "positive", label: "Clearly above the programme rate" }, { role: "negative", label: "Clearly below it" }, { role: "volume", label: "No clear difference" }]} />
        ) : (
          <RoleKey items={[{ role: "volume", label: "Transfers" }]} />
        )}
        {data ? (
          breedRanked.length > 0 ? (
            <Frame height={Math.max(180, breedRanked.length * 40)}>
              <BarChart data={breedRanked} layout="vertical" margin={{ top: 4, right: 56, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} horizontal={false} />
                <XAxis
                  type="number"
                  stroke={AXIS}
                  tickLine={false}
                  axisLine={false}
                  fontSize={11}
                  allowDecimals={false}
                  domain={breedMeasure === "rate" ? [0, 100] : [0, "auto"]}
                  unit={breedMeasure === "rate" ? "%" : undefined}
                />
                <YAxis type="category" dataKey="name" width={150} stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
                <Tooltip
                  formatter={(v, _n, item) => {
                    const p = item.payload as { n: number; rate: number | null };
                    return [breedMeasure === "rate" ? `${Number(v).toFixed(1)}% · n=${p.n}` : `${v} transfers · ${p.rate == null ? "—" : `${p.rate.toFixed(1)}%`} pregnant`, breedMeasure === "rate" ? "Pregnancy rate" : "Transfers"];
                  }}
                />
                <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                  {breedRanked.map((b) => (
                    <Cell
                      key={b.name}
                      {...roleProps(b.role)}
                      fillOpacity={filters.breed && !b.active ? FADE : b.n < SMALL_SAMPLE ? 0.45 : 1}
                      cursor="pointer"
                      onClick={() => toggle("breed", b.name)}
                    />
                  ))}
                  <LabelList
                    dataKey="value"
                    position="right"
                    formatter={(v: unknown) => (breedMeasure === "rate" ? `${Number(v).toFixed(1)}%` : String(v))}
                    fill={INK}
                    fontSize={11}
                  />
                </Bar>
              </BarChart>
            </Frame>
          ) : (
            <Empty>No breed has {breedMin} or more transfers with a result.</Empty>
          )
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 9. Protocol outcomes */}
      <Card
        title="Outcomes by protocol"
        caption="Pregnant and not-pregnant transfer counts for each protocol, so the sample behind every rate is visible. Share mode stacks each protocol to 100%."
        takeaway={protocolStackTake}
        controls={
          <>
            <Seg
              label="Measure"
              value={protocolMode}
              onChange={setProtocolMode}
              options={[
                { value: "counts", label: "Counts" },
                { value: "share", label: "Share" },
              ]}
            />
            <Seg label="Min transfers" value={protocolMin} onChange={setProtocolMin} options={MIN_OPTIONS} />
          </>
        }
      >
        {data ? (
          protocolStack.length > 0 ? (
            <Frame height={Math.max(200, protocolStack.length * 44)}>
              <BarChart data={protocolStack} layout="vertical" stackOffset={protocolMode === "share" ? "expand" : "none"} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} horizontal={false} />
                <XAxis
                  type="number"
                  stroke={AXIS}
                  tickLine={false}
                  axisLine={false}
                  fontSize={11}
                  allowDecimals={false}
                  tickFormatter={(v) => (protocolMode === "share" ? `${Math.round(Number(v) * 100)}%` : String(v))}
                />
                <YAxis type="category" dataKey="label" width={170} stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
                <Tooltip
                  formatter={(v, name) => [v, name === "pregnant" ? "Pregnant" : "Not pregnant / no result yet"]}
                  labelFormatter={(_l, payload) => (payload?.[0]?.payload as { full?: string } | undefined)?.full ?? ""}
                />
                <Legend verticalAlign="top" height={26} formatter={(v) => ink(v === "pregnant" ? "Pregnant" : "Not pregnant / no result yet")} />
                <Bar dataKey="pregnant" stackId="p" {...roleProps("positive")} name="pregnant" cursor="pointer" onClick={(d: unknown) => toggle("protocol_id", (d as { payload: { id: number | null } }).payload.id ?? undefined)} />
                <Bar dataKey="notPregnant" stackId="p" {...roleProps("negative")} radius={[0, 6, 6, 0]} name="notPregnant" cursor="pointer" onClick={(d: unknown) => toggle("protocol_id", (d as { payload: { id: number | null } }).payload.id ?? undefined)} />
              </BarChart>
            </Frame>
          ) : (
            <Empty>No protocol has {protocolMin} or more transfers.</Empty>
          )
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>

      {/* 10. Corpus luteum size */}
      <Card
        title="Pregnancy rate by corpus luteum size"
        caption="Ultrasound CL size at transfer, in millimetres. Columns show pregnancy rate with a verdict against the programme rate; transfers are a plain count. The tooltip gives each band's 95% interval."
        takeaway={clTake}
        controls={
          <>
            <Seg label="View" value={clView} onChange={setClView} options={[{ value: "columns", label: "Columns" }, { value: "line", label: "Line" }]} />
            <Seg label="Measure" value={clMeasure} onChange={setClMeasure} options={MEASURE_OPTIONS} />
          </>
        }
      >
        {clMeasure === "rate" ? (
          <RoleKey items={[{ role: "positive", label: "Clearly above the programme rate" }, { role: "negative", label: "Clearly below it" }, { role: "volume", label: "No clear difference" }]} />
        ) : (
          <RoleKey items={[{ role: "volume", label: "Transfers" }]} />
        )}
        {data ? (
          clView === "columns" ? (
            <Frame height={250}>
              <BarChart data={bins} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
                <XAxis dataKey="range" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
                <YAxis stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} allowDecimals={false} unit={clMeasure === "rate" ? "%" : undefined} domain={clMeasure === "rate" ? [0, 100] : [0, "auto"]} />
                <Tooltip
                  formatter={(v, _n, item) => {
                    const p = item.payload as { n: number; ci: string; transfers: number };
                    return clMeasure === "rate"
                      ? [`${Number(v).toFixed(1)}% · n=${p.n} · CI ${p.ci}`, "Pregnancy rate"]
                      : [`${p.transfers} transfers`, "Transfers"];
                  }}
                />
                <Bar dataKey={clMeasure === "rate" ? "rate" : "transfers"} radius={[6, 6, 0, 0]} name={clMeasure === "rate" ? "rate" : "transfers"}>
                  {bins.map((b) => (
                    <Cell key={b.range} {...roleProps(clMeasure === "rate" ? b.role : "volume")} fillOpacity={b.n < SMALL_SAMPLE ? 0.45 : 1} />
                  ))}
                </Bar>
              </BarChart>
            </Frame>
          ) : (
            <Frame height={250}>
              <LineChart data={bins} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={GRID} vertical={false} />
                <XAxis dataKey="range" stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} />
                <YAxis stroke={AXIS} tickLine={false} axisLine={false} fontSize={11} allowDecimals={false} unit={clMeasure === "rate" ? "%" : undefined} domain={clMeasure === "rate" ? [0, 100] : [0, "auto"]} />
                <Tooltip />
                <Legend verticalAlign="top" height={26} formatter={(v) => ink(v === "rate" ? "Pregnancy rate" : "Transfers")} />
                <Line type="monotone" dataKey={clMeasure === "rate" ? "rate" : "transfers"} name={clMeasure === "rate" ? "rate" : "transfers"} stroke={clMeasure === "rate" ? ROLE.positive.fill : ROLE.volume.stroke} strokeWidth={2.2} dot={{ r: 4 }} connectNulls />
              </LineChart>
            </Frame>
          )
        ) : (
          <Empty>Loading…</Empty>
        )}
      </Card>
    </div>
  );
}
