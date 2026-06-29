"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { runsApi, mappingsApi } from "@/lib/api";
import type { SyncRun } from "@/types";
import { MainLayout } from "@/components/layout/MainLayout";
import { RunsList } from "@/components/runs/RunsList";
import { RunDetail } from "@/components/runs/RunDetail";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "@/components/ui/toaster";
import { cn, getStatusColor, formatDuration } from "@/lib/utils";
import { Loader2, RefreshCw, X, Clock } from "lucide-react";

export default function RunsPage() {
  const qc = useQueryClient();
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [mappingFilter, setMappingFilter] = useState("all");
  const [searchText, setSearchText] = useState("");
  const [runSearchText, setRunSearchText] = useState("");

  const hasFilters = statusFilter !== "all" || mappingFilter !== "all" || searchText !== "" || runSearchText !== "";

  function resetFilters() {
    setStatusFilter("all");
    setMappingFilter("all");
    setSearchText("");
    setRunSearchText("");
  }

  const cancelMutation = useMutation({
    mutationFn: (runId: number) => runsApi.cancel(runId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["runs"] }),
  });

  const { data: runs, isLoading, isRefetching } = useQuery<SyncRun[]>({
    queryKey: ["runs"],
    queryFn: () => runsApi.list({ limit: 100 }),
    refetchInterval: (query) => {
      const data = query.state.data as SyncRun[] | undefined;
      const hasRunning = data?.some((r) => r.status === "running");
      return hasRunning ? 2000 : 10000;
    },
  });

  const { data: mappings } = useQuery({
    queryKey: ["mappings"],
    queryFn: () => mappingsApi.list(),
  });

  return (
    <MainLayout title="Sync Runs">
      <div className="flex-1 overflow-y-auto space-y-4">
        {/* Controls */}
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => qc.invalidateQueries({ queryKey: ["runs"] })}
            disabled={isRefetching}
          >
            <RefreshCw className={`mr-1 h-4 w-4 ${isRefetching ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          {hasFilters && (
            <Button variant="ghost" size="sm" onClick={resetFilters}>
              <X className="mr-1 h-4 w-4" />
              Reset Filters
            </Button>
          )}
        </div>

{/* Runs table */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <RunsList
            runs={runs ?? []}
            mappings={mappings ?? []}
            statusFilter={statusFilter}
            mappingFilter={mappingFilter}
            searchText={searchText}
            runSearchText={runSearchText}
            onStatusFilterChange={setStatusFilter}
            onMappingFilterChange={setMappingFilter}
            onSearchTextChange={setSearchText}
            onRunSearchTextChange={setRunSearchText}
            onSelect={setSelectedRunId}
            onCancel={(runId) => cancelMutation.mutate(runId)}
          />
        )}
      </div>

      {/* Run detail dialog */}
      {(() => {
        const selectedRun = runs?.find((r) => r.id === selectedRunId);
        return (
          <Dialog open={selectedRunId !== null} onOpenChange={(o) => !o && setSelectedRunId(null)}>
            <DialogContent className="max-w-4xl max-h-[85vh] flex flex-col">
              <DialogHeader className="shrink-0 pb-2 border-b flex flex-row items-center justify-between pr-8">
                <DialogTitle className="flex items-center gap-2.5">
                  <span>Run #{selectedRunId}</span>
                  {selectedRun && (
                    <span
                      className={cn(
                        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
                        getStatusColor(selectedRun.status)
                      )}
                    >
                      {selectedRun.status}
                    </span>
                  )}
                </DialogTitle>
                {selectedRun && (
                  <div className="flex items-center gap-1.5 text-sm text-muted-foreground font-medium">
                    <Clock className="h-4 w-4 text-zinc-400" />
                    <span>{formatDuration(selectedRun.started_at, selectedRun.completed_at)}</span>
                  </div>
                )}
              </DialogHeader>
          <div className="overflow-y-auto flex-1 pr-1 mt-4">
            {selectedRunId && (
              <RunDetail
                runId={selectedRunId}
                mappingName={mappings?.find(m => m.id === selectedRun?.mapping_template_id)?.name || "Unknown Template"}
              />
            )}
          </div>
            </DialogContent>
          </Dialog>
        );
      })()}
    </MainLayout>
  );
}
