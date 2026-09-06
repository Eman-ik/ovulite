import { useCallback, useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import { ROLE_PERMISSIONS } from "@/lib/roleRoutes";
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
      trendMetrics: [{ metric: "cleavage_rate", title: "Cleavage Rate", color: "#0ea5e9" }],
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
      trendMetrics: [{ metric: "pregnancy_rate", title: "Pregnancy Rate", color: "#059669" }],
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
      { metric: "pregnancy_rate", title: "Pregnancy Rate", color: "#059669" },
      { metric: "blastocyst_rate", title: "Blastocyst Rate", color: "#0ea5e9" },
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

  return (
    <div className="space-y-6">
      <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
        <div className="flex flex-col gap-1">
          <div className="inline-flex w-fit items-center rounded-full border border-emerald-200 bg-emerald-50 px-4 py-1.5 text-xs font-semibold text-emerald-700">
            OVULITE · REPRODUCTIVE INTELLIGENCE
          </div>
          <h1 className="mt-2 text-3xl font-bold text-gray-900">
            Welcome back, {user?.full_name || user?.username}
          </h1>
          <p className="text-sm text-gray-500">
            Signed in as {role} · numbers below reflect the current filter selection
          </p>
        </div>
      </div>

      <FilterBar filters={filters} options={filterOptions} onChange={setFilters} visibleFields={roleConfig.filterFields} />

      {loadError && <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{loadError}</div>}

      <KpiRow kpis={kpis?.kpis ?? []} keys={roleConfig.kpiKeys} />

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50 xl:col-span-2">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Reproductive Funnel</h3>
          <ReproductiveFunnel data={funnel} stageNames={roleConfig.funnelStages} />
        </div>
        <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
          {roleConfig.showIntelligence ? (
            <IntelligencePanel />
          ) : (
            <div>
              <h3 className="mb-3 text-lg font-semibold text-gray-900">Attention Required</h3>
              <AlertsPanel alerts={filteredAlerts} />
            </div>
          )}
        </div>
      </div>

      {kpis && (
        <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
          <h3 className="mb-3 text-lg font-semibold text-gray-900">What Changed</h3>
          <InsightCards kpis={roleConfig.kpiKeys ? kpis.kpis.filter((k) => roleConfig.kpiKeys!.includes(k.key)) : kpis.kpis} />
        </div>
      )}

      <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Today's Operations</h3>
        <OperationsPanel data={operations} tileKeys={roleConfig.operationsTiles} />
      </div>

      <div className={`grid grid-cols-1 gap-6 ${roleConfig.trendMetrics.length > 1 ? "xl:grid-cols-2" : ""}`}>
        {roleConfig.trendMetrics.map((t) => (
          <div key={t.metric} className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
            <h3 className="mb-2 text-lg font-semibold text-gray-900">{t.title} Trend</h3>
            <TrendChart data={trends[t.metric] ?? null} title={t.title} color={t.color} />
          </div>
        ))}
      </div>

      <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Performance</h3>
        <PerformancePanel filters={filters} dimensions={roleConfig.performanceDimensions} />
      </div>

      <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
        <h3 className="mb-4 text-lg font-semibold text-gray-900">Active Pipeline</h3>
        <ActivePipelineTable rows={pipeline} stages={roleConfig.pipelineStages} />
      </div>

      {roleConfig.showIntelligence && (
        <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Attention Required</h3>
          <AlertsPanel alerts={filteredAlerts} extra={qcExtra} />
        </div>
      )}

      {roleConfig.showDataQuality && (
        <div className="rounded-3xl bg-white p-6 shadow-sm border border-emerald-50">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Data Quality</h3>
          <DataQualityPanel data={dataQuality} />
        </div>
      )}
    </div>
  );
}
