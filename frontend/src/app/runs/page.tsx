"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { runsApi, mappingsApi } from "@/lib/api";
import { MainLayout } from "@/components/layout/MainLayout";
import { RunsList } from "@/components/runs/RunsList";
import { RunDetail } from "@/components/runs/RunDetail";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "@/components/ui/toaster";
import { Play, Loader2, RefreshCw } from "lucide-react";

export default function RunsPage() {
  const qc = useQueryClient();
  const [statusFilter, setStatusFilter] = useState("all");
  const [mappingFilter, setMappingFilter] = useState("all");
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);

  const { data: runs, isLoading, refetch } = useQuery({
    queryKey: ["runs", statusFilter, mappingFilter],
    queryFn: () =>
      runsApi.list({
        status: statusFilter !== "all" ? statusFilter : undefined,
        mapping_id: mappingFilter !== "all" ? parseInt(mappingFilter) : undefined,
        limit: 100,
      }),
    refetchInterval: 10000,
  });

  const { data: mappings } = useQuery({
    queryKey: ["mappings"],
    queryFn: () => mappingsApi.list(),
  });

  const triggerMutation = useMutation({
    mutationFn: (mappingId: number) => runsApi.trigger(mappingId, "ui"),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["runs"] });
      toast({ title: "Sync run started" });
    },
    onError: (err: Error) => {
      toast({ title: "Failed to start run", description: err.message, variant: "destructive" });
    },
  });

  return (
    <MainLayout title="Sync Runs">
      <div className="space-y-4">
        {/* Controls */}
        <div className="flex flex-wrap items-center gap-3">
          <Select value={statusFilter} onValueChange={setStatusFilter}>
            <SelectTrigger className="w-36">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="running">Running</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>

          <Select value={mappingFilter} onValueChange={setMappingFilter}>
            <SelectTrigger className="w-48">
              <SelectValue placeholder="All mappings" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All mappings</SelectItem>
              {mappings?.map((m) => (
                <SelectItem key={m.id} value={String(m.id)}>
                  {m.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Button variant="ghost" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-1 h-4 w-4" />
            Refresh
          </Button>

          <div className="flex-1" />

          {mappings?.filter((m) => m.is_active).length ? (
            <Select onValueChange={(v) => triggerMutation.mutate(parseInt(v))}>
              <SelectTrigger className="w-52">
                <SelectValue placeholder="Trigger run..." />
              </SelectTrigger>
              <SelectContent>
                {mappings
                  .filter((m) => m.is_active)
                  .map((m) => (
                    <SelectItem key={m.id} value={String(m.id)}>
                      <Play className="mr-1 inline h-3 w-3" />
                      {m.name}
                    </SelectItem>
                  ))}
              </SelectContent>
            </Select>
          ) : null}
        </div>

        {/* Stats bar */}
        {runs && (
          <div className="flex gap-4 text-sm text-muted-foreground">
            <span>{runs.length} runs</span>
            <span className="text-green-600">
              {runs.filter((r) => r.status === "completed").length} completed
            </span>
            <span className="text-red-500">
              {runs.filter((r) => r.status === "failed").length} failed
            </span>
            <span className="text-blue-500">
              {runs.filter((r) => r.status === "running").length} running
            </span>
          </div>
        )}

        {/* Runs table */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <RunsList runs={runs ?? []} />
        )}
      </div>

      {/* Run detail dialog */}
      <Dialog open={selectedRunId !== null} onOpenChange={(o) => !o && setSelectedRunId(null)}>
        <DialogContent className="max-w-4xl">
          <DialogHeader>
            <DialogTitle>Run #{selectedRunId} Details</DialogTitle>
          </DialogHeader>
          {selectedRunId && <RunDetail runId={selectedRunId} />}
        </DialogContent>
      </Dialog>
    </MainLayout>
  );
}
