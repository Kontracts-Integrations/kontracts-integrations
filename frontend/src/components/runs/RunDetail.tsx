"use client";

import { useQuery } from "@tanstack/react-query";
import { runsApi } from "@/lib/api";
import { RecordResults } from "./RecordResults";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn, formatDateTime, formatDuration, getStatusColor, getLogLevelColor } from "@/lib/utils";
import { Loader2 } from "lucide-react";

interface Props {
  runId: number;
}

export function RunDetail({ runId }: Props) {
  const { data: run, isLoading } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => runsApi.get(runId),
    refetchInterval: (data) =>
      data?.status === "pending" || data?.status === "running" ? 2000 : false,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!run) return <p>Run not found.</p>;

  const progress =
    run.total_records && run.total_records > 0
      ? Math.round(
          ((run.success_count + run.failed_count + run.skipped_count) / run.total_records) * 100
        )
      : 0;

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Status</p>
            <span
              className={cn(
                "mt-1 inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold",
                getStatusColor(run.status)
              )}
            >
              {run.status}
            </span>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Total Records</p>
            <p className="mt-1 text-2xl font-bold">{run.total_records ?? "—"}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Results</p>
            <div className="mt-1 flex gap-2 text-sm">
              <span className="text-green-600">{run.success_count} ok</span>
              <span className="text-red-500">{run.failed_count} failed</span>
              <span className="text-muted-foreground">{run.skipped_count} skipped</span>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <p className="text-xs text-muted-foreground">Duration</p>
            <p className="mt-1 text-sm font-medium">
              {formatDuration(run.started_at, run.completed_at)}
            </p>
            <p className="text-xs text-muted-foreground">{formatDateTime(run.created_at)}</p>
          </CardContent>
        </Card>
      </div>

      {run.error_message && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {run.error_message}
        </div>
      )}

      {/* Records & Logs */}
      <Tabs defaultValue="records">
        <TabsList>
          <TabsTrigger value="records">Records ({run.records.length})</TabsTrigger>
          <TabsTrigger value="logs">Logs ({run.logs.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="records" className="mt-4">
          <RecordResults records={run.records} />
        </TabsContent>

        <TabsContent value="logs" className="mt-4">
          <div className="overflow-auto rounded-lg border">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50 text-left">
                  <th className="p-3 text-xs font-semibold text-muted-foreground">Level</th>
                  <th className="p-3 text-xs font-semibold text-muted-foreground">Component</th>
                  <th className="p-3 text-xs font-semibold text-muted-foreground">Message</th>
                  <th className="p-3 text-xs font-semibold text-muted-foreground">Time</th>
                </tr>
              </thead>
              <tbody>
                {run.logs.map((log) => (
                  <tr key={log.id} className="border-b">
                    <td className="p-3">
                      <span
                        className={cn(
                          "inline-flex rounded px-1.5 py-0.5 text-xs font-medium",
                          getLogLevelColor(log.level)
                        )}
                      >
                        {log.level}
                      </span>
                    </td>
                    <td className="p-3 text-xs font-mono text-muted-foreground">
                      {log.component ?? "—"}
                    </td>
                    <td className="p-3 text-sm">{log.message}</td>
                    <td className="p-3 text-xs text-muted-foreground">
                      {formatDateTime(log.created_at)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
