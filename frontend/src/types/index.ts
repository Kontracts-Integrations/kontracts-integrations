// ──────────────────────────────────────────────
// Connection types
// ──────────────────────────────────────────────

export type SourceSystemType = "tririga" | "sap_re" | "planon" | "costar" | "servicenow_wsd";
export type ConnectionType = SourceSystemType | "kontracts";

export interface Connection {
  id: number;
  name: string;
  connection_type: ConnectionType;
  base_url: string | null;
  is_active: boolean;
  last_tested_at: string | null;
  last_test_success: boolean | null;
  last_test_error: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConnectionCreate {
  name: string;
  connection_type: ConnectionType;
  base_url: string;
  credentials: Record<string, string>;
}

export interface ConnectionUpdate {
  name?: string;
  base_url?: string;
  credentials?: Record<string, string>;
  is_active?: boolean;
}

export interface ConnectionTestResult {
  success: boolean;
  message: string;
  details?: Record<string, unknown> | null;
}

// ──────────────────────────────────────────────
// Mapping types
// ──────────────────────────────────────────────

export type TransformType =
  | "direct"
  | "constant"
  | "date_format"
  | "number_convert"
  | "boolean_convert"
  | "string_template"
  | "lookup_table"
  | "json_path"
  | "currency_code"
  | "lease_lookup";

export interface FieldMapping {
  id: string;
  source_field: string;
  target_field: string;
  transform_type: TransformType;
  transform_config?: Record<string, unknown> | null;
  is_required: boolean;
  description?: string | null;
  use_associated?: boolean;
}

export interface MappingVersion {
  id: number;
  template_id: number;
  version_number: number;
  field_mappings: { mappings: FieldMapping[] };
  is_current: boolean;
  created_at: string;
}

export interface MappingTemplate {
  id: number;
  name: string;
  description: string | null;
  source_connection_id: number | null;
  target_connection_id: number | null;
  source_module: string | null;
  source_object: string | null;
  source_query: string | null;
  kontracts_endpoint: string | null;
  kontracts_method: string | null;
  fetch_associated: boolean;
  assoc_module: string | null;
  assoc_object: string | null;
  assoc_string: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  current_version: MappingVersion | null;
}

export interface MappingTemplateCreate {
  name: string;
  description?: string;
  source_connection_id?: number;
  target_connection_id?: number;
  source_module?: string;
  source_object?: string;
  source_query?: string;
  kontracts_endpoint?: string;
  kontracts_method?: string;
  field_mappings: FieldMapping[];
  fetch_associated?: boolean;
  assoc_module?: string;
  assoc_object?: string;
  assoc_string?: string;
}

export interface MappingTemplateUpdate {
  name?: string;
  description?: string;
  source_connection_id?: number;
  target_connection_id?: number;
  source_module?: string;
  source_object?: string;
  source_query?: string;
  kontracts_endpoint?: string;
  kontracts_method?: string;
  fetch_associated?: boolean;
  assoc_module?: string;
  assoc_object?: string;
  assoc_string?: string;
  field_mappings?: FieldMapping[];
  is_active?: boolean;
}

// ──────────────────────────────────────────────
// Sync run types
// ──────────────────────────────────────────────

export type RunStatus = "pending" | "running" | "completed" | "failed";
export type RecordStatus = "success" | "failed" | "skipped";

export interface SyncRun {
  id: number;
  mapping_template_id: number | null;
  status: RunStatus;
  triggered_by: string | null;
  total_records: number | null;
  success_count: number;
  failed_count: number;
  skipped_count: number;
  error_message: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export interface SyncRecord {
  id: number;
  run_id: number;
  tririga_record_id: string | null;
  kontracts_record_id: string | null;
  status: RecordStatus;
  source_data: Record<string, unknown> | null;
  mapped_data: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string;
}

export interface SyncRunDetail extends SyncRun {
  records: SyncRecord[];
  logs: LogEntry[];
}

// ──────────────────────────────────────────────
// Log types
// ──────────────────────────────────────────────

export type LogLevel = "debug" | "info" | "warning" | "error";

export interface LogEntry {
  id: number;
  run_id: number | null;
  level: LogLevel;
  message: string;
  component: string | null;
  extra: Record<string, unknown> | null;
  created_at: string;
}

// ──────────────────────────────────────────────
// Source system types
// ──────────────────────────────────────────────

export interface SourceObject {
  name: string;
  label: string;
  id?: number;
  category?: string;
}

export interface SourceField {
  name: string;
  label: string;
  type: string;
  required?: boolean;
  read_only?: boolean;
  section?: string;
}

// Backwards-compatible aliases
export type TririgaModule = SourceObject;
export type TririgaField = SourceField;

export interface TririgaOperation {
  name: string;
  category: string;
  description: string;
}

export const SOURCE_SYSTEM_LABELS: Record<SourceSystemType, string> = {
  tririga: "IBM TRIRIGA",
  sap_re: "SAP RE-FX",
  planon: "Planon",
  costar: "CoStar",
  servicenow_wsd: "ServiceNow WSD",
};

// ──────────────────────────────────────────────
// Kontracts types
// ──────────────────────────────────────────────

export interface KontractsEndpoint {
  path: string;
  method: string;
  summary: string;
  tags: string[];
  has_request_body: boolean;
  operation_id: string;
}

export interface KontractsField {
  name: string;
  type: string;
  format?: string | null;
  required: boolean;
  description: string;
  enum?: string[] | null;
  default?: unknown;
  max_length?: number | null;
}

// ──────────────────────────────────────────────
// API response wrappers
// ──────────────────────────────────────────────

export interface PaginatedResponse<T> {
  results: T[];
  count: number;
  page: number;
  page_size: number;
}

export interface ApiError {
  detail: string | { msg: string; type: string; loc: string[] }[];
}
