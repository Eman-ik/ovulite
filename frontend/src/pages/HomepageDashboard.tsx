import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowUpRight, Sparkles } from "lucide-react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { ROLE_PERMISSIONS, getRoleDisplayName } from "@/lib/roleRoutes";
import type {
  DashboardAlertsResponse,
  DashboardDataQualityResponse,
  DashboardFilterOptions,
  DashboardFilterValues,
  DashboardFunnelResponse,
  DashboardKpiResponse,
  DashboardOperationsResponse,
  DashboardPipelineRow,
  DashboardTrendResponse,
  PaginatedResponse,
} from "@/lib/types";
import KpiRow from "@/components/dashboard/KpiRow";
import FilterBar from "@/components/dashboard/FilterBar";
import ReproductiveFunnel from "@/components/dashboard/ReproductiveFunnel";
import OperationsPanel from "@/components/dashboard/OperationsPanel";
import ActivePipelineTable from "@/components/dashboard/ActivePipelineTable";
import TrendChart from "@/components/dashboard/TrendChart";
import AlertsPanel from "@/components/dashboard/AlertsPanel";
import IntelligencePanel from "@/components/dashboard/IntelligencePanel";
import InsightCards from "@/components/dashboard/InsightCards";
import PerformancePanel from "@/components/dashboard/PerformancePanel";
import DataQualityPanel from "@/components/dashboard/DataQualityPanel";

type QCSummary = {
  total_alerts: number;
  anomalous_batches: number;
  anomaly_rate: number;
};

type RoleConfig = {
  kpiKeys?: string[];
  funnelStages?: string[];
  operationsTiles?: Array<keyof DashboardOperationsResponse>;
  pipelineStages?: DashboardPipelineRow["stage"][];
  trendMetrics: { metric: string; title: string; color: string }[];
  performanceDimensions: ("donor" | "sire" | "protocol" | "technician")[];
  showIntelligence: boolean;
  showDataQuality: boolean;
  filterFields?: Array<keyof DashboardFilterValues>;
  alertFilter?: (metricKey: string) => boolean;
};

function buildRoleConfig(role: string, canViewAnalytics: boolean, canViewAllData: boolean): RoleConfig {
  if (role === "embryologist") {
    return {
      kpiKeys: ["oocytes_recovered", "maturation_rate", "cleavage_rate", "blastocyst_rate"],
      funnelStages: ["Oocytes Recovered", "Mature Oocytes", "Cleaved Embryos", "Blastocysts"],
      operationsTiles: ["opu_sessions_today", "ivf_batches_in_culture", "embryos_pending_grading"],
      pipelineStages: ["opu", "ivf", "grading"],
      trendMetrics: [{ metric: "cleavage_rate", title: "Cleavage Rate", color: "#5fbf9f" }],
      performanceDimensions: ["donor", "sire"],
      showIntelligence: canViewAnalytics,
      showDataQuality: canViewAllData,
      filterFields: ["date_from", "date_to", "farm_location", "breed", "donor_id", "sire_id", "embryologist_id", "fresh_or_frozen"],
      alertFilter: (key) => ["blastocyst_rate", "predictions_pending_outcome"].includes(key),
    };
  }
  if (role === "et team") {
    return {
      kpiKeys: ["transferable_embryos", "transfers_completed", "pregnancy_rate", "model_auc"],
      funnelStages: ["Transferable Embryos", "Transfers", "Pregnancies", "Ongoing Pregnancies"],
      operationsTiles: ["transfers_scheduled_today", "pregnancy_checks_due", "predictions_pending_outcome"],
      pipelineStages: ["transfer_scheduled", "pending_pc"],
      trendMetrics: [{ metric: "pregnancy_rate", title: "Pregnancy Rate", color: "#a8cba0" }],
      performanceDimensions: ["protocol", "technician"],
      showIntelligence: canViewAnalytics,
      showDataQuality: canViewAllData,
      filterFields: ["date_from", "date_to", "farm_location", "technician_id", "protocol_id", "fresh_or_frozen"],
      alertFilter: (key) => ["pregnancy_rate", "pregnancy_checks_due"].includes(key),
    };
  }
  // admin and viewer see everything
  return {
    trendMetrics: [
      { metric: "pregnancy_rate", title: "Pregnancy Rate", color: "#a8cba0" },
      { metric: "blastocyst_rate", title: "Blastocyst Rate", color: "#5fbf9f" },
    ],
    performanceDimensions: ["donor", "sire", "protocol", "technician"],
    showIntelligence: canViewAnalytics,
    showDataQuality: canViewAllData,
  };
}

export default function HomepageDashboard() {
  const { user } = useAuth();
  const role = (user?.role?.toLowerCase() || "viewer") as keyof typeof ROLE_PERMISSIONS;
  const permissions = ROLE_PERMISSIONS[role] ?? ROLE_PERMISSIONS.viewer;
  const roleConfig = useMemo(
    () => buildRoleConfig(role, permissions.canViewAnalytics, permissions.canViewAllData),
    [role, permissions.canViewAnalytics, permissions.canViewAllData]
  );

  const [filters, setFilters] = useState<DashboardFilterValues>({});
  const [filterOptions, setFilterOptions] = useState<DashboardFilterOptions | null>(null);
  const [kpis, setKpis] = useState<DashboardKpiResponse | null>(null);
  const [funnel, setFunnel] = useState<DashboardFunnelResponse | null>(null);
  const [operations, setOperations] = useState<DashboardOperationsResponse | null>(null);
  const [pipeline, setPipeline] = useState<DashboardPipelineRow[]>([]);
  const [alerts, setAlerts] = useState<DashboardAlertsResponse | null>(null);
  const [dataQuality, setDataQuality] = useState<DashboardDataQualityResponse | null>(null);
  const [trends, setTrends] = useState<Record<string, DashboardTrendResponse>>({});
  const [qcSummary, setQcSummary] = useState<QCSummary | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<DashboardFilterOptions>("/dashboard/filters")
      .then((res) => setFilterOptions(res.data))
      .catch(() => setFilterOptions(null));
  }, []);

  const loadCore = useCallback(async () => {
    setLoadError(null);
    try {
      const [kpiRes, funnelRes, opsRes, pipelineRes] = await Promise.all([
        api.get<DashboardKpiResponse>("/dashboard/kpis", { params: filters }),
        api.get<DashboardFunnelResponse>("/dashboard/funnel", { params: filters }),
        api.get<DashboardOperationsResponse>("/dashboard/operations", { params: filters }),
        api.get<PaginatedResponse<DashboardPipelineRow>>("/dashboard/pipeline", {
          params: { ...filters, page_size: 50 },
        }),
      ]);
      setKpis(kpiRes.data);
      setFunnel(funnelRes.data);
      setOperations(opsRes.data);
      setPipeline(pipelineRes.data.items);
    } catch {
      setLoadError("Unable to load dashboard data from the server.");
    }
  }, [filters]);

  useEffect(() => {
    loadCore();
  }, [loadCore]);

  useEffect(() => {
    api.get<DashboardAlertsResponse>("/dashboard/alerts").then((res) => setAlerts(res.data)).catch(() => setAlerts(null));
    if (roleConfig.showDataQuality) {
      api
        .get<DashboardDataQualityResponse>("/dashboard/data-quality")
        .then((res) => setDataQuality(res.data))
        .catch(() => setDataQuality(null));
    }
    api
      .get<QCSummary>("/qc/summary")
      .then((res) => setQcSummary(res.data))
      .catch(() => setQcSummary(null));
  }, [roleConfig.showDataQuality]);

  useEffect(() => {
    Promise.all(
      roleConfig.trendMetrics.map((t) =>
        api
          .get<DashboardTrendResponse>("/dashboard/trends", { params: { ...filters, metric: t.metric } })
          .then((res) => [t.metric, res.data] as const)
      )
    ).then((entries) => {
      setTrends(Object.fromEntries(entries));
    });
  }, [filters, roleConfig.trendMetrics]);

  const filteredAlerts = alerts
    ? roleConfig.alertFilter
      ? alerts.alerts.filter((a) => roleConfig.alertFilter!(a.metric_key))
      : alerts.alerts
    : [];

  const qcExtra =
    qcSummary && qcSummary.total_alerts > 0
      ? [
          {
            title: "Lab QC alerts",
            detail: `${qcSummary.total_alerts} QC alert(s) across ${qcSummary.anomalous_batches} anomalous batch(es) (${(qcSummary.anomaly_rate * 100).toFixed(1)}% anomaly rate).`,
          },
        ]
      : [];

  const heroLink = permissions.canViewAnalytics ? "/app/analytics" : "/app/cases";
  const heroLinkLabel = permissions.canViewAnalytics ? "Explore analytics" : "Browse case records";

  return (
    <div className="space-y-5">
      {/* Page header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-[26px] font-semibold tracking-tight dash-heading">Performance Overview</h1>
          <p className="mt-1 text-sm dash-muted">
            Your program's production, transfers and outcomes — all in one place.
          </p>
        </div>
        <span className="rounded-full border border-[var(--border)] bg-[var(--card)] px-3 py-1.5 text-xs dash-muted">
          Signed in as <span className="text-[var(--primary)]">{getRoleDisplayName(user?.role)}</span>
        </span>
      </div>

      {/* Hero + today's snapshot */}
      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="dash-card relative overflow-hidden !p-0 xl:col-span-2">
          <div
            className="relative h-full min-h-[220px] p-7"
            style={{
              background:
                "radial-gradient(120% 140% at 100% 0%, rgba(207,227,184,0.30) 0%, rgba(127,176,105,0.16) 38%, rgba(10,16,12,0) 72%), linear-gradient(135deg, #16241b 0%, #0e1712 60%)",
            }}
          >
            <div className="inline-flex items-center gap-2 rounded-full border border-[var(--border)] bg-black/25 px-3 py-1.5 text-[11px] font-medium tracking-wide dash-muted">
              <Sparkles className="h-3.5 w-3.5 text-[var(--primary)]" />
              Live data · updates with your filters
            </div>

            <h2 className="hero-serif mt-5 max-w-[18ch] text-[42px] text-[#eef5ea] sm:text-[52px]">
              Explore your <em className="text-[var(--primary)]">program</em>
            </h2>
            <p className="mt-3 max-w-md text-sm dash-muted">
              Track oocyte recovery through to confirmed pregnancies, and see exactly where the losses happen.
            </p>

            <Link
              to={heroLink}
              className="mt-6 inline-flex items-center gap-2 rounded-full bg-[var(--primary)] px-5 py-2.5 text-sm font-semibold text-[var(--primary-foreground)] transition hover:brightness-110"
            >
              {heroLinkLabel}
              <ArrowUpRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        <div className="dash-card flex flex-col">
          <h3 className="text-base font-semibold dash-heading">Today</h3>
          <p className="mt-1 text-xs dash-muted">What's happening right now</p>
          <div className="mt-4 flex-1">
            <OperationsPanel data={operations} tileKeys={roleConfig.operationsTiles} />
          </div>
        </div>
      </div>

      <FilterBar filters={filters} options={filterOptions} onChange={setFilters} visibleFields={roleConfig.filterFields} />

      {loadError && (
        <div className="rounded-2xl border border-[rgba(224,101,111,0.3)] bg-[rgba(224,101,111,0.12)] p-4 text-sm text-[#f0a4aa]">
          {loadError}
        </div>
      )}

      <KpiRow kpis={kpis?.kpis ?? []} keys={roleConfig.kpiKeys} />

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="dash-card xl:col-span-2">
          <h3 className="mb-4 text-base font-semibold dash-heading">Reproductive Funnel</h3>
          <ReproductiveFunnel data={funnel} stageNames={roleConfig.funnelStages} />
        </div>
        <div className="dash-card">
          {roleConfig.showIntelligence ? (
            <IntelligencePanel />
          ) : (
            <div>
              <h3 className="mb-3 text-base font-semibold dash-heading">Attention Required</h3>
              <AlertsPanel alerts={filteredAlerts} />
            </div>
          )}
        </div>
      </div>

      {kpis && (
        <div className="dash-card">
          <h3 className="mb-3 text-base font-semibold dash-heading">What Changed</h3>
          <InsightCards kpis={roleConfig.kpiKeys ? kpis.kpis.filter((k) => roleConfig.kpiKeys!.includes(k.key)) : kpis.kpis} />
        </div>
      )}

      <div className={`grid grid-cols-1 gap-5 ${roleConfig.trendMetrics.length > 1 ? "xl:grid-cols-2" : ""}`}>
        {roleConfig.trendMetrics.map((t) => (
          <div key={t.metric} className="dash-card">
            <h3 className="mb-2 text-base font-semibold dash-heading">{t.title} Trend</h3>
            <TrendChart data={trends[t.metric] ?? null} title={t.title} color={t.color} />
          </div>
        ))}
      </div>

      <div className="dash-card">
        <h3 className="mb-4 text-base font-semibold dash-heading">Performance</h3>
        <PerformancePanel filters={filters} dimensions={roleConfig.performanceDimensions} />
      </div>

      <div className="dash-card">
        <h3 className="mb-4 text-base font-semibold dash-heading">Active Pipeline</h3>
        <ActivePipelineTable rows={pipeline} stages={roleConfig.pipelineStages} />
      </div>

      <div className={`grid grid-cols-1 gap-5 ${roleConfig.showIntelligence && roleConfig.showDataQuality ? "xl:grid-cols-2" : ""}`}>
        {roleConfig.showIntelligence && (
          <div className="dash-card">
            <h3 className="mb-4 text-base font-semibold dash-heading">Attention Required</h3>
            <AlertsPanel alerts={filteredAlerts} extra={qcExtra} />
          </div>
        )}

        {roleConfig.showDataQuality && (
          <div className="dash-card">
            <h3 className="mb-4 text-base font-semibold dash-heading">Data Quality</h3>
            <DataQualityPanel data={dataQuality} />
          </div>
        )}
      </div>
    </div>
  );
}
