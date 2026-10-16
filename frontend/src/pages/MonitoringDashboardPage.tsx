import { useState, useEffect, useCallback } from "react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { normalizeRole } from "@/lib/roleRoutes";
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
  Activity,
  RefreshCw,
  Loader2,
  AlertCircle,
  AlertTriangle,
  CheckCircle2,
  History,
  Gauge,
} from "lucide-react";

/* ─── Types (mirror backend/app/schemas/monitoring.py) ─────────────── */

interface RollingMetrics {
  status: string;
  message: string | null;
  sample_size: number;
  brier_score: number | null;
  roc_auc: number | null;
  pr_auc: number | null;
  win_rate: number | null;
}

interface ModelMetricOut {
  metric_id: number;
  model_version: string;
  window_label: string | null;
  brier_score: number | null;
  roc_auc: number | null;
  pr_auc: number | null;
  win_rate: number | null;
  sample_size: number;
  metric_date: string;
  created_at: string;
}

interface DriftReport {
  model_version: string;
  current_metrics: RollingMetrics;
  performance_drift_detected: boolean;
  performance_drift_details: Record<string, unknown>;
  population_drift_detected: boolean;
  population_drift_details: Record<string, unknown>;
  drift_detected: boolean;
  retrain_recommended: boolean;
  retrain_job_id: number | null;
  retrain_suppressed_reason?: string | null;
  persisted?: boolean;
}

interface RetrainJobOut {
  job_id: number;
  reason: string;
  status: string;
  triggered_by: string;
  drift_details: Record<string, unknown> | null;
  model_version: string | null;
  artifact_path: string | null;
  triggered_at: string;
  completed_at: string | null;
}

/* ─── Helpers ────────────────────────────────────────────────────── */

const fmt = (v: number | null | undefined, decimals = 3) =>
  v != null ? v.toFixed(decimals) : "—";

const STATUS_BADGE: Record<string, "destructive" | "default" | "secondary"> = {
  PENDING: "default",
  RUNNING: "default",
  COMPLETE: "secondary",
  FAILED: "destructive",
};

/* ─── Page Component ─────────────────────────────────────────────── */

export default function MonitoringDashboardPage() {
  const { user } = useAuth();
  // Upstream had canRunPipelines()/isAdmin() helpers for its three-role model.
  // Here both actions carry the same privilege — POST /monitoring/run and the
  // acknowledge route are gated to admin and organization_admin, the same pair
  // as /qc/run and /analytics/run — so one check covers both, and it matches
  // what the API will actually allow.
  const role = normalizeRole(user?.role);
  const canRun = role === "admin" || role === "organization_admin";
  const admin = canRun;
  const [lastRunNote, setLastRunNote] = useState<string | null>(null);
  const [drift, setDrift] = useState<DriftReport | null>(null);
  const [metrics, setMetrics] = useState<ModelMetricOut[]>([]);
  const [jobs, setJobs] = useState<RetrainJobOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [driftRes, metricsRes, jobsRes] = await Promise.all([
        api.get("/monitoring/drift"),
        api.get("/monitoring/metrics"),
        api.get("/monitoring/retrain-jobs"),
      ]);
      setDrift(driftRes.data as DriftReport);
      setMetrics(
        Array.isArray((metricsRes.data as { metrics?: unknown }).metrics)
          ? (metricsRes.data as { metrics: ModelMetricOut[] }).metrics
          : []
      );
      setJobs(
        Array.isArray((jobsRes.data as { jobs?: unknown }).jobs)
          ? (jobsRes.data as { jobs: RetrainJobOut[] }).jobs
          : []
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to load monitoring data";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const runMonitoring = useCallback(async () => {
    setRunning(true);
    try {
      // Only this POST saves a snapshot / creates a retrain job. Loading the
      // page (GET /monitoring/drift) is read-only.
      const res = await api.post("/monitoring/run");
      const report = res.data as DriftReport;
      setLastRunNote(
        report.retrain_suppressed_reason ??
          (report.current_metrics.status === "ok"
            ? "Run complete: today's metric snapshot was saved."
            : `Run complete: ${report.current_metrics.message ?? "no metrics computed"}`)
      );
      await fetchAll();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Monitoring pipeline failed";
      setError(msg);
    } finally {
      setRunning(false);
    }
  }, [fetchAll]);

  const acknowledge = useCallback(
    async (jobId: number, newStatus: "RUNNING" | "COMPLETE" | "FAILED") => {
      try {
        await api.post(`/monitoring/retrain-jobs/${jobId}/acknowledge?new_status=${newStatus}`);
        await fetchAll();
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Could not update the retrain job";
        setError(msg);
      }
    },
    [fetchAll]
  );

  if (loading) {
    return (
      <div className="flex h-96 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <span className="ml-3 text-muted-foreground">Loading monitoring data…</span>
      </div>
    );
  }

  if (error && !drift) {
    return (
      <div className="flex h-96 flex-col items-center justify-center gap-4">
        <AlertCircle className="h-12 w-12 text-destructive" />
        <p className="text-muted-foreground">{error}</p>
        {canRun && (
          <Button onClick={runMonitoring}>
            <Activity className="mr-2 h-4 w-4" />
            Run Monitoring Pipeline
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="ov-reveal ov-stagger-1 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Outcome Tracking & Continuous Learning</h2>
          <p className="text-muted-foreground">
            Rolling model performance, drift detection, and retrain job audit trail
          </p>
        </div>
        <div className="flex w-full flex-wrap gap-2 sm:w-auto">
          <Button variant="outline" size="sm" onClick={fetchAll} disabled={running}>
            <RefreshCw className={`mr-2 h-4 w-4 ${running ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          {canRun && (
            <Button size="sm" onClick={runMonitoring} disabled={running}>
              {running ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Activity className="mr-2 h-4 w-4" />
              )}
              Run Pipeline
            </Button>
          )}
        </div>
      </div>

      {lastRunNote && (
        <div className="rounded-md border p-3 text-sm text-muted-foreground">{lastRunNote}</div>
      )}

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}

      {/* Drift banner */}
      {drift && (
        <Card
          className={`ov-reveal ov-stagger-2 ov-hover-lift ${
            drift.drift_detected ? "border-destructive" : "border-green-500/40"
          }`}
        >
          <CardHeader className="pb-2">
            <CardTitle className="flex items-center gap-2">
              {drift.drift_detected ? (
                <AlertTriangle className="h-5 w-5 text-destructive" />
              ) : (
                <CheckCircle2 className="h-5 w-5 text-green-500" />
              )}
              {drift.drift_detected ? "Drift Detected" : "Model Stable"}
              <Badge variant="secondary" className="ml-1">
                {drift.model_version}
              </Badge>
            </CardTitle>
            <CardDescription>
              {drift.retrain_recommended
                ? `Retrain recommended${
                    drift.retrain_job_id
                      ? ` — job #${drift.retrain_job_id} is open and waiting for an admin`
                      : " — run the pipeline to record a retrain job"
                  }`
                : "No retrain action needed right now"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="flex items-center gap-2 rounded-md border p-3">
                {drift.performance_drift_detected ? (
                  <AlertTriangle className="h-4 w-4 text-destructive" />
                ) : (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                )}
                <div>
                  <p className="text-sm font-medium">Performance drift</p>
                  <p className="text-xs text-muted-foreground">
                    {drift.performance_drift_detected ? "Detected" : "None"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2 rounded-md border p-3">
                {drift.population_drift_detected ? (
                  <AlertTriangle className="h-4 w-4 text-destructive" />
                ) : (
                  <CheckCircle2 className="h-4 w-4 text-green-500" />
                )}
                <div>
                  <p className="text-sm font-medium">Population drift</p>
                  <p className="text-xs text-muted-foreground">
                    {drift.population_drift_detected ? "Detected" : "None"}
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Current rolling metrics */}
      {drift && (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card className="ov-reveal ov-stagger-3 ov-hover-lift">
            <CardHeader className="pb-2">
              <CardDescription className="flex items-center gap-1">
                <Gauge className="h-3.5 w-3.5" /> Brier Score
              </CardDescription>
              <CardTitle className="text-3xl">{fmt(drift.current_metrics.brier_score)}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">lower is better</p>
            </CardContent>
          </Card>
          <Card className="ov-reveal ov-stagger-4 ov-hover-lift">
            <CardHeader className="pb-2">
              <CardDescription>ROC-AUC</CardDescription>
              <CardTitle className="text-3xl">{fmt(drift.current_metrics.roc_auc)}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">discrimination</p>
            </CardContent>
          </Card>
          <Card className="ov-reveal ov-stagger-5 ov-hover-lift">
            <CardHeader className="pb-2">
              <CardDescription>PR-AUC</CardDescription>
              <CardTitle className="text-3xl">{fmt(drift.current_metrics.pr_auc)}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">precision-recall</p>
            </CardContent>
          </Card>
          <Card className="ov-reveal ov-stagger-5 ov-hover-lift">
            <CardHeader className="pb-2">
              <CardDescription>Sample Size</CardDescription>
              <CardTitle className="text-3xl">{drift.current_metrics.sample_size}</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">{drift.current_metrics.status}</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Metric history */}
      <Card className="ov-reveal ov-stagger-5 ov-hover-lift">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <History className="h-5 w-5" />
            Metric History
          </CardTitle>
          <CardDescription>Persisted rolling-metric snapshots per model version</CardDescription>
        </CardHeader>
        <CardContent>
          {metrics.length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">
              No metric history yet. Run the monitoring pipeline to compute one.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Date</TableHead>
                  <TableHead>Model Version</TableHead>
                  <TableHead>Window</TableHead>
                  <TableHead className="text-right">Brier</TableHead>
                  <TableHead className="text-right">ROC-AUC</TableHead>
                  <TableHead className="text-right">PR-AUC</TableHead>
                  <TableHead className="text-right">Win Rate</TableHead>
                  <TableHead className="text-right">N</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {metrics.slice(0, 30).map((m) => (
                  <TableRow key={m.metric_id}>
                    <TableCell className="text-muted-foreground">{m.metric_date}</TableCell>
                    <TableCell className="font-mono text-xs">{m.model_version}</TableCell>
                    <TableCell>{m.window_label ?? "—"}</TableCell>
                    <TableCell className="text-right font-mono">{fmt(m.brier_score)}</TableCell>
                    <TableCell className="text-right font-mono">{fmt(m.roc_auc)}</TableCell>
                    <TableCell className="text-right font-mono">{fmt(m.pr_auc)}</TableCell>
                    <TableCell className="text-right font-mono">{fmt(m.win_rate)}</TableCell>
                    <TableCell className="text-right">{m.sample_size}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Retrain job audit trail */}
      <Card className="ov-reveal ov-stagger-5 ov-hover-lift">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Retrain Job Audit Trail
          </CardTitle>
          <CardDescription>
            A log of drift-triggered or manually requested retrain decisions
          </CardDescription>
        </CardHeader>
        <CardContent>
          {jobs.length === 0 ? (
            <p className="py-8 text-center text-muted-foreground">
              No retrain jobs recorded yet.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Job #</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Triggered By</TableHead>
                  <TableHead>Reason</TableHead>
                  <TableHead>Model Version</TableHead>
                  <TableHead>Triggered At</TableHead>
                  {admin && <TableHead className="text-right">Admin action</TableHead>}
                </TableRow>
              </TableHeader>
              <TableBody>
                {jobs.slice(0, 30).map((job) => (
                  <TableRow key={job.job_id}>
                    <TableCell className="font-medium">#{job.job_id}</TableCell>
                    <TableCell>
                      <Badge variant={STATUS_BADGE[job.status] ?? "secondary"}>{job.status}</Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant="outline">{job.triggered_by}</Badge>
                    </TableCell>
                    <TableCell className="max-w-xs truncate text-sm">{job.reason}</TableCell>
                    <TableCell className="font-mono text-xs">{job.model_version ?? "—"}</TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(job.triggered_at).toLocaleString()}
                    </TableCell>
                    {admin && (
                      <TableCell className="text-right">
                        {job.status === "PENDING" || job.status === "RUNNING" ? (
                          <div className="flex justify-end gap-1">
                            {job.status === "PENDING" && (
                              <Button size="sm" variant="outline" onClick={() => acknowledge(job.job_id, "RUNNING")}>
                                Acknowledge
                              </Button>
                            )}
                            <Button size="sm" variant="outline" onClick={() => acknowledge(job.job_id, "COMPLETE")}>
                              Mark complete
                            </Button>
                            <Button size="sm" variant="outline" onClick={() => acknowledge(job.job_id, "FAILED")}>
                              Mark failed
                            </Button>
                          </div>
                        ) : (
                          <span className="text-xs text-muted-foreground">closed</span>
                        )}
                      </TableCell>
                    )}
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
