"use client";

import { useState, useCallback, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { sourceApi, kontractsApi, connectionsApi, mappingsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MappingRow } from "./MappingRow";
import { FieldPanel } from "./FieldPanel";
import { DataPreview } from "./DataPreview";
import { generateId, cn } from "@/lib/utils";
import { Plus, Save, Loader2, Pencil } from "lucide-react";
import type { FieldMapping, MappingTemplate, SourceField, KontractsField } from "@/types";

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

  // Preview data (source records)
  const { data: previewData } = useQuery({
    queryKey: ["source-preview", sourceObject, sourceQuery, sourceConnId],
    queryFn: () => sourceApi.preview(sourceObject, sourceQuery, sourceConnId),
    enabled: !!sourceObject && !!sourceQuery,
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
                <Select value={sourceConnId ? String(sourceConnId) : "__default__"} onValueChange={(v) => setSourceConnId(v === "__default__" ? undefined : parseInt(v))}>
                  <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Default (env)" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__default__">Default (from env)</SelectItem>
                    {sourceConns.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Kontracts Connection</Label>
                <Select value={targetConnId ? String(targetConnId) : "__default__"} onValueChange={(v) => setTargetConnId(v === "__default__" ? undefined : parseInt(v))}>
                  <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Default (env)" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__default__">Default (from env)</SelectItem>
                    {kontractsConns.map((c) => <SelectItem key={c.id} value={String(c.id)}>{c.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">Kontracts Endpoint</Label>
                <Select value={kontractsEndpoint} onValueChange={setKontractsEndpoint}>
                  <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Select endpoint..." /></SelectTrigger>
                  <SelectContent>
                    {endpoints.filter((e) => e.has_request_body).map((e) => (
                      <SelectItem key={`${e.method}:${e.path}`} value={e.path}>
                        <span className="font-mono text-xs">{e.method}</span> <span>{e.path}</span>
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* TRIRIGA Module + BO */}
            <div className="grid grid-cols-2 gap-3 border-l-4 border-l-blue-400 pl-3 rounded-sm">
              <div className="space-y-1">
                <Label className="text-xs">TRIRIGA Module</Label>
                <Select value={sourceModule} onValueChange={(v) => { setSourceModule(v); setSourceObject(""); setSourceObjectId(undefined); }} disabled={fetchAssociatedObjects}>
                  <SelectTrigger className="h-8 text-xs"><SelectValue placeholder="Select TRIRIGA Module..." /></SelectTrigger>
                  <SelectContent>{modules.map((m) => <SelectItem key={m.name} value={m.name}>{m.label ?? m.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-1">
                <Label className="text-xs">TRIRIGA Business Object</Label>
                <Select value={sourceObject} onValueChange={(v) => { setSourceObject(v); const bo = businessObjects.find((b) => b.name === v); setSourceObjectId(bo?.id ?? undefined); setAssocModule(""); setAssocObject(""); setAssocString(""); }} disabled={!sourceModule || boLoading || fetchAssociatedObjects}>
                  <SelectTrigger className="h-8 text-xs"><SelectValue placeholder={!sourceModule ? "Select TRIRIGA Module first..." : boLoading ? "Loading..." : "Select TRIRIGA Business Object..."} /></SelectTrigger>
                  <SelectContent>{businessObjects.map((bo) => <SelectItem key={bo.name} value={bo.name}>{bo.label ?? bo.name}</SelectItem>)}</SelectContent>
                </Select>
              </div>
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
                  <Select value={assocModule} onValueChange={(v) => { setAssocModule(v); setAssocObject(""); setAssocString(""); }} disabled={assocLoading}>
                    <SelectTrigger className="h-8 text-xs"><SelectValue placeholder={assocLoading ? "Loading..." : "Select Associated Module..."} /></SelectTrigger>
                    <SelectContent position="popper" className="max-h-72 overflow-y-auto">{assocModuleOptions.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Associated TRIRIGA Business Object</Label>
                  <Select value={assocObject} onValueChange={(v) => { setAssocObject(v); setAssocString(""); }} disabled={!assocModule}>
                    <SelectTrigger className="h-8 text-xs"><SelectValue placeholder={!assocModule ? "Select Associated Module first..." : "Select Associated Business Object..."} /></SelectTrigger>
                    <SelectContent position="popper" className="max-h-72 overflow-y-auto">{assocObjectOptions.map((o) => <SelectItem key={o} value={o}>{o}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="space-y-1">
                  <Label className="text-xs">Association String</Label>
                  <Select value={assocString} onValueChange={setAssocString} disabled={!assocObject}>
                    <SelectTrigger className="h-8 text-xs"><SelectValue placeholder={!assocObject ? "Select Associated Business Object first..." : "Select Association String..."} /></SelectTrigger>
                    <SelectContent position="popper" className="max-h-72 overflow-y-auto">{assocStringOptions.map((s) => <SelectItem key={s} value={s}>{s}</SelectItem>)}</SelectContent>
                  </Select>
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
          {previewData ? (
            <DataPreview
              sourceRecords={previewData.records}
              mappedPayloads={mappedPreviewData?.records.map((r) => r.mapped)}
              mappingWarnings={mappedPreviewData?.records.map((r) => r.warnings)}
            />
          ) : (
            <div className="rounded-lg border-2 border-dashed p-8 text-center text-sm text-muted-foreground">
              Select a source object and query name to load preview data.
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
