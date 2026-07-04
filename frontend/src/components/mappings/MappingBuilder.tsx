"use client";

import { useState, useCallback, useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { sourceApi, kontractsApi, connectionsApi, mappingsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MappingRow } from "./MappingRow";
import { FieldPanel } from "./FieldPanel";
import { DataPreview } from "./DataPreview";
import { generateId, cn } from "@/lib/utils";
import { Plus, Save, Loader2, Pencil, Trash2, Filter } from "lucide-react";
import type { FieldMapping, MappingTemplate, SourceField, KontractsField, SourceFilter, FilterOperator } from "@/types";

const FILTER_OPERATORS: { value: FilterOperator; label: string; needsValue: boolean }[] = [
  { value: "equals", label: "equals", needsValue: true },
  { value: "not_equals", label: "not equals", needsValue: true },
  { value: "contains", label: "contains", needsValue: true },
  { value: "not_contains", label: "does not contain", needsValue: true },
  { value: "starts_with", label: "starts with", needsValue: true },
  { value: "ends_with", label: "ends with", needsValue: true },
  { value: "is_empty", label: "is empty", needsValue: false },
  { value: "is_not_empty", label: "is not empty", needsValue: false },
  { value: "greater_than", label: "greater than", needsValue: true },
  { value: "less_than", label: "less than", needsValue: true },
  { value: "gte", label: "≥", needsValue: true },
  { value: "lte", label: "≤", needsValue: true },
  { value: "regex", label: "matches regex", needsValue: true },
];

interface Props {
  template: MappingTemplate;
  onSave: (
    updates: {
      name: string;
      description?: string | null;
      source_module?: string | null;
      source_object?: string | null;
      source_query?: string | null;
      kontracts_endpoint?: string | null;
      kontracts_method?: string;
      lookup_table_name?: string | null;
      update_existing?: boolean;
      source_filters?: SourceFilter[];
      filter_match?: string;
      field_mappings: FieldMapping[];
      source_connection_id?: number | null;
      target_connection_id?: number | null;
      fetch_associated?: boolean;
      assoc_module?: string | null;
      assoc_object?: string | null;
      assoc_string?: string | null;
    }
  ) => Promise<void>;
  saving?: boolean;
  saveRef?: React.MutableRefObject<(() => void) | null>;
}

export function MappingBuilder({ template, onSave, saving, saveRef }: Props) {
  const [name, setName] = useState(template.name);
  const [description, setDescription] = useState(template.description ?? "");
  const [sourceModule, setSourceModule] = useState(template.source_module ?? "");
  const [sourceObject, setSourceObject] = useState(template.source_object ?? "");
  const [sourceQuery, setSourceQuery] = useState(template.source_query ?? "");
  const [kontractsEndpoint, setKontractsEndpoint] = useState(template.kontracts_endpoint ?? "");
  const [kontractsMethod, setKontractsMethod] = useState(template.kontracts_method ?? "POST");
  const [lookupTableName, setLookupTableName] = useState(template.lookup_table_name ?? "");
  const [updateExisting, setUpdateExisting] = useState(template.update_existing ?? false);
  const [sourceFilters, setSourceFilters] = useState<SourceFilter[]>(template.source_filters ?? []);
  const [filterMatch, setFilterMatch] = useState(template.filter_match ?? "all");
  const [fetchAssociatedObjects, setFetchAssociatedObjects] = useState(template.fetch_associated ?? false);
  const [sourceObjectId, setSourceObjectId] = useState<number | undefined>(undefined);
  const [assocModule, setAssocModule] = useState(template.assoc_module ?? "");
  const [assocObject, setAssocObject] = useState(template.assoc_object ?? "");
  const [assocString, setAssocString] = useState(template.assoc_string ?? "");
  const [sourceConnId, setSourceConnId] = useState<number | undefined>(
    template.source_connection_id ?? undefined
  );
  const [targetConnId, setTargetConnId] = useState<number | undefined>(
    template.target_connection_id ?? undefined
  );

  const initialMappings: FieldMapping[] =
    template.current_version?.field_mappings?.mappings ?? [];
  const [mappings, setMappings] = useState<FieldMapping[]>(initialMappings);
  const [isEditing, setIsEditing] = useState(!template.current_version);

  // Sync all local state when a new version is saved (current_version.id changes)
  useEffect(() => {
    setName(template.name);
    setDescription(template.description ?? "");
    setSourceModule(template.source_module ?? "");
    setSourceObject(template.source_object ?? "");
    setSourceQuery(template.source_query ?? "");
    setKontractsEndpoint(template.kontracts_endpoint ?? "");
    setKontractsMethod(template.kontracts_method ?? "POST");
    setLookupTableName(template.lookup_table_name ?? "");
    setUpdateExisting(template.update_existing ?? false);
    setSourceFilters(template.source_filters ?? []);
    setFilterMatch(template.filter_match ?? "all");
    setSourceConnId(template.source_connection_id ?? undefined);
    setTargetConnId(template.target_connection_id ?? undefined);
    setFetchAssociatedObjects(template.fetch_associated ?? false);
    setAssocModule(template.assoc_module ?? "");
    setAssocObject(template.assoc_object ?? "");
    setAssocString(template.assoc_string ?? "");
    setMappings(template.current_version?.field_mappings?.mappings ?? []);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [template.id, template.current_version?.id]);

  // Connections list
  const { data: connections } = useQuery({
    queryKey: ["connections"],
    queryFn: () => connectionsApi.list(),
  });

  const sourceConns = connections?.filter((c) => c.connection_type !== "kontracts") ?? [];
  const kontractsConns = connections?.filter((c) => c.connection_type === "kontracts") ?? [];

  // Source fields — requires a business object to be selected
  // Passes module_name so backend calls getObjectTypeByName(moduleName, objectTypeName) correctly
  const { data: sourceFields = [], isLoading: sourceLoading } = useQuery<SourceField[]>({
    queryKey: ["source-fields", sourceObject, sourceConnId, sourceModule],
    queryFn: () => sourceApi.getFields(sourceObject, sourceConnId, sourceModule || undefined),
    enabled: !!sourceObject,
    staleTime: 5 * 60 * 1000, // cache for 5 minutes — fields don't change often
  });

  // Kontracts fields
  const { data: targetFields = [], isLoading: targetLoading } = useQuery<KontractsField[]>({
    queryKey: ["kontracts-fields", kontractsEndpoint, kontractsMethod, targetConnId],
    queryFn: () => kontractsApi.getSchema(kontractsEndpoint, kontractsMethod, targetConnId),
    enabled: !!kontractsEndpoint,
  });

  // Modules (top-level TRIRIGA modules)
  const { data: modules = [] } = useQuery({
    queryKey: ["source-modules", sourceConnId],
    queryFn: () => sourceApi.getObjects(sourceConnId),
  });

  // Business objects within the selected module
  const { data: businessObjects = [], isLoading: boLoading } = useQuery({
    queryKey: ["source-business-objects", sourceModule, sourceConnId],
    queryFn: () => sourceApi.getBusinessObjects(sourceModule, sourceConnId),
    enabled: !!sourceModule,
  });

  // Sync sourceObjectId when businessObjects loads and sourceObject is already set (e.g. from saved template)
  useEffect(() => {
    if (sourceObject && businessObjects.length > 0) {
      const bo = businessObjects.find((b) => b.name === sourceObject);
      setSourceObjectId(bo?.id ?? undefined);
    }
  }, [sourceObject, businessObjects]);

  // Fields for the associated BO (when one is selected in Row 5)
  const { data: assocFields = [], isLoading: assocFieldsLoading } = useQuery<SourceField[]>({
    queryKey: ["source-fields", assocObject, sourceConnId, assocModule],
    queryFn: () => sourceApi.getFields(assocObject, sourceConnId, assocModule || undefined),
    enabled: fetchAssociatedObjects && !!assocObject,
    staleTime: 5 * 60 * 1000,
  });

  // Associated objects — fetched via getAssociationDefinitions using the selected BO's object type ID
  const { data: associatedObjects = [], isLoading: assocLoading } = useQuery({
    queryKey: ["source-associated-objects", sourceObjectId, sourceConnId],
    queryFn: () => sourceApi.getAssociatedObjects(sourceObjectId!, sourceConnId),
    enabled: fetchAssociatedObjects && !!sourceObjectId,
  });

  const assocModuleOptions = [...new Set(associatedObjects.map((a) => a.module_name))];
  const assocObjectOptions = [...new Set(
    associatedObjects
      .filter((a) => a.module_name === assocModule)
      .map((a) => a.object_type_name)
  )];
  const assocStringOptions = associatedObjects
    .filter((a) => a.module_name === assocModule && a.object_type_name === assocObject)
    .map((a) => a.association_name);

  // Kontracts endpoints
  const { data: endpoints = [] } = useQuery({
    queryKey: ["kontracts-endpoints", targetConnId],
    queryFn: () => kontractsApi.getEndpoints(targetConnId),
  });

  // Preview data (source records) — fetched via the same dynamic query the sync
  // uses: module + object + the source fields referenced by the mappings.
  const previewFieldNames = useMemo(
    () => mappings.map((m) => m.source_field).filter((f): f is string => !!f),
    [mappings]
  );
  const activeFilters = useMemo(
    () => sourceFilters.filter((f) => f.field),
    [sourceFilters]
  );
  const {
    data: previewData,
    isFetching: previewLoading,
    error: previewError,
  } = useQuery({
    queryKey: ["source-preview", sourceObject, sourceModule, previewFieldNames.join(","), sourceConnId, JSON.stringify(activeFilters), filterMatch],
    queryFn: () => sourceApi.preview(sourceObject, sourceModule || undefined, previewFieldNames, sourceConnId, activeFilters, filterMatch),
    enabled: !!sourceObject,
  });

  // Mapped preview — apply current field mappings to source records via the backend engine
  const hasMappings = mappings.some((m) => m.source_field && m.target_field);
  const { data: mappedPreviewData } = useQuery({
    queryKey: ["mapped-preview", template.id, previewData?.records, mappings],
    queryFn: () =>
      mappingsApi.previewMapping(template.id, previewData!.records, mappings),
    enabled: !!previewData?.records.length && hasMappings,
  });

  const addRow = () => {
    setMappings((prev) => [
      ...prev,
      {
        id: generateId(),
        source_field: "",
        target_field: "",
        transform_type: "direct",
        is_required: false,
        use_associated: false,
      },
    ]);
  };

  const addFilter = () => {
    setSourceFilters((prev) => [...prev, { field: "", operator: "contains", value: "" }]);
  };
  const updateFilter = (index: number, patch: Partial<SourceFilter>) => {
    setSourceFilters((prev) => prev.map((f, i) => (i === index ? { ...f, ...patch } : f)));
  };
  const removeFilter = (index: number) => {
    setSourceFilters((prev) => prev.filter((_, i) => i !== index));
  };

  const addAssocRow = () => {
    setMappings((prev) => [
      ...prev,
      {
        id: generateId(),
        source_field: "",
        target_field: "",
        transform_type: "direct",
        is_required: false,
        use_associated: true,
      },
    ]);
  };

  const updateRow = useCallback((index: number, updated: FieldMapping) => {
    setMappings((prev) => {
      const next = [...prev];
      next[index] = updated;
      return next;
    });
  }, []);

  const deleteRow = useCallback((index: number) => {
    setMappings((prev) => prev.filter((_, i) => i !== index));
  }, []);

  const buildPayload = () => ({
    name,
    description: description || null,
    source_module: sourceModule || null,
    source_object: sourceObject || null,
    source_query: sourceQuery || null,
    kontracts_endpoint: kontractsEndpoint || null,
    kontracts_method: kontractsMethod,
    lookup_table_name: lookupTableName.trim() || null,
    update_existing: updateExisting,
    source_filters: sourceFilters.filter((f) => f.field),
    filter_match: filterMatch,
    field_mappings: mappings,
    source_connection_id: sourceConnId ?? null,
    target_connection_id: targetConnId ?? null,
    fetch_associated: fetchAssociatedObjects,
    assoc_module: assocModule || null,
    assoc_object: assocObject || null,
    assoc_string: assocString || null,
  });

  // "Save Mapping" button — saves field mappings only, never touches isEditing
  const handleSaveMappings = () => {
    onSave(buildPayload());
  };

  // Details card button — toggles read-only/edit mode and saves on lock
  const handleDetailsSave = () => {
    if (!isEditing) {
      setIsEditing(true);
      return;
    }
    onSave(buildPayload()).then(() => {
      setIsEditing(false);
    }).catch(() => {
      // keep editing mode on error so user can retry
    });
  };

  if (saveRef) saveRef.current = handleSaveMappings;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-4">
      {/* Header settings */}
      <div className="rounded-lg border bg-card px-4 py-2.5">
        {isEditing ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between border-b pb-2">
              <h2 className="text-sm font-semibold text-muted-foreground">Details</h2>
              <Button size="sm" onClick={handleDetailsSave} disabled={saving}>
                {saving ? <Loader2 className="mr-1 h-4 w-4 animate-spin" /> : <Save className="mr-1 h-4 w-4" />}
                Save
              </Button>
            </div>

            {/* Name */}
            <div className="space-y-1">
              <Label className="text-xs">Mapping Template Name</Label>
              <Input className="h-8 text-xs max-w-sm" value={name} onChange={(e) => setName(e.target.value)} />
            </div>

            {/* Connections + Endpoint */}
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-1">
                <Label className="text-xs">Source Connection</Label>
                <SearchableSelect
                  options={[
                    { value: "__default__", label: "Default (from env)" },
                    ...sourceConns.map((c) => ({ value: String(c.id), label: c.name })),
                  ]}
                  value={sourceConnId ? String(sourceConnId) : "__default__"}
                  onValueChange={(v) => setSourceConnId(v === "__default__" ? undefined : parseInt(v))}
                  placeholder="Default (env)"
                  searchPlaceholder="Search connections..."
                  widthClass="w-[240px]"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Kontracts Connection</Label>
                <SearchableSelect
                  options={[
                    { value: "__default__", label: "Default (from env)" },
                    ...kontractsConns.map((c) => ({ value: String(c.id), label: c.name })),
                  ]}
                  value={targetConnId ? String(targetConnId) : "__default__"}
                  onValueChange={(v) => setTargetConnId(v === "__default__" ? undefined : parseInt(v))}
                  placeholder="Default (env)"
                  searchPlaceholder="Search connections..."
                  widthClass="w-[240px]"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Kontracts Endpoint</Label>
                <SearchableSelect
                  options={endpoints.filter((e) => e.has_request_body).map((e) => ({
                    value: e.path,
                    label: `${e.method} ${e.path}`,
                  }))}
                  value={kontractsEndpoint}
                  onValueChange={setKontractsEndpoint}
                  placeholder="Select endpoint..."
                  searchPlaceholder="Search endpoints..."
                  widthClass="w-[280px]"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Lookup Table Name</Label>
                <Input
                  className="w-[240px]"
                  value={lookupTableName}
                  onChange={(e) => setLookupTableName(e.target.value)}
                  placeholder="e.g. lease_mappings"
                />
                <p className="text-[10px] text-muted-foreground">
                  Names the table this mapping writes created IDs into, so later mappings can look them up.
                </p>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Re-run Behavior</Label>
                <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer pt-1.5">
                  <input
                    type="checkbox"
                    className="h-3.5 w-3.5 accent-primary"
                    checked={updateExisting}
                    onChange={(e) => setUpdateExisting(e.target.checked)}
                  />
                  Update changed records on re-run
                </label>
                <p className="text-[10px] text-muted-foreground">
                  When on, subsequent runs PUT records whose mapped payload changed instead of skipping them.
                </p>
              </div>
            </div>

            {/* TRIRIGA Module + BO */}
            <div className="grid grid-cols-2 gap-3 border-l-4 border-l-blue-400 pl-3 rounded-sm">
              <div className="space-y-1">
                <Label className="text-xs">TRIRIGA Module</Label>
                <SearchableSelect
                  options={modules.map((m) => ({ value: m.name, label: m.label ?? m.name }))}
                  value={sourceModule}
                  onValueChange={(v) => { setSourceModule(v); setSourceObject(""); setSourceObjectId(undefined); }}
                  disabled={fetchAssociatedObjects}
                  placeholder="Select TRIRIGA Module..."
                  searchPlaceholder="Search modules..."
                  widthClass="w-[300px]"
                />
              </div>
              <div className="space-y-1">
                <Label className="text-xs">TRIRIGA Business Object</Label>
                <SearchableSelect
                  options={businessObjects.map((bo) => ({ value: bo.name, label: bo.label ?? bo.name }))}
                  value={sourceObject}
                  onValueChange={(v) => { setSourceObject(v); const bo = businessObjects.find((b) => b.name === v); setSourceObjectId(bo?.id ?? undefined); setAssocModule(""); setAssocObject(""); setAssocString(""); }}
                  disabled={!sourceModule || boLoading || fetchAssociatedObjects}
                  placeholder={!sourceModule ? "Select TRIRIGA Module first..." : boLoading ? "Loading..." : "Select TRIRIGA Business Object..."}
                  searchPlaceholder="Search business objects..."
                  widthClass="w-[300px]"
                />
              </div>
            </div>

            {/* Source Record Filters */}
            <div className="space-y-2 border-l-4 border-l-amber-400 pl-3 rounded-sm">
              <div className="flex items-center gap-2">
                <Filter className="h-3.5 w-3.5 text-amber-500" />
                <Label className="text-xs font-medium">Source Record Filters</Label>
                {sourceFilters.length > 1 && (
                  <div className="flex items-center gap-1 text-[11px] text-muted-foreground">
                    <span>match</span>
                    <Select value={filterMatch} onValueChange={setFilterMatch}>
                      <SelectTrigger className="h-6 w-[70px] text-[11px]"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">all</SelectItem>
                        <SelectItem value="any">any</SelectItem>
                      </SelectContent>
                    </Select>
                    <span>of the conditions</span>
                  </div>
                )}
              </div>

              {sourceFilters.map((flt, i) => {
                const opMeta = FILTER_OPERATORS.find((o) => o.value === flt.operator);
                return (
                  <div key={i} className="flex items-center gap-2">
                    <SearchableSelect
                      options={sourceFields.map((f) => ({
                        value: `${f.section || "General"}||${f.name}`,
                        label: f.label && f.label !== f.name ? `${f.name} (${f.label})` : f.name,
                      }))}
                      value={flt.field}
                      onValueChange={(v) => updateFilter(i, { field: v })}
                      disabled={!sourceObject || sourceLoading}
                      placeholder={!sourceObject ? "Select a business object first..." : "Select field..."}
                      searchPlaceholder="Search fields..."
                      widthClass="w-[260px]"
                    />
                    <Select value={flt.operator} onValueChange={(v) => updateFilter(i, { operator: v as FilterOperator })}>
                      <SelectTrigger className="h-8 w-[170px] text-xs"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        {FILTER_OPERATORS.map((o) => (
                          <SelectItem key={o.value} value={o.value} className="text-xs">{o.label}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    {opMeta?.needsValue !== false && (
                      <Input
                        className="h-8 w-[200px] text-xs"
                        value={flt.value ?? ""}
                        onChange={(e) => updateFilter(i, { value: e.target.value })}
                        placeholder="value"
                      />
                    )}
                    <Button size="icon" variant="ghost" className="h-7 w-7 text-muted-foreground hover:text-red-500" onClick={() => removeFilter(i)}>
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                );
              })}

              <Button size="sm" variant="outline" onClick={addFilter} className="h-7 text-xs border-amber-400 text-amber-600 hover:bg-amber-50 dark:hover:bg-amber-950">
                <Plus className="mr-1 h-3.5 w-3.5" />
                Add Filter
              </Button>
              <p className="text-[10px] text-muted-foreground">
                Only source records matching these conditions are synced. String comparisons are case-insensitive.
              </p>
            </div>

            {/* Fetch Associated Objects */}
            <div className={cn("flex items-center gap-2 border-l-4 pl-3 rounded-sm transition-colors", fetchAssociatedObjects ? "border-l-purple-400" : "border-l-transparent")}>
              <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer">
                <input type="checkbox" className="h-3.5 w-3.5 accent-primary" checked={fetchAssociatedObjects} onChange={(e) => { setFetchAssociatedObjects(e.target.checked); if (!e.target.checked) { setAssocModule(""); setAssocObject(""); setAssocString(""); setMappings((prev) => prev.filter((m) => !m.use_associated)); } }} />
                Fetch Associated Objects?
              </label>
            </div>

            {fetchAssociatedObjects && (
              <div className="grid grid-cols-3 gap-3 border-l-4 border-l-purple-400 pl-3 rounded-sm">
                <div className="space-y-1">
                  <Label className="text-xs">Associated TRIRIGA Module</Label>
                  <SearchableSelect
                    options={assocModuleOptions.map((m) => ({ value: m, label: m }))}
                    value={assocModule}
                    onValueChange={(v) => { setAssocModule(v); setAssocObject(""); setAssocString(""); }}
                    disabled={assocLoading}
                    placeholder={assocLoading ? "Loading..." : "Select Associated Module..."}
                    searchPlaceholder="Search modules..."
                    widthClass="w-[240px]"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Associated TRIRIGA Business Object</Label>
                  <SearchableSelect
                    options={assocObjectOptions.map((o) => ({ value: o, label: o }))}
                    value={assocObject}
                    onValueChange={(v) => { setAssocObject(v); setAssocString(""); }}
                    disabled={!assocModule}
                    placeholder={!assocModule ? "Select Associated Module first..." : "Select Associated Business Object..."}
                    searchPlaceholder="Search business objects..."
                    widthClass="w-[240px]"
                  />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Association String</Label>
                  <SearchableSelect
                    options={assocStringOptions.map((s) => ({ value: s, label: s }))}
                    value={assocString}
                    onValueChange={setAssocString}
                    disabled={!assocObject}
                    placeholder={!assocObject ? "Select Associated BO first..." : "Select Association..."}
                    searchPlaceholder="Search associations..."
                    widthClass="w-[240px]"
                  />
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Collapsed summary row */
          <div className="flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <span className="font-medium text-sm truncate">{name}</span>
              <div className="flex items-center gap-2 flex-wrap text-xs text-muted-foreground">
                {sourceModule && (
                  <span className="rounded bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300 px-1.5 py-0.5">
                    {sourceObject || sourceModule}
                  </span>
                )}
                {fetchAssociatedObjects && assocObject && (
                  <span className="rounded bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300 px-1.5 py-0.5">
                    + {assocObject}
                  </span>
                )}
                {kontractsEndpoint && (
                  <span className="rounded bg-muted px-1.5 py-0.5 font-mono">
                    {kontractsMethod} {kontractsEndpoint}
                  </span>
                )}
                {activeFilters.length > 0 && (
                  <span className="inline-flex items-center gap-1 rounded bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300 px-1.5 py-0.5">
                    <Filter className="h-3 w-3" />
                    {activeFilters.length} filter{activeFilters.length > 1 ? `s (${filterMatch})` : ""}
                  </span>
                )}
              </div>
            </div>
            <Button size="sm" variant="ghost" onClick={handleDetailsSave} disabled={saving} className="flex-shrink-0 text-xs h-7">
              <Pencil className="mr-1 h-3.5 w-3.5" />
              Edit Details
            </Button>
          </div>
        )}
      </div>

      {/* Main builder tabs */}
      <Tabs defaultValue="builder" className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="builder">Field Mappings ({mappings.length})</TabsTrigger>
            <TabsTrigger value="fields">Field Reference</TabsTrigger>
            <TabsTrigger value="preview">Data Preview</TabsTrigger>
          </TabsList>

          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={addRow} className="border-blue-400 text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-950">
              <Plus className="mr-1 h-4 w-4" />
              Add Mapping (Base BO)
            </Button>
            {fetchAssociatedObjects && (
              <Button variant="outline" size="sm" onClick={addAssocRow} className="border-purple-400 text-purple-600 hover:bg-purple-50 dark:hover:bg-purple-950">
                <Plus className="mr-1 h-4 w-4" />
                Add Mapping (Associated BO)
              </Button>
            )}
            <Button size="sm" onClick={handleSaveMappings} disabled={saving}>
              {saving ? (
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-1 h-4 w-4" />
              )}
              Save Mappings
            </Button>
          </div>
        </div>

        <TabsContent value="builder" className="mt-4 min-h-0 flex-1 overflow-y-auto">
          <div className="space-y-3">
            {mappings.length === 0 ? (
              <div className="rounded-lg border-2 border-dashed p-8 text-center text-sm text-muted-foreground">
                No field mappings yet. Click "Add Row" to create your first mapping.
              </div>
            ) : (
              mappings.map((mapping, index) => (
                <MappingRow
                  key={mapping.id}
                  mapping={mapping}
                  sourceFields={sourceFields}
                  assocFields={assocFields}
                  assocFieldsLoading={assocFieldsLoading}
                  targetFields={targetFields}
                  sourceLoading={sourceLoading}
                  onChange={(updated) => updateRow(index, updated)}
                  onDelete={() => deleteRow(index)}
                  index={index}
                />
              ))
            )}
          </div>
        </TabsContent>

        <TabsContent value="fields" className="mt-4 flex-1 overflow-hidden">
          <div className="grid h-[500px] grid-cols-2 gap-4">
            <FieldPanel
              title="Source Fields"
              fields={sourceFields}
              loading={sourceLoading}
              side="source"
            />
            <FieldPanel
              title="Kontracts Fields"
              fields={targetFields}
              loading={targetLoading}
              side="target"
            />
          </div>
        </TabsContent>

        <TabsContent value="preview" className="mt-4 overflow-auto">
          {!sourceObject ? (
            <div className="rounded-lg border-2 border-dashed p-8 text-center text-sm text-muted-foreground">
              Select a TRIRIGA business object to load preview data.
            </div>
          ) : previewError ? (
            <div className="rounded-lg border-2 border-dashed border-red-300 p-8 text-center text-sm text-red-600 dark:text-red-400">
              Failed to load preview data: {(previewError as Error).message}
            </div>
          ) : previewLoading && !previewData ? (
            <div className="flex items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Loading preview data from TRIRIGA…
            </div>
          ) : previewData ? (
            <DataPreview
              sourceRecords={previewData.records}
              mappedPayloads={mappedPreviewData?.records.map((r) => r.mapped)}
              mappingWarnings={mappedPreviewData?.records.map((r) => r.warnings)}
            />
          ) : (
            <div className="rounded-lg border-2 border-dashed p-8 text-center text-sm text-muted-foreground">
              No preview data returned.
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
