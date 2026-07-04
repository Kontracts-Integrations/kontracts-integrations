import axios, { AxiosInstance, AxiosError } from "axios";
import { getSession, signOut } from "next-auth/react";
import type {
  Connection,
  ConnectionCreate,
  ConnectionUpdate,
  ConnectionTestResult,
  FieldMapping,
  MappingTemplate,
  MappingTemplateCreate,
  MappingTemplateUpdate,
  MappingVersion,
  SyncRun,
  SyncRunDetail,
  LogEntry,
  SourceObject,
  SourceField,
  SourceFilter,
  TririgaModule,
  TririgaField,
  KontractsEndpoint,
  KontractsField,
} from "@/types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const http: AxiosInstance = axios.create({
  baseURL: `${BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
  timeout: 30000,
});

http.interceptors.request.use(async (config) => {
  const session = await getSession();
  const token = (session as { accessToken?: string } | null)?.accessToken;
  if (token) {
    config.headers["Authorization"] = `Bearer ${token}`;
  }
  return config;
});

http.interceptors.response.use(
  (r) => r,
  async (err: AxiosError) => {
    if (err.response?.status === 401) {
      await signOut({ callbackUrl: "/login" });
    }
    const detail =
      (err.response?.data as { detail?: string })?.detail || err.message;
    return Promise.reject(new Error(typeof detail === "string" ? detail : JSON.stringify(detail)));
  }
);

// ──────────────────────────────────────────────
// Connections
// ──────────────────────────────────────────────

export const connectionsApi = {
  list: async (): Promise<Connection[]> => {
    const r = await http.get<Connection[]>("/connections/");
    return r.data;
  },
  get: async (id: number): Promise<Connection> => {
    const r = await http.get<Connection>(`/connections/${id}`);
    return r.data;
  },
  create: async (payload: ConnectionCreate): Promise<Connection> => {
    const r = await http.post<Connection>("/connections/", payload);
    return r.data;
  },
  update: async (id: number, payload: ConnectionUpdate): Promise<Connection> => {
    const r = await http.put<Connection>(`/connections/${id}`, payload);
    return r.data;
  },
  delete: async (id: number): Promise<void> => {
    await http.delete(`/connections/${id}`);
  },
  test: async (id: number): Promise<ConnectionTestResult> => {
    const r = await http.post<ConnectionTestResult>(`/connections/${id}/test`);
    return r.data;
  },
};

// ──────────────────────────────────────────────
// TRIRIGA
// ──────────────────────────────────────────────

export const tririgaApi = {
  getModules: async (connectionId?: number): Promise<TririgaModule[]> => {
    const params = connectionId ? { connection_id: connectionId } : {};
    const r = await http.get<{ modules: TririgaModule[] }>("/tririga/modules", { params });
    return r.data.modules;
  },
  getFields: async (moduleName: string, connectionId?: number): Promise<TririgaField[]> => {
    const params: Record<string, unknown> = { module_name: moduleName };
    if (connectionId) params.connection_id = connectionId;
    const r = await http.get<{ fields: TririgaField[] }>("/tririga/fields", { params });
    return r.data.fields;
  },
  runQuery: async (
    moduleName: string,
    queryName: string,
    connectionId?: number,
    maxRecords = 100
  ): Promise<Record<string, unknown>[]> => {
    const r = await http.post<{ records: Record<string, unknown>[]; count: number }>(
      "/tririga/query",
      {
        connection_id: connectionId,
        module_name: moduleName,
        query_name: queryName,
        max_records: maxRecords,
      }
    );
    return r.data.records;
  },
  preview: async (
    moduleName: string,
    queryName: string,
    connectionId?: number
  ): Promise<{
    records: Record<string, unknown>[];
    fields: TririgaField[];
    count: number;
  }> => {
    const r = await http.post("/tririga/preview", {
      connection_id: connectionId,
      module_name: moduleName,
      query_name: queryName,
      max_records: 5,
    });
    return r.data;
  },
};

// ──────────────────────────────────────────────
// Source (generic multi-source API)
// ──────────────────────────────────────────────

export const sourceApi = {
  getObjects: async (connectionId?: number): Promise<SourceObject[]> => {
    const params = connectionId ? { connection_id: connectionId } : {};
    const r = await http.get<{ objects: SourceObject[] }>("/source/objects", { params });
    return r.data.objects;
  },
  getBusinessObjects: async (moduleName: string, connectionId?: number): Promise<SourceObject[]> => {
    const params: Record<string, unknown> = { module_name: moduleName };
    if (connectionId) params.connection_id = connectionId;
    const r = await http.get<{ business_objects: SourceObject[] }>("/source/business-objects", { params });
    return r.data.business_objects;
  },
  getFields: async (objectName: string, connectionId?: number, moduleName?: string): Promise<SourceField[]> => {
    const params: Record<string, unknown> = { object_name: objectName };
    if (connectionId) params.connection_id = connectionId;
    if (moduleName) params.module_name = moduleName;
    const r = await http.get<{ fields: SourceField[] }>("/source/fields", { params });
    return r.data.fields;
  },
  getAssociatedObjects: async (
    objectTypeId: number,
    connectionId?: number
  ): Promise<{ module_name: string; object_type_name: string; association_name: string }[]> => {
    const params: Record<string, unknown> = { object_type_id: objectTypeId };
    if (connectionId) params.connection_id = connectionId;
    const r = await http.get<{ associations: { module_name: string; object_type_name: string; association_name: string }[] }>(
      "/source/associated-objects",
      { params }
    );
    return r.data.associations;
  },
  preview: async (
    objectName: string,
    moduleName?: string,
    fieldNames?: string[],
    connectionId?: number,
    sourceFilters?: SourceFilter[],
    filterMatch?: string
  ): Promise<{ records: Record<string, unknown>[]; fields: SourceField[]; count: number }> => {
    const r = await http.post("/source/preview", {
      connection_id: connectionId,
      object_name: objectName,
      module_name: moduleName || null,
      field_names: fieldNames && fieldNames.length ? fieldNames : null,
      source_filters: sourceFilters && sourceFilters.length ? sourceFilters : null,
      filter_match: filterMatch || "all",
      max_records: 5,
    });
    return r.data;
  },
};

// ──────────────────────────────────────────────
// Kontracts
// ──────────────────────────────────────────────

export const kontractsApi = {
  getEndpoints: async (connectionId?: number): Promise<KontractsEndpoint[]> => {
    const params = connectionId ? { connection_id: connectionId } : {};
    const r = await http.get<{ endpoints: KontractsEndpoint[] }>("/kontracts/endpoints", {
      params,
    });
    return r.data.endpoints;
  },
  getSchema: async (
    endpoint: string,
    method: string,
    connectionId?: number
  ): Promise<KontractsField[]> => {
    const params: Record<string, unknown> = { endpoint, method };
    if (connectionId) params.connection_id = connectionId;
    const r = await http.get<{ fields: KontractsField[] }>("/kontracts/schema", { params });
    return r.data.fields;
  },
  health: async (connectionId?: number): Promise<Record<string, unknown>> => {
    const params = connectionId ? { connection_id: connectionId } : {};
    const r = await http.get("/kontracts/health", { params });
    return r.data;
  },
};

// ──────────────────────────────────────────────
// Mappings
// ──────────────────────────────────────────────

export const mappingsApi = {
  list: async (activeOnly = false): Promise<MappingTemplate[]> => {
    const r = await http.get<MappingTemplate[]>("/mappings/", {
      params: { active_only: activeOnly },
    });
    return r.data;
  },
  get: async (id: number): Promise<MappingTemplate> => {
    const r = await http.get<MappingTemplate>(`/mappings/${id}`);
    return r.data;
  },
  create: async (payload: MappingTemplateCreate): Promise<MappingTemplate> => {
    const r = await http.post<MappingTemplate>("/mappings/", payload);
    return r.data;
  },
  update: async (id: number, payload: MappingTemplateUpdate): Promise<MappingTemplate> => {
    const r = await http.put<MappingTemplate>(`/mappings/${id}`, payload);
    return r.data;
  },
  delete: async (id: number): Promise<void> => {
    await http.delete(`/mappings/${id}`);
  },
  getVersions: async (id: number): Promise<MappingVersion[]> => {
    const r = await http.get<MappingVersion[]>(`/mappings/${id}/versions`);
    return r.data;
  },
  export: async (id: number): Promise<Blob> => {
    // Authenticated blob download (a plain window.open can't attach the Bearer token).
    const r = await http.get(`/mappings/${id}/export`, { responseType: "blob" });
    return r.data as Blob;
  },
  import: async (
    payload: Record<string, unknown>,
    nameOverride?: string
  ): Promise<MappingTemplate> => {
    const r = await http.post<MappingTemplate>("/mappings/import", payload, {
      params: nameOverride ? { name_override: nameOverride } : undefined,
    });
    return r.data;
  },
  previewMapping: async (
    id: number,
    records: Record<string, unknown>[],
    fieldMappings?: FieldMapping[]
  ): Promise<{
    records: { mapped: Record<string, unknown>; warnings: string[]; error: string | null }[];
    count: number;
  }> => {
    const r = await http.post(`/mappings/${id}/preview`, {
      records,
      field_mappings: fieldMappings,
    });
    return r.data;
  },
};

// ──────────────────────────────────────────────
// Runs
// ──────────────────────────────────────────────

export const runsApi = {
  list: async (params?: {
    mapping_id?: number;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<SyncRun[]> => {
    const r = await http.get<SyncRun[]>("/runs/", { params });
    return r.data;
  },
  get: async (id: number): Promise<SyncRunDetail> => {
    const r = await http.get<SyncRunDetail>(`/runs/${id}`);
    return r.data;
  },
  trigger: async (
    mappingTemplateId: number,
    triggeredBy = "ui"
  ): Promise<SyncRun> => {
    const r = await http.post<SyncRun>("/runs/", {
      mapping_template_id: mappingTemplateId,
      triggered_by: triggeredBy,
    });
    return r.data;
  },
  retry: async (runId: number): Promise<SyncRun> => {
    const r = await http.post<SyncRun>(`/runs/${runId}/retry`);
    return r.data;
  },
  cancel: async (runId: number): Promise<SyncRun> => {
    const r = await http.post<SyncRun>(`/runs/${runId}/cancel`);
    return r.data;
  },
  exportRecords: async (
    runId: number,
    status: string,
    category: string,
    errorMessages: string[]
  ): Promise<Blob> => {
    // Fetch through the authenticated client (adds the Bearer token) as a blob,
    // since a plain window.open navigation can't attach the auth header.
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    if (category) params.set("category", category);
    errorMessages.forEach((m) => params.append("error_message", m));
    const r = await http.get(`/runs/${runId}/export`, {
      params,
      responseType: "blob",
    });
    return r.data as Blob;
  },
};

// ──────────────────────────────────────────────
// Logs
// ──────────────────────────────────────────────

export const logsApi = {
  list: async (params?: {
    run_id?: number;
    level?: string;
    component?: string;
    search?: string;
    limit?: number;
    offset?: number;
  }): Promise<LogEntry[]> => {
    const r = await http.get<LogEntry[]>("/logs/", { params });
    return r.data;
  },
  stats: async (runId?: number): Promise<{ stats: Record<string, number> }> => {
    const params = runId !== undefined ? { run_id: runId } : {};
    const r = await http.get<{ stats: Record<string, number> }>("/logs/stats", { params });
    return r.data;
  },
};

// ──────────────────────────────────────────────
// Health
// ──────────────────────────────────────────────

export const healthApi = {
  check: async (): Promise<{ status: string; demo_mode: boolean; version: string }> => {
    const r = await axios.get(`${BASE_URL}/health`);
    return r.data;
  },
};
