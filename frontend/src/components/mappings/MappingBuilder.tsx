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
import { generateId } from "@/lib/utils";
import { Plus, Save, Loader2 } from "lucide-react";
import type { FieldMapping, MappingTemplate, SourceField, KontractsField } from "@/types";

interface Props {
  template: MappingTemplate;
  onSave: (
    updates: {
      name: string;
      description?: string;
      source_module?: string;
      source_object?: string;
      source_query?: string;
      kontracts_endpoint?: string;
      kontracts_method?: string;
      field_mappings: FieldMapping[];
      source_connection_id?: number;
      target_connection_id?: number;
    }
  ) => Promise<void>;
  saving?: boolean;
}

export function MappingBuilder({ template, onSave, saving }: Props) {
  const [name, setName] = useState(template.name);
  const [description, setDescription] = useState(template.description ?? "");
  const [sourceModule, setSourceModule] = useState(template.source_module ?? "");
  const [sourceObject, setSourceObject] = useState(template.source_object ?? "");
  const [sourceQuery, setSourceQuery] = useState(template.source_query ?? "");
  const [kontractsEndpoint, setKontractsEndpoint] = useState(template.kontracts_endpoint ?? "");
  const [kontractsMethod, setKontractsMethod] = useState(template.kontracts_method ?? "POST");
  const [sourceConnId, setSourceConnId] = useState<number | undefined>(
    template.source_connection_id ?? undefined
  );
  const [targetConnId, setTargetConnId] = useState<number | undefined>(
    template.target_connection_id ?? undefined
  );

  const initialMappings: FieldMapping[] =
    template.current_version?.field_mappings?.mappings ?? [];
  const [mappings, setMappings] = useState<FieldMapping[]>(initialMappings);

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

  const handleSave = () => {
    onSave({
      name,
      description: description || undefined,
      source_module: sourceModule || undefined,
      source_object: sourceObject || undefined,
      source_query: sourceQuery || undefined,
      kontracts_endpoint: kontractsEndpoint || undefined,
      kontracts_method: kontractsMethod,
      field_mappings: mappings,
      source_connection_id: sourceConnId,
      target_connection_id: targetConnId,
    });
  };

  return (
    <div className="flex h-full flex-col space-y-4">
      {/* Header settings */}
      <div className="grid grid-cols-2 gap-4 rounded-lg border bg-card p-4 lg:grid-cols-4">
        <div className="col-span-2 space-y-1 lg:col-span-1">
          <Label className="text-xs">Mapping Name</Label>
          <Input
            className="h-8 text-xs"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Source Connection</Label>
          <Select
            value={sourceConnId ? String(sourceConnId) : "__default__"}
            onValueChange={(v) => setSourceConnId(v === "__default__" ? undefined : parseInt(v))}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Default (env)" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__default__">Default (from env)</SelectItem>
              {sourceConns.map((c) => (
                <SelectItem key={c.id} value={String(c.id)}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Kontracts Connection</Label>
          <Select
            value={targetConnId ? String(targetConnId) : "__default__"}
            onValueChange={(v) => setTargetConnId(v === "__default__" ? undefined : parseInt(v))}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Default (env)" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__default__">Default (from env)</SelectItem>
              {kontractsConns.map((c) => (
                <SelectItem key={c.id} value={String(c.id)}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-xs">TRIRIGA Module</Label>
          <Select
            value={sourceModule}
            onValueChange={(v) => {
              setSourceModule(v);
              setSourceObject(""); // reset business object when module changes
            }}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Select module..." />
            </SelectTrigger>
            <SelectContent>
              {modules.map((m) => (
                <SelectItem key={m.name} value={m.name}>
                  {m.label ?? m.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Business Object</Label>
          <Select
            value={sourceObject}
            onValueChange={setSourceObject}
            disabled={!sourceModule || boLoading}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder={!sourceModule ? "Select module first..." : boLoading ? "Loading..." : "Select object..."} />
            </SelectTrigger>
            <SelectContent>
              {businessObjects.map((bo) => (
                <SelectItem key={bo.name} value={bo.name}>
                  {bo.label ?? bo.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Source Query / View</Label>
          <Input
            className="h-8 text-xs"
            placeholder="All Active Leases"
            value={sourceQuery}
            onChange={(e) => setSourceQuery(e.target.value)}
          />
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Kontracts Endpoint</Label>
          <Select value={kontractsEndpoint} onValueChange={setKontractsEndpoint}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Select endpoint..." />
            </SelectTrigger>
            <SelectContent>
              {endpoints
                .filter((e) => e.has_request_body)
                .map((e) => (
                  <SelectItem key={`${e.method}:${e.path}`} value={e.path}>
                    <span className="font-mono text-xs">{e.method}</span>{" "}
                    <span>{e.path}</span>
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Method</Label>
          <Select value={kontractsMethod} onValueChange={setKontractsMethod}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {["POST", "PUT", "PATCH"].map((m) => (
                <SelectItem key={m} value={m}>
                  {m}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Main builder tabs */}
      <Tabs defaultValue="builder" className="flex flex-1 flex-col overflow-hidden">
        <div className="flex items-center justify-between">
          <TabsList>
            <TabsTrigger value="builder">Field Mappings ({mappings.length})</TabsTrigger>
            <TabsTrigger value="fields">Field Reference</TabsTrigger>
            <TabsTrigger value="preview">Data Preview</TabsTrigger>
          </TabsList>

          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={addRow}>
              <Plus className="mr-1 h-4 w-4" />
              Add Row
            </Button>
            <Button size="sm" onClick={handleSave} disabled={saving}>
              {saving ? (
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
              ) : (
                <Save className="mr-1 h-4 w-4" />
              )}
              Save Mapping
            </Button>
          </div>
        </div>

        <TabsContent value="builder" className="mt-4 flex-1 overflow-auto">
          <div className="space-y-2">
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
