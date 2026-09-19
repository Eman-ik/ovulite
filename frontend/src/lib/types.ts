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
  /** Site this record belongs to. `farm_location` is the imported free
   *  text kept as the source record; this is what new writes set. */
  laboratory_id: number | null;
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
  /** Site this record belongs to. `farm_location` is the imported free
   *  text kept as the source record; this is what new writes set. */
  laboratory_id: number | null;
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
  /** Site this record belongs to. `farm_location` is the imported free
   *  text kept as the source record; this is what new writes set. */
  laboratory_id: number | null;
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
  // Set where the stage above counts a different set of animals, so the
  // conversion percentage is deliberately absent rather than nonsensical.
  cohort_break?: boolean;
  cohort_note?: string | null;
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

// ── Vet / ET workflow ────────────────────────────────────

export type Eligibility = "Excellent" | "Acceptable" | "Not Recommended";
export type Quality = "Good" | "Fair" | "Poor";
export type CheckResult = "Pregnant" | "Open" | "Recheck" | "Lost";
export type CheckMethod = "Ultrasound" | "Rectal Palpation" | "Blood Test" | "Other";
export type CalvingOutcome = "Live Birth" | "Stillbirth" | "Abortion";
export type StepState = "Done" | "Overdue" | "Due today" | "Upcoming";

export interface RecipientEvaluation {
  evaluation_id: number;
  recipient_id: number;
  recipient_tag: string | null;
  evaluation_date: string;
  technician_id: number | null;
  technician_name: string | null;
  cl_present: boolean | null;
  cl_side: "Left" | "Right" | null;
  cl_diameter_mm: string | number | null;
  cl_quality: Quality | null;
  follicle_count: number | null;
  largest_follicle_mm: string | number | null;
  uterine_tone: Quality | null;
  progesterone_ng_ml: string | number | null;
  body_condition_score: string | number | null;
  eligibility: Eligibility | null;
  notes: string | null;
  transfer_id: number | null;
}

export interface PregnancyCheck {
  check_id: number;
  transfer_id: number;
  check_date: string;
  days_post_transfer: number | null;
  result: CheckResult;
  method: CheckMethod | null;
  technician_name: string | null;
  /** Check dated before its own transfer, or improbably long after it. */
  implausible_offset: boolean;
  notes: string | null;
}

export interface CalvingRecord {
  calving_id: number;
  transfer_id: number;
  calving_date: string;
  outcome: CalvingOutcome;
  calf_sex: "Male" | "Female" | "Unknown" | null;
  calf_weight_kg: string | number | null;
  gestation_days: number | null;
  assisted: boolean | null;
  notes: string | null;
}

export interface TransferOutcomeChain {
  transfer_id: number;
  et_date: string | null;
  recipient_tag: string | null;
  checks: PregnancyCheck[];
  calving: CalvingRecord | null;
  current_status: string;
}

export interface RetentionStage {
  label: string;
  n: number;
  pregnant: number;
  rate_pct: number | null;
  retained_from_previous_pct: number | null;
}

export interface RetentionResponse {
  stages: RetentionStage[];
  live_birth_tracked: boolean;
  live_birth: RetentionStage | null;
  note: string;
}

export interface ProtocolStep {
  step_id: number;
  protocol_id: number;
  /** Days from the enrollment start, zero-based: 0 is the start date. */
  day_offset: number;
  step_name: string;
  drug_name: string | null;
  dosage: string | null;
  route: string | null;
  is_transfer_day: boolean;
  notes: string | null;
}

export interface ScheduledStep {
  step_id: number;
  day_offset: number;
  step_name: string;
  drug_name: string | null;
  dosage: string | null;
  route: string | null;
  is_transfer_day: boolean;
  due_date: string;
  state: StepState;
  completed_on: string | null;
  days_from_today: number;
}

export interface EnrollmentSchedule {
  enrollment_id: number;
  recipient_id: number;
  recipient_tag: string | null;
  protocol_id: number;
  protocol_name: string | null;
  start_date: string;
  status: string;
  transfer_id: number | null;
  steps: ScheduledStep[];
  /** False when the protocol has no step template defined yet. */
  has_schedule: boolean;
  next_step: ScheduledStep | null;
  overdue_count: number;
  completed_count: number;
  total_steps: number;
  transfer_due_date: string | null;
  current_stage: string;
}

export interface BoardCount {
  key: string;
  label: string;
  count: number;
  is_estimated: boolean;
  /** What was actually counted, so the number can be checked. */
  basis: string;
}

export interface VetBoardResponse {
  as_of: string;
  counts: BoardCount[];
  protocols_without_steps: string[];
  note: string;
}

// ── Laboratory workflow ──────────────────────────────────

export type EmbryoStatus =
  | "In Culture"
  | "Transferable"
  | "Frozen"
  | "Assigned"
  | "Transferred"
  | "Discarded";

export const EMBRYO_STATUSES: EmbryoStatus[] = [
  "In Culture",
  "Transferable",
  "Frozen",
  "Assigned",
  "Transferred",
  "Discarded",
];

export interface LabCount {
  key: string;
  label: string;
  count: number;
  is_estimated: boolean;
  basis: string;
}

export interface WorkflowStage {
  label: string;
  /** Null when the backing column is entirely unrecorded — not a zero. */
  count: number | null;
  unavailable_reason: string | null;
}

export interface LabBoardResponse {
  as_of: string;
  counts: LabCount[];
  workflow: WorkflowStage[];
  note: string;
}

export interface InventoryRow {
  embryo_id: number;
  donor_tag: string | null;
  sire_name: string | null;
  opu_date: string | null;
  stage: number | null;
  grade: number | null;
  fresh_or_frozen: string | null;
  cane_number: string | null;
  freezing_date: string | null;
  status: string | null;
  transfer_id: number | null;
  observation_count: number;
}

export interface InventoryResponse {
  rows: InventoryRow[];
  total: number;
  page: number;
  page_size: number;
  summary: { status: string | null; count: number }[];
  note: string;
}

export interface EmbryoObservation {
  observation_id: number;
  embryo_id: number;
  observation_date: string;
  day_number: number;
  stage: number | null;
  grade: number | null;
  stage_label: string | null;
  morphology: string | null;
  is_arrested: boolean | null;
  cell_count: number | null;
  expansion_diameter_um: string | number | null;
  embryologist_name: string | null;
  notes: string | null;
}

export interface EmbryoTimeline {
  embryo_id: number;
  donor_tag: string | null;
  sire_name: string | null;
  status: string | null;
  final_stage: number | null;
  final_grade: number | null;
  fresh_or_frozen: string | null;
  observations: EmbryoObservation[];
  transfer_id: number | null;
  note: string;
}

export interface IVMBatch {
  ivm_batch_id: number;
  opu_id: number;
  ivm_date: string | null;
  medium: string | null;
  medium_lot: string | null;
  incubation_hours: string | number | null;
  temperature_c: string | number | null;
  co2_percent: string | number | null;
  o2_percent: string | number | null;
  oocytes_in: number | null;
  mature_oocytes_out: number | null;
  embryologist_name: string | null;
  /** Null when either count is missing — a rate without its denominator. */
  maturation_rate_pct: number | null;
  notes: string | null;
}

export interface OocyteGradeSummary {
  opu_id: number;
  donor_tag: string | null;
  opu_date: string;
  oocytes_recovered: number | null;
  grade_a_oocytes: number | null;
  grade_b_oocytes: number | null;
  grade_c_oocytes: number | null;
  degenerated_oocytes: number | null;
  graded_total: number;
  ungraded: number | null;
  ivm_batches: IVMBatch[];
}

// ── Real model performance ───────────────────────────────

export interface ModelMetricSet {
  model_key: string;
  display_name: string;
  roc_auc: number | null;
  pr_auc: number | null;
  brier_score: number | null;
  accuracy: number | null;
  precision: number | null;
  recall: number | null;
  f1: number | null;
  confusion_matrix: Record<string, number> | null;
  /** A caveat the artifact recorded, e.g. that TabPFN was never installed. */
  note: string | null;
}

export interface ModelPerformanceResponse {
  available: boolean;
  model_version: string | null;
  trained_at: string | null;
  best_model: string | null;
  models: ModelMetricSet[];
  n_features: number | null;
  split: Record<string, unknown> | null;
  shap_top_features: [string, number][] | null;
  discrimination_vs_chance_pct: number | null;
  is_better_than_chance: boolean | null;
  interpretation: string;
  unavailable_reason: string | null;
}

export interface ExportDataset {
  key: string;
  description: string;
}


// ── Administration ────────────────────────────────────────────────────────

export interface AdminUser {
  user_id: number;
  username: string;
  role: string | null;
  full_name: string | null;
  email: string | null;
  active: boolean;
  organization_id: number | null;
  created_at: string | null;
  last_login: string | null;
}

/** A role plus what it actually grants, served from the same tuples the API
 *  enforces — so the picker cannot drift from the real permissions. */
export interface RoleDescriptor {
  role: string;
  label: string;
  description: string;
  can_write_lab: boolean;
  can_write_et: boolean;
  can_run_predictions: boolean;
  is_admin: boolean;
}

export interface Laboratory {
  laboratory_id: number;
  organization_id: number;
  name: string;
  code: string | null;
  site_type: string | null;
  address: string | null;
  city: string | null;
  country: string | null;
  contact_name: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  active: boolean;
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

/** How many records point at a site. Shown before deactivating one. */
export interface LaboratoryUsage {
  laboratory_id: number;
  name: string;
  transfers: number;
  opu_sessions: number;
  recipients: number;
}
