import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
  Shield,
  AlertTriangle,
  AlertCircle,
  Info,
  Activity,
  Users,
  RefreshCw,
  Loader2,
  TrendingUp,
  TrendingDown,
  Minus,
} from "lucide-react";

/* ─── Types ─────────────────────────────────────────────── */

interface QCAlert {
  alert_type: string;
  entity_type: string;
  entity_id: string;
  severity: string;
  metric: string;
  metric_value: number | null;
  baseline_value: number | null;
  description: string;
  period: string | null;
  timestamp: string | null;
}

interface QCSummary {
  total_records: number;
  total_batches: number;
  anomalous_batches: number;
  anomaly_rate: number;
  chart_alerts: number;
  total_alerts: number;
  technicians_analyzed: number;
  protocols_analyzed: number;
  months_analyzed: number;
}

interface TechnicianStats {
  technician_name: string;
  transfer_count: number;
  pregnancy_rate: number | null;
  avg_cl_measure: number | null;
  std_cl_measure: number | null;
  avg_embryo_grade: number | null;
  avg_bc_score: number | null;
  preg_rate_vs_mean: number | null;
}

interface EWMAPoint {
  value: number;
  ewma: number;
  target: number;
  ucl: number;
  lcl: number;
  out_of_control: boolean;
}

interface CUSUMPoint {
  value: number;
  cusum_pos: number;
  cusum_neg: number;
  threshold_pos: number;
  threshold_neg: number;
  shift_detected: boolean;
  shift_direction: string;
}

interface ControlChart {
  metric: string;
  periods: string[];
  ewma: EWMAPoint[];
  cusum: CUSUMPoint[];
  alerts: QCAlert[];
}

/* ─── Constants ─────────────────────────────────────────── */

const SEVERITY_CONFIG: Record<
  string,
  { icon: typeof AlertCircle; color: string; badge: "destructive" | "default" | "secondary" }
> = {
  critical: { icon: AlertCircle, color: "text-red-500", badge: "destructive" },
  warning: { icon: AlertTriangle, color: "text-yellow-500", badge: "default" },
  info: { icon: Info, color: "text-blue-400", badge: "secondary" },
};

/* ─── Page Component ────────────────────────────────────── */

export default function QCDashboardPage() {
  const [summary, setSummary] = useState<QCSummary | null>(null);
  const [alerts, setAlerts] = useState<QCAlert[]>([]);
  const [technicians, setTechnicians] = useState<TechnicianStats[]>([]);
  const [charts, setCharts] = useState<ControlChart[]>([]);
  const [globalPregRate, setGlobalPregRate] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeChart, setActiveChart] = useState<string>("pregnancy_rate");

  /* ── Data fetching ────────────────────────────────────── */

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sumRes, alertRes, techRes, chartRes] = await Promise.all([
        api.get("/qc/summary"),
        api.get("/qc/anomalies"),
        api.get("/qc/technicians"),
        api.get("/qc/charts"),
      ]);
      setSummary(sumRes.data);
      setAlerts(alertRes.data.alerts);
      setTechnicians(techRes.data.technicians);
      setGlobalPregRate(techRes.data.global_pregnancy_rate);
      setCharts(chartRes.data.charts);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load QC data";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const runPipeline = useCallback(
    async (withSynthetic: boolean = false) => {
      setRunning(true);
      try {
        await api.post(`/qc/run?with_synthetic=${withSynthetic}`);
        await fetchAll();
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Pipeline failed";
        setError(msg);
      } finally {
        setRunning(false);
      }
    },
    [fetchAll]
  );

  /* ── Helpers ──────────────────────────────────────────── */

  const fmt = (v: number | null | undefined, decimals = 1) =>
    v != null ? v.toFixed(decimals) : "—";

  const pct = (v: number | null | undefined) =>
    v != null ? `${(v * 100).toFixed(1)}%` : "—";

  const trendIcon = (val: number | null) => {
    if (val == null) return <Minus className="h-3 w-3 text-muted-foreground" />;
    if (val > 0.02)
      return <TrendingUp className="h-3 w-3 text-green-500" />;
    if (val < -0.02)
      return <TrendingDown className="h-3 w-3 text-red-500" />;
    return <Minus className="h-3 w-3 text-muted-foreground" />;
  };

  /* ── Loading state ────────────────────────────────────── */

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Loading QC data…</span>
      </div>
    );
  }

  if (error && !summary) {
    return (
      <div className="flex h-96 flex-col items-center justify-center gap-4">
        <AlertCircle className="h-12 w-12 text-destructive" />
        <p className="text-muted-foreground">{error}</p>
        <div className="flex gap-2">
          <Button onClick={() => runPipeline(false)}>
            <Activity className="mr-2 h-4 w-4" />
            Run QC Pipeline
          </Button>
          <Button variant="outline" onClick={() => runPipeline(true)}>
            Run with Synthetic Anomalies
          </Button>
        </div>
      </div>
    );
  }

  /* ── Active chart data ────────────────────────────────── */

  const currentChart = charts.find((c) => c.metric === activeChart) ?? charts[0];

  /* ─── Render ──────────────────────────────────────────── */

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Lab QC & Anomaly Detection</h2>
          <p className="text-muted-foreground">
            Monitor quality control metrics, detect anomalies, and track technician performance
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={fetchAll} disabled={running}>
            <RefreshCw className={`mr-2 h-4 w-4 ${running ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button size="sm" onClick={() => runPipeline(false)} disabled={running}>
            {running ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Activity className="mr-2 h-4 w-4" />
            )}
            Run Pipeline
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* Summary Cards */}
      {summary && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Total Records</CardDescription>
              <CardTitle className="text-3xl">{summary.total_records.toLocaleString()}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                {summary.total_batches} batches analyzed
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Anomalies Detected</CardDescription>
              <CardTitle className="text-3xl text-destructive">
                {summary.anomalous_batches}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                {pct(summary.anomaly_rate)} anomaly rate
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Active Alerts</CardDescription>
              <CardTitle className="text-3xl">{summary.total_alerts}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                {alerts.filter((a) => a.severity === "critical").length > 0 && (
                  <Badge variant="destructive">
                    {alerts.filter((a) => a.severity === "critical").length} critical
                  </Badge>
                )}
                {alerts.filter((a) => a.severity === "warning").length > 0 && (
                  <Badge>
                    {alerts.filter((a) => a.severity === "warning").length} warning
                  </Badge>
                )}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-2">
              <CardDescription>Technicians</CardDescription>
              <CardTitle className="text-3xl">{summary.technicians_analyzed}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                {summary.months_analyzed} months · {summary.protocols_analyzed} protocols
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Control Charts Section */}
      {charts.length > 0 && currentChart && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2">
                  <Activity className="h-5 w-5" />
                  Control Charts
                </CardTitle>
                <CardDescription>
                  EWMA and CUSUM statistical process control
                </CardDescription>
              </div>
              <div className="flex gap-1">
                {charts.map((c) => (
                  <Button
                    key={c.metric}
                    variant={activeChart === c.metric ? "default" : "outline"}
                    size="sm"
                    onClick={() => setActiveChart(c.metric)}
                  >
                    {c.metric.replace(/_/g, " ")}
                  </Button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {/* EWMA Chart (text-based visualization) */}
            <div className="mb-6">
              <h4 className="mb-3 text-sm font-medium">EWMA — {currentChart.metric.replace(/_/g, " ")}</h4>
              {currentChart.ewma.length > 0 ? (
                <div className="overflow-x-auto">
                  <div className="flex items-end gap-1" style={{ minHeight: 120 }}>
                    {currentChart.ewma.map((point, i) => {
                      const range = point.ucl - point.lcl || 1;
                      const normalizedHeight = Math.max(
                        10,
                        Math.min(100, ((point.ewma - point.lcl) / range) * 100)
                      );
                      return (
                        <div
                          key={i}
                          className="group relative flex flex-col items-center"
                          title={`Period: ${currentChart.periods[i] ?? i}\nValue: ${point.value.toFixed(3)}\nEWMA: ${point.ewma.toFixed(3)}\nUCL: ${point.ucl.toFixed(3)}\nLCL: ${point.lcl.toFixed(3)}`}
                        >
                          <div
                            className={`w-3 rounded-t transition-colors ${
                              point.out_of_control
                                ? "bg-red-500"
                                : "bg-primary/70"
                            }`}
                            style={{ height: `${normalizedHeight}px` }}
                          />
                          {point.out_of_control && (
                            <div className="absolute -top-4">
                              <AlertTriangle className="h-3 w-3 text-red-500" />
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                  <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
                    <span>{currentChart.periods[0]}</span>
                    <span>{currentChart.periods[currentChart.periods.length - 1]}</span>
                  </div>
                  <div className="mt-2 flex gap-4 text-xs text-muted-foreground">
                    <span>
                      UCL: {currentChart.ewma[0]?.ucl.toFixed(3)}
                    </span>
                    <span>
                      Target: {currentChart.ewma[0]?.target.toFixed(3)}
                    </span>
                    <span>
                      LCL: {currentChart.ewma[0]?.lcl.toFixed(3)}
                    </span>
                    <span className="text-red-500">
                      ▲ = Out of control ({currentChart.ewma.filter((p) => p.out_of_control).length})
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No EWMA data available</p>
              )}
            </div>

            {/* CUSUM Chart */}
            <div>
              <h4 className="mb-3 text-sm font-medium">CUSUM — {currentChart.metric.replace(/_/g, " ")}</h4>
              {currentChart.cusum.length > 0 ? (
                <div className="overflow-x-auto">
                  <div className="flex items-end gap-1" style={{ minHeight: 80 }}>
                    {currentChart.cusum.map((point, i) => {
                      const maxThresh = Math.max(point.threshold_pos, Math.abs(point.threshold_neg)) || 1;
                      const posH = Math.min(60, (Math.abs(point.cusum_pos) / maxThresh) * 60);
                      const negH = Math.min(60, (Math.abs(point.cusum_neg) / maxThresh) * 60);
                      return (
                        <div
                          key={i}
                          className="group relative flex flex-col items-center"
                          title={`Period: ${currentChart.periods[i] ?? i}\nC+: ${point.cusum_pos.toFixed(3)}\nC-: ${point.cusum_neg.toFixed(3)}${point.shift_detected ? "\n⚠ SHIFT DETECTED (" + point.shift_direction + ")" : ""}`}
                        >
                          <div
                            className={`w-1.5 rounded-t ${
                              point.shift_detected ? "bg-red-500" : "bg-blue-400"
                            }`}
                            style={{ height: `${Math.max(2, posH)}px` }}
                          />
                          <div
                            className={`w-1.5 rounded-b ${
                              point.shift_detected ? "bg-orange-500" : "bg-blue-300"
                            }`}
                            style={{ height: `${Math.max(2, negH)}px` }}
                          />
                        </div>
                      );
                    })}
                  </div>
                  <div className="mt-2 flex gap-4 text-xs text-muted-foreground">
                    <span className="text-blue-400">■ C+ (positive shift)</span>
                    <span className="text-blue-300">■ C− (negative shift)</span>
                    <span className="text-red-500">
                      Shifts detected: {currentChart.cusum.filter((p) => p.shift_detected).length}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No CUSUM data available</p>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Alerts Table */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            QC Alerts
          </CardTitle>
          <CardDescription>
            Anomalies detected by Isolation Forest and control chart violations
          </CardDescription>
        </CardHeader>
        <CardContent>
          {alerts.length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">
              No alerts detected. Run the QC pipeline to analyze data.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-[100px]">Severity</TableHead>
                  <TableHead>Source</TableHead>
                  <TableHead>Entity</TableHead>
                  <TableHead>Period</TableHead>
                  <TableHead>Description</TableHead>
                  <TableHead className="text-right">Value</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {alerts.slice(0, 50).map((alert, i) => {
                  const sev = SEVERITY_CONFIG[alert.severity] ?? SEVERITY_CONFIG.info;
                  const SevIcon = sev.icon;
                  return (
                    <TableRow key={i}>
                      <TableCell>
                        <Badge variant={sev.badge} className="gap-1">
                          <SevIcon className="h-3 w-3" />
                          {alert.severity}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-xs font-mono">
                        {alert.alert_type.replace(/_/g, " ")}
                      </TableCell>
                      <TableCell className="font-medium">{alert.entity_id}</TableCell>
                      <TableCell className="text-muted-foreground">
                        {alert.period ?? "—"}
                      </TableCell>
                      <TableCell className="max-w-xs truncate text-sm">
                        {alert.description}
                      </TableCell>
                      <TableCell className="text-right font-mono">
                        {alert.metric_value != null ? alert.metric_value.toFixed(3) : "—"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Technician Stats */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Users className="h-5 w-5" />
            Technician Performance
          </CardTitle>
          <CardDescription>
            Per-technician QC metrics compared to global average
            {globalPregRate != null && (
              <span className="ml-2 font-medium">
                (Global pregnancy rate: {pct(globalPregRate)})
              </span>
            )}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {technicians.length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">
              No technician data available.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Technician</TableHead>
                  <TableHead className="text-right">Transfers</TableHead>
                  <TableHead className="text-right">Preg. Rate</TableHead>
                  <TableHead className="text-right">vs Mean</TableHead>
                  <TableHead className="text-right">Avg CL (mm)</TableHead>
                  <TableHead className="text-right">Std CL</TableHead>
                  <TableHead className="text-right">Avg Grade</TableHead>
                  <TableHead className="text-right">Avg BC</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {technicians.map((tech) => (
                  <TableRow key={tech.technician_name}>
                    <TableCell className="font-medium">{tech.technician_name}</TableCell>
                    <TableCell className="text-right">{tech.transfer_count}</TableCell>
                    <TableCell className="text-right">{pct(tech.pregnancy_rate)}</TableCell>
                    <TableCell className="text-right">
                      <span className="inline-flex items-center gap-1">
                        {trendIcon(tech.preg_rate_vs_mean)}
                        {tech.preg_rate_vs_mean != null
                          ? `${(tech.preg_rate_vs_mean * 100).toFixed(1)}pp`
                          : "—"}
                      </span>
                    </TableCell>
                    <TableCell className="text-right">{fmt(tech.avg_cl_measure)}</TableCell>
                    <TableCell className="text-right">{fmt(tech.std_cl_measure, 2)}</TableCell>
                    <TableCell className="text-right">{fmt(tech.avg_embryo_grade)}</TableCell>
                    <TableCell className="text-right">{fmt(tech.avg_bc_score)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
