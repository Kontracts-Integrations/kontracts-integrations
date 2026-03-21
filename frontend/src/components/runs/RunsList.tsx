"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { runsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn, formatDateTime, formatDuration, getStatusColor } from "@/lib/utils";
import { RotateCcw, Eye, Loader2 } from "lucide-react";
import { toast } from "@/components/ui/toaster";
import type { SyncRun } from "@/types";

interface Props {
  runs: SyncRun[];
  showMappingId?: boolean;
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
        getStatusColor(status)
      )}
    >
      {status}
    </span>
  );
}

function RunRow({ run }: { run: SyncRun }) {
  const qc = useQueryClient();

  const retryMutation = useMutation({
    mutationFn: () => runsApi.retry(run.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["runs"] });
      toast({ title: "Retry triggered", description: `New run started based on run #${run.id}` });
    },
    onError: (err: Error) => {
      toast({ title: "Retry failed", description: err.message, variant: "destructive" });
    },
  });

  return (
    <tr className="border-b transition-colors hover:bg-muted/50">
      <td className="p-3 text-sm font-medium">#{run.id}</td>
      <td className="p-3">
        <StatusBadge status={run.status} />
      </td>
      <td className="p-3 text-sm text-muted-foreground">
        {run.mapping_template_id ? `Mapping #${run.mapping_template_id}` : "—"}
      </td>
      <td className="p-3 text-sm">
        {run.total_records != null ? (
          <div className="flex items-center gap-2">
            <span>{run.total_records}</span>
            {run.success_count > 0 && (
              <span className="text-xs text-green-600">{run.success_count} ok</span>
            )}
            {run.failed_count > 0 && (
              <span className="text-xs text-red-500">{run.failed_count} failed</span>
            )}
            {run.skipped_count > 0 && (
              <span className="text-xs text-muted-foreground">{run.skipped_count} skipped</span>
            )}
          </div>
        ) : (
          "—"
        )}
      </td>
      <td className="p-3 text-sm text-muted-foreground">
        {formatDateTime(run.created_at)}
      </td>
      <td className="p-3 text-sm text-muted-foreground">
        {formatDuration(run.started_at, run.completed_at)}
      </td>
      <td className="p-3 text-sm text-muted-foreground">
        {run.triggered_by ?? "—"}
      </td>
      <td className="p-3">
        <div className="flex items-center gap-1">
          {(run.status === "failed" || run.status === "completed") && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => retryMutation.mutate()}
              disabled={retryMutation.isPending}
              title="Retry this run"
            >
              {retryMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RotateCcw className="h-4 w-4" />
              )}
            </Button>
          )}
        </div>
      </td>
    </tr>
  );
}

export function RunsList({ runs }: Props) {
  if (!runs.length) {
    return (
      <div className="py-12 text-center text-sm text-muted-foreground">
        No sync runs found.
      </div>
    );
  }

  return (
    <div className="overflow-auto rounded-lg border">
      <table className="w-full">
        <thead>
          <tr className="border-b bg-muted/50 text-left">
            <th className="p-3 text-xs font-semibold text-muted-foreground">Run</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">Status</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">Mapping</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">Records</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">Started</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">Duration</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">Triggered By</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">Actions</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <RunRow key={run.id} run={run} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
