"use client";

import { useState } from "react";
import Link from "next/link";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mappingsApi, runsApi } from "@/lib/api";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/toaster";
import { cn, formatRelativeTime, getStatusColor } from "@/lib/utils";
import { Plus, GitBranch, Play, Pencil, Trash2, Loader2, CheckCircle2, XCircle } from "lucide-react";
import type { MappingTemplate } from "@/types";

function MappingCard({ mapping }: { mapping: MappingTemplate }) {
  const qc = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: () => mappingsApi.delete(mapping.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["mappings"] });
      toast({ title: "Mapping deleted" });
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
              <GitBranch className="h-4 w-4 text-primary" />
              <h3 className="font-medium">{mapping.name}</h3>
              <span
                className={cn(
                  "rounded-full px-2 py-0.5 text-xs font-medium",
                  mapping.is_active
                    ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                    : "bg-gray-100 text-gray-600"
                )}
              >
                {mapping.is_active ? "Active" : "Inactive"}
              </span>
              {mapping.current_version && (
                <span className="text-xs text-muted-foreground">
                  v{mapping.current_version.version_number}
                </span>
              )}
            </div>

            {mapping.description && (
              <p className="mt-1 text-sm text-muted-foreground">{mapping.description}</p>
            )}

            <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
              {mapping.tririga_module && (
                <span>
                  TRIRIGA: <code className="font-mono">{mapping.tririga_module}</code>
                  {mapping.tririga_query_name && (
                    <span> / {mapping.tririga_query_name}</span>
                  )}
                </span>
              )}
              {mapping.kontracts_endpoint && (
                <span>
                  →{" "}
                  <code className="font-mono">
                    {mapping.kontracts_method} {mapping.kontracts_endpoint}
                  </code>
                </span>
              )}
              {mapping.current_version && (
                <span>
                  {mapping.current_version.field_mappings?.mappings?.length ?? 0} fields mapped
                </span>
              )}
              <span>Updated {formatRelativeTime(mapping.updated_at)}</span>
            </div>
          </div>

          <div className="flex items-center gap-2 flex-shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => runMutation.mutate()}
              disabled={runMutation.isPending || !mapping.is_active}
            >
              {runMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Play className="h-4 w-4" />
              )}
              <span className="ml-1 hidden sm:inline">Run</span>
            </Button>
            <Button variant="ghost" size="sm" asChild>
              <Link href={`/mappings/${mapping.id}`}>
                <Pencil className="h-4 w-4" />
                <span className="ml-1 hidden sm:inline">Edit</span>
              </Link>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground hover:text-destructive"
              onClick={() => {
                if (confirm(`Delete mapping "${mapping.name}"?`)) {
                  deleteMutation.mutate();
                }
              }}
              disabled={deleteMutation.isPending}
            >
              <Trash2 className="h-4 w-4" />
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

  const createMutation = useMutation({
    mutationFn: () =>
      mappingsApi.create({ name, description: description || undefined, field_mappings: [] }),
    onSuccess: (mapping) => {
      qc.invalidateQueries({ queryKey: ["mappings"] });
      toast({ title: "Mapping created", description: `"${mapping.name}" ready to configure` });
      onClose();
      window.location.href = `/mappings/${mapping.id}`;
    },
    onError: (err: Error) => {
      toast({ title: "Create failed", description: err.message, variant: "destructive" });
    },
  });

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Create Mapping Template</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label>Name</Label>
            <Input
              placeholder="TRIRIGA Leases → Kontracts"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Description (optional)</Label>
            <Input
              placeholder="Brief description of what this mapping does"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button
            onClick={() => createMutation.mutate()}
            disabled={!name.trim() || createMutation.isPending}
          >
            {createMutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Create & Configure
          </Button>
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
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm text-muted-foreground">
              {mappings?.length ?? 0} mapping templates configured
            </p>
          </div>
          <Button onClick={() => setShowCreate(true)}>
            <Plus className="mr-2 h-4 w-4" />
            New Mapping
          </Button>
        </div>

        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : !mappings?.length ? (
          <div className="rounded-lg border-2 border-dashed py-16 text-center">
            <GitBranch className="mx-auto h-12 w-12 text-muted-foreground/40" />
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
