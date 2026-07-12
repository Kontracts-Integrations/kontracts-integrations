"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mappingsApi, runsApi, connectionsApi, sourceApi, kontractsApi } from "@/lib/api";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { toast } from "@/components/ui/toaster";
import { cn, formatRelativeTime, getStatusColor } from "@/lib/utils";
import { Plus, FileCode, Play, Pencil, Trash2, Loader2, CheckCircle2, XCircle } from "lucide-react";
import type { MappingTemplate } from "@/types";

function MappingCard({ mapping }: { mapping: MappingTemplate }) {
  const qc = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: () => mappingsApi.delete(mapping.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mappings"] });
      toast({ title: "Mapping Template Deleted" });
    },
    onError: (err: Error) => {
      toast({ title: "Delete failed", description: err.message, variant: "destructive" });
    },
  });

  const runMutation = useMutation({
    mutationFn: () => runsApi.trigger(mapping.id, "ui"),
    onSuccess: () => {
      toast({ title: "Sync run triggered", description: `Run started for "${mapping.name}"` });
    },
    onError: (err: Error) => {
      toast({ title: "Failed to trigger run", description: err.message, variant: "destructive" });
    },
  });

  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <FileCode className="h-4 w-4 text-primary" />
              <h3 className="font-medium">{mapping.name}</h3>
            </div>
            {mapping.description && (
              <p className="mt-1 text-sm text-muted-foreground">{mapping.description}</p>
            )}
            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              {mapping.current_version && (
                <span>
                  {(() => { const n = mapping.current_version.field_mappings?.mappings?.length ?? 0; return `${n} ${n === 1 ? "field" : "fields"} mapped`; })()}
                </span>
              )}
              <span>Updated {formatRelativeTime(mapping.updated_at)}</span>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <Button variant="ghost" size="sm" asChild>
              <Link href={`/mappings/${mapping.id}`}>
                <Pencil className="h-4 w-4" />
                <span className="ml-1 hidden sm:inline">Edit</span>
              </Link>
            </Button>
            <Button
              size="sm"
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending || !mapping.is_active}
              className="bg-green-600 hover:bg-green-700 text-white"
            >
              {runMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              <span className="ml-1 hidden sm:inline">Run</span>
            </Button>
            <Button
              size="sm"
              className="bg-red-600 hover:bg-red-700 text-white"
              onClick={() => {
                if (confirm(`Delete mapping "${mapping.name}"?`)) {
                  deleteMutation.mutate();
                }
              }}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="h-4 w-4" />
              <span className="ml-1 hidden sm:inline">Delete</span>
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function CreateMappingDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [sourceConnId, setSourceConnId] = useState<number | undefined>(undefined);
  const [targetConnId, setTargetConnId] = useState<number | undefined>(undefined);
  const [kontractsEndpoint, setKontractsEndpoint] = useState("");
  const [kontractsMethod, setKontractsMethod] = useState("POST");
  const [sourceModule, setSourceModule] = useState("");
  const [sourceObject, setSourceObject] = useState("");
  const [fetchAssociatedObjects, setFetchAssociatedObjects] = useState(false);
  const [assocModule, setAssocModule] = useState("");
  const [assocObject, setAssocObject] = useState("");
  const [assocString, setAssocString] = useState("");
  const [createdId, setCreatedId] = useState<number | null>(null);

  const { data: connections } = useQuery({
    queryKey: ["connections"],
    queryFn: () => connectionsApi.list(),
    enabled: open,
  });
  const sourceConns = connections?.filter((c) => c.connection_type !== "kontracts") ?? [];
  const kontractsConns = connections?.filter((c) => c.connection_type === "kontracts") ?? [];

  const { data: modules = [] } = useQuery({
    queryKey: ["source-modules", sourceConnId],
    queryFn: () => sourceApi.getObjects(sourceConnId),
    enabled: open,
  });

  const { data: businessObjects = [], isLoading: boLoading } = useQuery({
    queryKey: ["source-business-objects", sourceModule, sourceConnId],
    queryFn: () => sourceApi.getBusinessObjects(sourceModule, sourceConnId),
    enabled: !!sourceModule,
  });

  const { data: endpoints = [] } = useQuery({
    queryKey: ["kontracts-endpoints", targetConnId],
    queryFn: () => kontractsApi.getEndpoints(targetConnId),
    enabled: open,
  });

  const sourceObjectId = businessObjects.find((b) => b.name === sourceObject)?.id;

  const { data: associatedObjects = [], isLoading: assocLoading } = useQuery({
    queryKey: ["source-associated-objects", sourceObjectId, sourceConnId],
    queryFn: () => sourceApi.getAssociatedObjects(sourceObjectId!, sourceConnId),
    enabled: fetchAssociatedObjects && !!sourceObjectId,
  });
  const assocModuleOptions = [...new Set(associatedObjects.map((a) => a.module_name))];
  const assocObjectOptions = [...new Set(
    associatedObjects.filter((a) => a.module_name === assocModule).map((a) => a.object_type_name)
  )];
  const assocStringOptions = associatedObjects
    .filter((a) => a.module_name === assocModule && a.object_type_name === assocObject)
    .map((a) => a.association_name);

  const createMutation = useMutation({
    mutationFn: () =>
      mappingsApi.create({
        name,
        description: description || undefined,
        field_mappings: [],
        source_connection_id: sourceConnId ?? null,
        target_connection_id: targetConnId ?? null,
        kontracts_endpoint: kontractsEndpoint || null,
        kontracts_method: kontractsMethod,
        source_module: sourceModule || null,
        source_object: sourceObject || null,
        fetch_associated: fetchAssociatedObjects,
        assoc_module: assocModule || null,
        assoc_object: assocObject || null,
        assoc_string: assocString || null,
      }),
    onSuccess: (mapping) => {
      qc.invalidateQueries({ queryKey: ["mappings"] });
      toast({ title: "Mapping created", description: `"${mapping.name}" saved successfully` });
      setCreatedId(mapping.id);
    },
    onError: (err: Error) => {
      toast({ title: "Create failed", description: err.message, variant: "destructive" });
    },
  });

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent className="max-w-6xl w-[90vw] h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Create Mapping Template</DialogTitle>
        </DialogHeader>
        <div className="max-h-[70vh] overflow-y-auto space-y-4 pl-4 pr-1 pb-3">
          {/* Name & Description */}
          <div className="space-y-2">
            <Label className="text-xs">Name</Label>
            <Input
              className="h-8 text-xs"
              placeholder="Name your Mapping Template..."
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label className="text-xs">Description (optional)</Label>
            <Input
              className="h-8 text-xs"
              placeholder="Brief description of what this mapping does"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          {/* Connections + Endpoint */}
          <div className="grid grid-cols-3 gap-4">
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
          </div>

          {/* TRIRIGA Module + Business Object */}
          <div className="grid grid-cols-2 gap-4 border-l-4 border-l-blue-400 pl-3 rounded-sm">
            <div className="space-y-1">
              <Label className="text-xs">TRIRIGA Module</Label>
              <SearchableSelect
                options={modules.map((m) => ({ value: m.name, label: m.label ?? m.name }))}
                value={sourceModule}
                onValueChange={(v) => { setSourceModule(v); setSourceObject(""); }}
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
                onValueChange={setSourceObject}
                disabled={!sourceModule || boLoading || fetchAssociatedObjects}
                placeholder={!sourceModule ? "Select TRIRIGA Module first..." : boLoading ? "Loading..." : "Select TRIRIGA Business Object..."}
                searchPlaceholder="Search business objects..."
                widthClass="w-[300px]"
              />
            </div>
          </div>

          {/* Fetch Associated Objects */}
          <div className={cn("flex items-center gap-2 border-l-4 pl-3 rounded-sm transition-colors", fetchAssociatedObjects ? "border-l-purple-400" : "border-l-transparent")}>
            <label className="flex items-center gap-1.5 text-xs text-muted-foreground cursor-pointer">
              <input
                type="checkbox"
                className="h-3.5 w-3.5 accent-primary"
                checked={fetchAssociatedObjects}
                onChange={(e) => {
                  setFetchAssociatedObjects(e.target.checked);
                  if (!e.target.checked) { setAssocModule(""); setAssocObject(""); setAssocString(""); }
                }}
              />
              Fetch Associated Objects?
            </label>
          </div>

          {/* Associated Object selectors */}
          {fetchAssociatedObjects && (
            <div className="grid grid-cols-3 gap-4 border-l-4 border-l-purple-400 pl-3 rounded-sm">
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

        <DialogFooter>
          {createdId ? (
            <>
              <Button asChild>
                <Link href={`/mappings/${createdId}`}>Add Field Mappings</Link>
              </Button>
              <Button variant="outline" onClick={onClose}>
                Save & Close
              </Button>
            </>
          ) : (
            <>
              <Button
                onClick={() => createMutation.mutate()}
                disabled={!name.trim() || createMutation.isPending}
              >
                {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Create
              </Button>
              <Button variant="outline" onClick={onClose}>
                Cancel
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default function MappingsPage() {
  const [showCreate, setShowCreate] = useState(false);

  const { data: mappings, isLoading } = useQuery({
    queryKey: ["mappings"],
    queryFn: () => mappingsApi.list(),
  });

  return (
    <MainLayout title="Mapping Templates">
      <div className="flex-1 overflow-y-auto space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">
              {mappings?.length ?? 0} mapping templates configured
            </p>
          </div>
          <Button size="sm" onClick={() => setShowCreate(true)}>
            Create Mapping Template
          </Button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : !mappings?.length ? (
          <div className="rounded-lg border-2 border-dashed py-16 text-center">
            <FileCode className="mx-auto h-12 w-12 text-muted-foreground/40" />
            <h3 className="mt-4 text-lg font-medium">No mappings yet</h3>
            <p className="mt-2 text-sm text-muted-foreground">
              Create your first mapping template to start syncing data from TRIRIGA to Kontracts.
            </p>
            <Button className="mt-4" onClick={() => setShowCreate(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create Mapping
            </Button>
          </div>
        ) : (
          <div className="space-y-3">
            {mappings.map((m) => (
              <MappingCard key={m.id} mapping={m} />
            ))}
          </div>
        )}
      </div>

      <CreateMappingDialog open={showCreate} onClose={() => setShowCreate(false)} />
    </MainLayout>
  );
}
