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

export interface Embryo {
  embryo_id: number;
  donor_id: number | null;
  sire_id: number | null;
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
