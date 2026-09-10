/**
 * Shared TypeScript types for API responses and entities.
 */

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Donor {
  donor_id: number;
  tag_id: string;
  breed: string | null;
  birth_weight_epd: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Sire {
  sire_id: number;
  name: string;
  breed: string | null;
  birth_weight_epd: number | null;
  semen_type: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Recipient {
  recipient_id: number;
  tag_id: string;
  farm_location: string | null;
  cow_or_heifer: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Technician {
  technician_id: number;
  name: string;
  role: string | null;
  active: boolean;
  created_at: string;
}

export interface Protocol {
  protocol_id: number;
  name: string;
  description: string | null;
  created_at: string;
}

export interface OPUSession {
  opu_id: number;
  donor_id: number;
  donor_tag: string | null;
  opu_date: string;
  technician_id: number | null;
  technician_name: string | null;
  farm_location: string | null;
  total_follicles: number | null;
  oocytes_recovered: number | null;
  viable_oocytes: number | null;
  recovery_rate: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface IVFBatch {
  ivf_batch_id: number;
  opu_id: number;
  opu_donor_tag: string | null;
  opu_date: string | null;
  sire_id: number | null;
  sire_name: string | null;
  ivf_date: string | null;
  oocytes_used: number | null;
  mature_oocytes: number | null;
  cleaved_embryos: number | null;
  blastocysts: number | null;
  degenerated_embryos: number | null;
  culture_media: string | null;
  embryologist_id: number | null;
  embryologist_name: string | null;
  cleavage_rate: number | null;
  blastocyst_rate: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Embryo {
  embryo_id: number;
  donor_id: number | null;
  sire_id: number | null;
  opu_id: number | null;
  ivf_batch_id: number | null;
  opu_date: string | null;
  stage: number | null;
  grade: number | null;
  fresh_or_frozen: string | null;
  cane_number: string | null;
  freezing_date: string | null;
  ai_grade: number | null;
  ai_viability: number | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface ETTransfer {
  transfer_id: number;
  et_number: number | null;
  lab: string | null;
  satellite: string | null;
  customer_id: string | null;
  et_date: string;
  farm_location: string | null;
  recipient_id: number | null;
  bc_score: number | null;
  cl_side: string | null;
  cl_measure_mm: number | null;
  protocol_id: number | null;
  protocol_name: string | null;
  embryo_stage: number | null;
  embryo_grade: number | null;
  fresh_or_frozen: string | null;
}

/* AI Agent Types */

export interface AgentQueryRequest {
  input: string;
  session_id?: string;
}

export interface AgentQueryResponse {
  output: string;
  used_tools: string[];
  intermediate_steps?: Array<Record<string, unknown>>;
  is_domain_refusal: boolean;
}

export interface AgentHealthResponse {
  status: "healthy" | "error";
  vectorstore_status: string;
  lab_data_status: string;
  message?: string;
}

export interface ETTransferDetail extends ETTransfer {
  donor_tag?: string | null;
  donor_breed?: string | null;
  sire_name?: string | null;
  recipient_tag?: string | null;
  technician_name?: string | null;
  pc1_result: string | null;
  embryo_id?: number | null;
  heat_observed?: boolean | null;
  heat_day?: number | null;
  technician_id?: number | null;
  assistant_name?: string | null;
  pc1_date?: string | null;
  donor_id?: number | null;
  sire_id?: number | null;
  opu_date?: string | null;
  cane_number?: string | null;
}

/* Analytics API Types (backend/app/schemas/analytics.py) */

export interface AnalyticsDateRange {
  first: string | null;
  last: string | null;
  span_months: number;
}

export interface AnalyticsEntityCounts {
  donors: number;
  recipients: number;
  technicians: number;
  protocols: number;
  sires: number;
}

export interface AnalyticsFreshFrozenStats {
  n: number;
  pregnant: number;
  rate: number | null;
}

export interface AnalyticsKPIResponse {
  total_transfers: number;
  with_outcome: number;
  pregnant: number;
  open: number;
  pregnancy_rate: number | null;
  embryo_utilization: number | null;
  unique_embryos: number | null;
  date_range: AnalyticsDateRange;
  entity_counts: AnalyticsEntityCounts;
  fresh_vs_frozen: Record<string, AnalyticsFreshFrozenStats>;
}

export interface AnalyticsMonthlyTrend {
  month: string;
  n_transfers: number;
  n_pregnant: number;
  pregnancy_rate: number;
  avg_cl: number | null;
}

export interface AnalyticsFunnelStage {
  stage: string;
  count: number;
  rate_from_previous: number | null;
}

export interface AnalyticsFunnelResponse {
  stages: AnalyticsFunnelStage[];
}

export interface AnalyticsProtocolRate {
  protocol_name: string;
  n_transfers: number;
  n_pregnant: number;
  pregnancy_rate: number;
  ci_lower: number;
  ci_upper: number;
}

export interface AnalyticsProtocolRatesResponse {
  protocols: AnalyticsProtocolRate[];
  total: number;
}

export interface AnalyticsProtocolRegression {
  coefficients: Record<string, number>;
  odds_ratios: Record<string, number>;
  intercept: number;
  n_samples: number;
  feature_names: string[];
  protocol_classes: string[];
  error: string | null;
}

export interface AnalyticsFeatureImportance {
  mean: number;
  std: number;
}

export interface AnalyticsProtocolImportance {
  feature_importances: Record<string, AnalyticsFeatureImportance>;
  protocol_total_importance: number;
  n_samples: number;
  error: string | null;
}

export interface AnalyticsDonorStats {
  donor_tag: string;
  breed: string | null;
  n_transfers: number;
  n_pregnant: number;
  pregnancy_rate: number;
  avg_cl: number | null;
  first_date: string | null;
  last_date: string | null;
  active_months: number;
}

export interface AnalyticsDonorStatsResponse {
  donors: AnalyticsDonorStats[];
  total: number;
}

export interface AnalyticsBiomarkerBin {
  range: string;
  n: number;
  pregnancy_rate: number;
  ci_lower: number | null;
  ci_upper: number | null;
  mean_value: number | null;
}

export interface AnalyticsBiomarkerResult {
  biomarker: string | null;
  bins: AnalyticsBiomarkerBin[];
  optimal_range: AnalyticsBiomarkerBin | null;
  optimal_bin: AnalyticsBiomarkerBin | null;
  overall_rate: number | null;
  total_records: number;
  error: string | null;
}

export interface AnalyticsBiomarkersResponse {
  cl_measure: AnalyticsBiomarkerResult | null;
  bc_score: AnalyticsBiomarkerResult | null;
  heat_day: AnalyticsBiomarkerResult | null;
}

/* Homepage Dashboard API Types (backend/app/schemas/dashboard.py) — live-queried, not cached */

export interface DashboardFilterValues {
  date_from?: string;
  date_to?: string;
  farm_location?: string;
  breed?: string;
  donor_id?: number;
  sire_id?: number;
  embryologist_id?: number;
  technician_id?: number;
  protocol_id?: number;
  fresh_or_frozen?: string;
}

export interface LabeledOption {
  id: number;
  label: string;
}

export interface DashboardFilterOptions {
  donors: LabeledOption[];
  sires: LabeledOption[];
  technicians: LabeledOption[];
  protocols: LabeledOption[];
  breeds: string[];
  farm_locations: string[];
  fresh_or_frozen: string[];
}

export interface DashboardSparklinePoint {
  bucket: string;
  value: number | null;
}

export interface DashboardKpiItem {
  key: string;
  label: string;
  value: number | null;
  unit: "count" | "percent";
  delta_pct: number | null;
  delta_direction: "up" | "down" | "flat" | null;
  sparkline: DashboardSparklinePoint[];
  comparison_label: string;
}

export interface DashboardKpiResponse {
  kpis: DashboardKpiItem[];
  date_from: string;
  date_to: string;
}

export interface DashboardFunnelStage {
  name: string;
  value: number;
  conversion_pct_from_previous: number | null;
  conversion_pct_from_first: number | null;
}

export interface DashboardOmittedStage {
  name: string;
  reason: string;
}

export interface DashboardFunnelResponse {
  stages: DashboardFunnelStage[];
  omitted_stages: DashboardOmittedStage[];
}

export interface DashboardTrendPoint {
  bucket_label: string;
  value: number | null;
  n: number;
}

export interface DashboardTrendResponse {
  metric: string;
  granularity: "day" | "week" | "month";
  points: DashboardTrendPoint[];
}

export interface DashboardOperationsResponse {
  opu_sessions_today: number;
  ivf_batches_in_culture: number;
  embryos_pending_grading: number;
  transfers_scheduled_today: number;
  pregnancy_checks_due: number;
  predictions_pending_outcome: number;
  estimated_fields: string[];
}

export interface DashboardPipelineRow {
  stage: "opu" | "ivf" | "grading" | "transfer_scheduled" | "pending_pc";
  entity_id: number;
  label: string;
  date: string | null;
  detail: string | null;
}

export interface DashboardAlertItem {
  severity: "critical" | "warning" | "info";
  title: string;
  detail: string;
  metric_key: string;
}

export interface DashboardAlertsResponse {
  alerts: DashboardAlertItem[];
}

export interface DashboardPerformanceRow {
  id: number;
  label: string;
  n_transfers: number;
  pregnancy_rate: number | null;
  insufficient_data: boolean;
}

export interface DashboardPerformanceResponse {
  dimension: "donor" | "sire" | "protocol" | "technician";
  rows: DashboardPerformanceRow[];
}

export interface DashboardDataQualityRow {
  table: string;
  field: string;
  total: number;
  missing: number;
  missing_pct: number;
  stale: boolean;
}

export interface DashboardDataQualityResponse {
  rows: DashboardDataQualityRow[];
}

export interface DashboardHighRiskTransfer {
  transfer_id: number;
  et_date: string | null;
  probability: number;
  risk_band: string | null;
  predicted_at: string;
}

export interface DashboardAISummaryResponse {
  pending_predictions_count: number;
  high_risk_transfers: DashboardHighRiskTransfer[];
}

// ── Research (comparative outcome analyses) ──────────────

export interface RateCell {
  n: number;
  successes: number;
  rate_pct: number | null;
  ci_low_pct: number | null;
  ci_high_pct: number | null;
  insufficient_data: boolean;
}

export interface DonorSireCell extends RateCell {
  donor_id: number;
  donor_tag: string;
  sire_id: number;
  sire_name: string;
}

export interface DonorSireResponse {
  min_sample_size: number;
  donors: string[];
  sires: string[];
  cells: DonorSireCell[];
  overall: RateCell;
  note: string;
}

export interface ProtocolComparisonRow extends RateCell {
  protocol_id: number;
  protocol_name: string;
  is_baseline: boolean;
  /** Pooled comparison — ignores when each protocol was used. */
  diff_vs_baseline_pp: number | null;
  p_value: number | null;
  significant_at_05: boolean | null;
  /** Mantel-Haenszel difference, stratified by month. */
  adjusted_diff_pp: number | null;
  adjusted_p_value: number | null;
  adjusted_significant_at_05: boolean | null;
  strata_compared: number;
  time_overlap_pct: number | null;
  confounded: boolean;
  confound_reason: string | null;
}

export interface PeriodRate extends RateCell {
  period: string;
}

export interface ProtocolComparisonResponse {
  min_sample_size: number;
  baseline_protocol: string | null;
  rows: ProtocolComparisonRow[];
  confounding_detected: boolean;
  warning: string | null;
  period_rates: PeriodRate[];
  note: string;
}

export interface FactorLevel extends RateCell {
  label: string;
}

export interface OutcomeFactor {
  key: string;
  label: string;
  levels: FactorLevel[];
  available: boolean;
  unavailable_reason: string | null;
}

export interface OutcomeFactorsResponse {
  min_sample_size: number;
  factors: OutcomeFactor[];
  overall: RateCell;
}

// ── Change attribution ───────────────────────────────────

export interface GroupContribution {
  label: string;
  share_before: number;
  share_after: number;
  rate_before_pct: number | null;
  rate_after_pct: number | null;
  n_before: number;
  n_after: number;
  /** Contribution from this group's share of the population changing. */
  mix_pp: number;
  /** Contribution from this group's own rate changing. */
  rate_pp: number;
  only_in: string | null;
}

export interface Decomposition {
  dimension: string;
  mix_pp: number;
  rate_pp: number;
  mix_share: number;
  verdict: string;
  groups: GroupContribution[];
}

export interface ChangePoint {
  period: string;
  n_before: number;
  n_after: number;
  rate_before_pct: number;
  rate_after_pct: number;
  delta_pp: number;
  z_score: number;
  permutation_p: number;
  decompositions: Decomposition[];
  summary: string;
}

export interface AttributionResponse {
  change_point: ChangePoint | null;
  series: PeriodRate[];
  dimensions_tested: string[];
  note: string;
}
