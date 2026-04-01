"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { runsApi, mappingsApi } from "@/lib/api";
import { MainLayout } from "@/components/layout/MainLayout";
import { RunsList } from "@/components/runs/RunsList";
import { RunDetail } from "@/components/runs/RunDetail";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "@/components/ui/toaster";
import { Loader2, RefreshCw, X } from "lucide-react";

export default function RunsPage() {
  const qc = useQueryClient();
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [mappingFilter, setMappingFilter] = useState("all");

  const hasFilters = statusFilter !== "all" || mappingFilter !== "all";

  function resetFilters() {
    setStatusFilter("all");
    setMappingFilter("all");
  }

  const { data: runs, isLoading, isRefetching } = useQuery({
    queryKey: ["runs"],
    queryFn: () => runsApi.list({ limit: 100 }),
    refetchInterval: 10000,
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
            onStatusFilterChange={setStatusFilter}
            onMappingFilterChange={setMappingFilter}
            onSelect={setSelectedRunId}
          />
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
