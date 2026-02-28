import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  BarChart3,
  Activity,
  Users,
  TestTube,
  TrendingUp,
  TrendingDown,
  Minus,
  Loader2,
  RefreshCw,
  AlertCircle,
  Beaker,
  Heart,
} from "lucide-react";

/* ─── Types ─────────────────────────────────────────────── */

interface KPIs {
  total_transfers: number;
  with_outcome: number;
  pregnant: number;
  open: number;
  pregnancy_rate: number | null;
  embryo_utilization: number | null;
  unique_embryos: number | null;
  date_range: { first: string | null; last: string | null; span_months: number };
  entity_counts: {
    donors: number;
    recipients: number;
    technicians: number;
    protocols: number;
    sires: number;
  };
  fresh_vs_frozen: Record<string, { n: number; pregnant: number; rate: number | null }>;
}

interface MonthlyTrend {
  month: string;
  n_transfers: number;
  n_pregnant: number;
  pregnancy_rate: number;
  avg_cl: number | null;
}

interface FunnelStage {
  stage: string;
  count: number;
  rate_from_previous: number | null;
}

interface ProtocolRate {
  protocol_name: string;
  n_transfers: number;
  n_pregnant: number;
  pregnancy_rate: number;
  ci_lower: number;
  ci_upper: number;
}

interface DonorStat {
  donor_tag: string;
  breed: string | null;
  n_transfers: number;
  n_pregnant: number;
  pregnancy_rate: number;
  avg_cl: number | null;
  active_months: number;
}

interface BiomarkerBin {
  range: string;
  n: number;
  pregnancy_rate: number;
  ci_lower?: number | null;
  ci_upper?: number | null;
  mean_value?: number | null;
}

interface BiomarkerResult {
  bins: BiomarkerBin[];
  optimal_range?: BiomarkerBin | null;
  optimal_bin?: BiomarkerBin | null;
  overall_rate: number | null;
  total_records: number;
}

/* ─── Helpers ───────────────────────────────────────────── */

const pct = (v: number | null | undefined) =>
  v != null ? `${(v * 100).toFixed(1)}%` : "—";

const fmt = (v: number | null | undefined, d = 1) =>
  v != null ? v.toFixed(d) : "—";

const trendIcon = (val: number | null) => {
  if (val == null) return <Minus className="h-3 w-3 text-muted-foreground" />;
  if (val > 0.02) return <TrendingUp className="h-3 w-3 text-green-500" />;
  if (val < -0.02) return <TrendingDown className="h-3 w-3 text-red-500" />;
  return <Minus className="h-3 w-3 text-muted-foreground" />;
};

/* Color for bar based on pregnancy rate */
const barColor = (rate: number) => {
  if (rate >= 0.4) return "bg-green-500";
  if (rate >= 0.25) return "bg-yellow-500";
  return "bg-red-400";
};

/* ─── Tabs ──────────────────────────────────────────────── */

type Tab = "overview" | "protocols" | "donors" | "biomarkers";

const TABS: { key: Tab; label: string; icon: typeof BarChart3 }[] = [
  { key: "overview", label: "Overview", icon: Activity },
  { key: "protocols", label: "Protocols", icon: TestTube },
  { key: "donors", label: "Donors", icon: Users },
  { key: "biomarkers", label: "Biomarkers", icon: Beaker },
];

/* ─── Page Component ────────────────────────────────────── */

export default function AnalyticsPage() {
  const [tab, setTab] = useState<Tab>("overview");
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [trends, setTrends] = useState<MonthlyTrend[]>([]);
  const [funnel, setFunnel] = useState<FunnelStage[]>([]);
  const [protocols, setProtocols] = useState<ProtocolRate[]>([]);
  const [donors, setDonors] = useState<DonorStat[]>([]);
  const [biomarkers, setBiomarkers] = useState<Record<string, BiomarkerResult>>({});
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [kpiRes, trendRes, funnelRes, protocolRes, donorRes, bioRes] =
        await Promise.all([
          api.get("/analytics/kpis"),
          api.get("/analytics/trends"),
          api.get("/analytics/funnel"),
          api.get("/analytics/protocols"),
          api.get("/analytics/donors"),
          api.get("/analytics/biomarkers"),
        ]);
      setKpis(kpiRes.data);
      setTrends(trendRes.data);
      setFunnel(funnelRes.data.stages);
      setProtocols(protocolRes.data.protocols);
      setDonors(donorRes.data.donors);
      setBiomarkers(bioRes.data);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load analytics";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const runPipeline = useCallback(async () => {
    setRunning(true);
    try {
      await api.post("/analytics/run");
      await fetchAll();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Pipeline failed";
      setError(msg);
    } finally {
      setRunning(false);
    }
  }, [fetchAll]);

  /* ── Loading ──────────────────────────────────────────── */

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Loading analytics…</span>
      </div>
    );
  }

  if (error && !kpis) {
    return (
      <div className="flex h-96 flex-col items-center justify-center gap-4">
        <AlertCircle className="h-12 w-12 text-destructive" />
        <p className="text-muted-foreground">{error}</p>
        <Button onClick={runPipeline}>
          <Activity className="mr-2 h-4 w-4" />
          Run Analytics Pipeline
        </Button>
      </div>
    );
  }

  /* ─── Render ──────────────────────────────────────────── */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Analytics Dashboard</h2>
          <p className="text-muted-foreground">
            Reproductive KPIs, protocol effectiveness, donor performance & biomarker analysis
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchAll} disabled={running}>
            <RefreshCw className={`mr-2 h-4 w-4 ${running ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button size="sm" onClick={runPipeline} disabled={running}>
            {running ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Activity className="mr-2 h-4 w-4" />}
            Run Pipeline
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}

      {/* Tab navigation */}
      <div className="flex gap-1 border-b">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 border-b-2 px-4 py-2 text-sm font-medium transition-colors ${
              tab === t.key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            <t.icon className="h-4 w-4" />
            {t.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {tab === "overview" && <OverviewTab kpis={kpis} trends={trends} funnel={funnel} />}
      {tab === "protocols" && <ProtocolsTab protocols={protocols} />}
      {tab === "donors" && <DonorsTab donors={donors} />}
      {tab === "biomarkers" && <BiomarkersTab biomarkers={biomarkers} />}
    </div>
  );
}

/* ─── Tab: Overview ─────────────────────────────────────── */

function OverviewTab({
  kpis,
  trends,
  funnel,
}: {
  kpis: KPIs | null;
  trends: MonthlyTrend[];
  funnel: FunnelStage[];
}) {
  if (!kpis) return null;

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Transfers</CardDescription>
            <CardTitle className="text-3xl">{kpis.total_transfers.toLocaleString()}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              {kpis.date_range.first} → {kpis.date_range.last} ({kpis.date_range.span_months} months)
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Pregnancy Rate</CardDescription>
            <CardTitle className="text-3xl text-green-600">{pct(kpis.pregnancy_rate)}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              {kpis.pregnant} pregnant / {kpis.with_outcome} with outcome
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Unique Donors</CardDescription>
            <CardTitle className="text-3xl">{kpis.entity_counts.donors}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              {kpis.entity_counts.sires} sires · {kpis.entity_counts.recipients} recipients
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Embryo Utilization</CardDescription>
            <CardTitle className="text-3xl">{fmt(kpis.embryo_utilization)}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-xs text-muted-foreground">
              transfers per unique embryo ({kpis.unique_embryos} embryos)
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Fresh vs Frozen */}
      {Object.keys(kpis.fresh_vs_frozen).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Fresh vs Frozen</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-8">
              {Object.entries(kpis.fresh_vs_frozen).map(([type, stats]) => (
                <div key={type} className="text-center">
                  <div className="text-2xl font-bold">{pct(stats.rate)}</div>
                  <div className="text-sm text-muted-foreground">{type}</div>
                  <div className="text-xs text-muted-foreground">
                    {stats.pregnant}/{stats.n} transfers
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* IVF Funnel */}
      {funnel.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Heart className="h-5 w-5" />
              IVF Funnel
            </CardTitle>
            <CardDescription>Conversion rates through the transfer pipeline</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {funnel.map((stage, i) => {
                const maxCount = funnel[0]?.count || 1;
                const widthPct = Math.max(10, (stage.count / maxCount) * 100);
                return (
                  <div key={stage.stage} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{stage.stage}</span>
                      <span className="text-muted-foreground">
                        {stage.count.toLocaleString()}
                        {i > 0 && stage.rate_from_previous != null && (
                          <span className="ml-2 text-xs">
                            ({pct(stage.rate_from_previous)} conversion)
                          </span>
                        )}
                      </span>
                    </div>
                    <div className="h-6 w-full rounded bg-muted">
                      <div
                        className={`h-6 rounded transition-all ${
                          i === funnel.length - 1 ? "bg-green-500" : "bg-primary/70"
                        }`}
                        style={{ width: `${widthPct}%` }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Monthly Trends */}
      {trends.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Monthly Pregnancy Rate Trend</CardTitle>
            <CardDescription>
              {trends.length} months of data
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <div className="flex items-end gap-1" style={{ minHeight: 140 }}>
                {trends.map((m) => {
                  const height = Math.max(8, m.pregnancy_rate * 120);
                  return (
                    <div
                      key={m.month}
                      className="group relative flex flex-col items-center"
                      title={`${m.month}\nRate: ${pct(m.pregnancy_rate)}\nTransfers: ${m.n_transfers}\nPregnant: ${m.n_pregnant}`}
                    >
                      <div
                        className={`w-4 rounded-t ${barColor(m.pregnancy_rate)}`}
                        style={{ height: `${height}px` }}
                      />
                    </div>
                  );
                })}
              </div>
              <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
                <span>{trends[0]?.month}</span>
                <span>{trends[trends.length - 1]?.month}</span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

/* ─── Tab: Protocols ────────────────────────────────────── */

function ProtocolsTab({ protocols }: { protocols: ProtocolRate[] }) {
  return (
    <div className="space-y-6">
      {/* Protocol Bar Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TestTube className="h-5 w-5" />
            Pregnancy Rate by Protocol
          </CardTitle>
          <CardDescription>
            With 95% Wilson confidence intervals
          </CardDescription>
        </CardHeader>
        <CardContent>
          {protocols.length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">No protocol data available.</p>
          ) : (
            <div className="space-y-3">
              {protocols.map((p) => (
                <div key={p.protocol_name} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium">{p.protocol_name}</span>
                    <span className="text-muted-foreground">
                      {pct(p.pregnancy_rate)}
                      <span className="ml-1 text-xs">
                        [{pct(p.ci_lower)}–{pct(p.ci_upper)}]
                      </span>
                      <span className="ml-2 text-xs">(n={p.n_transfers})</span>
                    </span>
                  </div>
                  <div className="relative h-5 w-full rounded bg-muted">
                    {/* CI range bar */}
                    <div
                      className="absolute h-5 rounded bg-primary/20"
                      style={{
                        left: `${p.ci_lower * 100}%`,
                        width: `${(p.ci_upper - p.ci_lower) * 100}%`,
                      }}
                    />
                    {/* Point estimate */}
                    <div
                      className={`h-5 rounded ${barColor(p.pregnancy_rate)}`}
                      style={{ width: `${p.pregnancy_rate * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Protocol Table */}
      <Card>
        <CardHeader>
          <CardTitle>Protocol Details</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Protocol</TableHead>
                <TableHead className="text-right">Transfers</TableHead>
                <TableHead className="text-right">Pregnant</TableHead>
                <TableHead className="text-right">Rate</TableHead>
                <TableHead className="text-right">95% CI</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {protocols.map((p) => (
                <TableRow key={p.protocol_name}>
                  <TableCell className="font-medium">{p.protocol_name}</TableCell>
                  <TableCell className="text-right">{p.n_transfers}</TableCell>
                  <TableCell className="text-right">{p.n_pregnant}</TableCell>
                  <TableCell className="text-right font-mono">{pct(p.pregnancy_rate)}</TableCell>
                  <TableCell className="text-right text-xs text-muted-foreground">
                    {pct(p.ci_lower)}–{pct(p.ci_upper)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

/* ─── Tab: Donors ───────────────────────────────────────── */

function DonorsTab({ donors }: { donors: DonorStat[] }) {
  const globalRate =
    donors.length > 0
      ? donors.reduce((s, d) => s + d.n_pregnant, 0) /
        donors.reduce((s, d) => s + d.n_transfers, 0)
      : null;

  return (
    <div className="space-y-6">
      {/* Top donors bar chart */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Donor Performance
          </CardTitle>
          <CardDescription>
            {donors.length} donors analyzed
            {globalRate != null && ` · Global rate: ${pct(globalRate)}`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {donors.length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">No donor data.</p>
          ) : (
            <div className="space-y-2">
              {donors.slice(0, 15).map((d) => (
                <div key={d.donor_tag} className="space-y-0.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium truncate max-w-[200px]">{d.donor_tag}</span>
                    <span className="text-muted-foreground">
                      {pct(d.pregnancy_rate)} (n={d.n_transfers})
                    </span>
                  </div>
                  <div className="h-3 w-full rounded bg-muted">
                    <div
                      className={`h-3 rounded ${barColor(d.pregnancy_rate)}`}
                      style={{ width: `${d.pregnancy_rate * 100}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Donor table */}
      <Card>
        <CardHeader>
          <CardTitle>Donor Details</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Donor</TableHead>
                <TableHead>Breed</TableHead>
                <TableHead className="text-right">Transfers</TableHead>
                <TableHead className="text-right">Preg Rate</TableHead>
                <TableHead className="text-right">vs Mean</TableHead>
                <TableHead className="text-right">Avg CL</TableHead>
                <TableHead className="text-right">Active</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {donors.map((d) => {
                const diff = globalRate != null ? d.pregnancy_rate - globalRate : null;
                return (
                  <TableRow key={d.donor_tag}>
                    <TableCell className="font-medium truncate max-w-[150px]">
                      {d.donor_tag}
                    </TableCell>
                    <TableCell>{d.breed ?? "—"}</TableCell>
                    <TableCell className="text-right">{d.n_transfers}</TableCell>
                    <TableCell className="text-right font-mono">{pct(d.pregnancy_rate)}</TableCell>
                    <TableCell className="text-right">
                      <span className="inline-flex items-center gap-1">
                        {trendIcon(diff)}
                        {diff != null ? `${(diff * 100).toFixed(1)}pp` : "—"}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">{fmt(d.avg_cl)}</TableCell>
                    <TableCell className="text-right">{d.active_months}m</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

/* ─── Tab: Biomarkers ───────────────────────────────────── */

function BiomarkersTab({
  biomarkers,
}: {
  biomarkers: Record<string, BiomarkerResult>;
}) {
  const metrics = Object.entries(biomarkers).filter(
    ([, v]) => v && v.bins && v.bins.length > 0
  );

  const LABELS: Record<string, string> = {
    cl_measure: "CL Measure (mm)",
    bc_score: "Body Condition Score",
    heat_day: "Heat Day",
  };

  return (
    <div className="space-y-6">
      {metrics.length === 0 && (
        <p className="py-8 text-center text-muted-foreground">No biomarker data available.</p>
      )}

      {metrics.map(([key, data]) => {
        const optimal = data.optimal_range ?? data.optimal_bin;
        return (
          <Card key={key}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Beaker className="h-5 w-5" />
                {LABELS[key] ?? key}
              </CardTitle>
              <CardDescription>
                {data.total_records} records analyzed · Overall rate: {pct(data.overall_rate)}
                {optimal && (
                  <Badge variant="success" className="ml-2">
                    Optimal: {optimal.range} ({pct(optimal.pregnancy_rate)})
                  </Badge>
                )}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {/* Bar chart */}
              <div className="space-y-2">
                {data.bins.map((bin) => (
                  <div key={bin.range} className="space-y-0.5">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-mono w-20">{bin.range}</span>
                      <span className="text-muted-foreground">
                        {pct(bin.pregnancy_rate)} (n={bin.n})
                        {bin.ci_lower != null && bin.ci_upper != null && (
                          <span className="ml-1 text-[10px]">
                            [{pct(bin.ci_lower)}–{pct(bin.ci_upper)}]
                          </span>
                        )}
                      </span>
                    </div>
                    <div className="h-4 w-full rounded bg-muted">
                      <div
                        className={`h-4 rounded ${
                          optimal && bin.range === optimal.range
                            ? "bg-green-500"
                            : "bg-primary/70"
                        }`}
                        style={{ width: `${Math.max(4, bin.pregnancy_rate * 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
