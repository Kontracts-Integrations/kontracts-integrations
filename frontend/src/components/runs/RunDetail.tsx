"use client";

import { useQuery } from "@tanstack/react-query";
import { runsApi } from "@/lib/api";
import { toast } from "@/components/ui/toaster";
import { RecordResults } from "./RecordResults";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { cn, formatDateTime, formatDuration, getStatusColor } from "@/lib/utils";
import { AlertTriangle, Lightbulb, Hourglass, FileSpreadsheet, FileCode } from "lucide-react";
import type { GroupedRecord } from "@/types";

interface Props {
  runId: number;
  mappingName?: string;
}

interface GroupedError {
  category: string;
  detail: string;
  count: number;
  examples: string[];
  recommendation: string;
  raw_messages: string[];
}

interface GroupedSkip {
  category: string;
  count: number;
}

function getFailureSummary(groupedRecords: GroupedRecord[]): GroupedError[] {
  const failed = (groupedRecords || []).filter((r) => r.status === "failed");
  const groups: Record<string, GroupedError> = {};

  failed.forEach((rec) => {
    const rawMsg = rec.error_message || "Unknown error";
    let category = "General Push Error";
    let detail = rawMsg;
    let recommendation = "Review the logs or error details for this record.";

    if (rawMsg.includes("payment_type_id") && rawMsg.includes("does not exist")) {
      category = "Stale Payment Type ID";
      const match = rawMsg.match(/payment_type_id '([^']+)'/);
      const staleId = match ? match[1] : "";
      detail = staleId
        ? `Payment Type ID '${staleId}' is invalid or does not exist on the target Kontracts server.`
        : "The mapped Payment Type ID does not exist on the target Kontracts server.";
      recommendation = "Update the lookup table transform for 'payment_type_id' in your Mapping Template. Replace this stale UUID with one of the valid UUIDs retrieved from the Kontracts connection dropdown options.";
    } else if (rawMsg.includes("Bulk request chunk push failed") || rawMsg.includes("422 Unprocessable Content")) {
      category = "Bulk Batch Rejection (422)";
      detail = "The target API validation rejected this entire chunk of 1,000 records because one or more records in this batch had invalid data (such as stale payment type IDs or invalid formats).";
      recommendation = "Identify the records in this chunk that failed with specific server errors (e.g. stale payment_type_id). Fix those mapping rules or set 'partial=true' on the bulk endpoint parameters to allow successful records to import.";
    } else if (rawMsg.includes("lease_id") && (rawMsg.includes("missing or null") || rawMsg.includes("Required field"))) {
      category = "Missing Lease ID";
      detail = "Required target field 'lease_id' is null. The lease lookup transform did not find a matching lease mapping.";
      recommendation = "Ensure that the source TRIRIGA contract or record is properly associated with a lease, and that the lease has already been successfully synced to Kontracts first.";
    } else if (rawMsg.includes("due_date") && (rawMsg.includes("missing or null") || rawMsg.includes("Required field"))) {
      category = "Missing Due Date";
      detail = "Required target field 'due_date' (or 'payment_date') is missing or null.";
      recommendation = "Ensure the source TRIRIGA record has a valid end/due date set in the 'triEndDA' field.";
    } else if (rawMsg.includes("Amount must be greater than 0")) {
      category = "Invalid Amount";
      const match = rawMsg.match(/value': '([^']+)'/);
      const valStr = match ? match[1] : "";
      detail = valStr
        ? `The expected amount is '${valStr}', which is not greater than 0.`
        : "The expected amount is negative or zero, which is not allowed.";
      recommendation = "Check the expected amount field in TRIRIGA; only positive payment amounts can be synced to Kontracts.";
    } else if (rawMsg.startsWith("[{") && rawMsg.endsWith("}]")) {
      category = "Local Validation Error";
      detail = "One or more mapped fields failed schema validation locally before push.";
      recommendation = "Check the source fields in TRIRIGA to ensure they match target schema formats.";
    }

    if (!groups[category]) {
      groups[category] = {
        category,
        detail,
        count: 0,
        examples: [],
        recommendation,
        raw_messages: []
      };
    }

    groups[category].count += rec.count;
    if (rec.error_message && !groups[category].raw_messages.includes(rec.error_message)) {
      groups[category].raw_messages.push(rec.error_message);
    }

    if (rec.examples) {
      for (const ex of rec.examples) {
        if (ex && !groups[category].examples.includes(ex)) {
          groups[category].examples.push(ex);
          if (groups[category].examples.length >= 10) {
            break;
          }
        }
      }
    }
  });

  return Object.values(groups).sort((a, b) => b.count - a.count);
}

function getSkippedSummary(groupedRecords: GroupedRecord[]): GroupedSkip[] {
  const skipped = (groupedRecords || []).filter((r) => r.status === "skipped");
  const groups: Record<string, number> = {};

  skipped.forEach((rec) => {
    const rawMsg = rec.error_message || "Skipped by default mapping rules";
    let category = rawMsg;

    if (rawMsg.includes("already exists") || rawMsg.includes("duplicate")) {
      category = "Duplicate Prevention (Already Synced)";
    } else if (rawMsg.includes("status is not active") || rawMsg.includes("contract status")) {
      category = "Inactive Contract State";
    }

    groups[category] = (groups[category] || 0) + rec.count;
  });

  return Object.entries(groups)
    .map(([category, count]) => ({ category, count }))
    .sort((a, b) => b.count - a.count);
}

function formatPercent(count: number, total: number): string {
  if (total <= 0 || count <= 0) return "(0%)";
  const pct = (count / total) * 100;
  if (pct < 1) return "(<1%)";
  return `(${Math.round(pct)}%)`;
}

export function RunDetail({ runId, mappingName = "Unknown Template" }: Props) {
  const { data: run, isLoading } = useQuery({
    queryKey: ["run", runId],
    queryFn: () => runsApi.get(runId),
    refetchInterval: (query) =>
      query.state.data?.status === "pending" || query.state.data?.status === "running" ? 2000 : false,
  });

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-12 gap-3">
        <Hourglass className="h-8 w-8 animate-[spin_2s_ease-in-out_infinite] text-muted-foreground" />
        <span className="text-sm font-medium text-muted-foreground animate-pulse">Loading...</span>
      </div>
    );
  }

  if (!run) return <p>Run not found.</p>;

  const handleExportToExcel = async (status: string, errorMessages: string[], category: string) => {
    try {
      const blob = await runsApi.exportRecords(runId, status, category, errorMessages);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `run ${runId} - ${category || "export"}.csv`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast({
        title: "Export failed",
        description: (e as Error).message,
        variant: "destructive",
      });
    }
  };

  const groupedErrors = getFailureSummary(run.grouped_records || []);
  const skippedSummary = getSkippedSummary(run.grouped_records || []);
  const defaultTab = "summary";
  const recordsTotal = ((run.grouped_records || []).filter(r => r.status !== "success").reduce((acc, curr) => acc + curr.count, 0) + run.success_count);
  const total = run.total_records ?? 0;

  return (
    <div className="space-y-4">
      {/* Summary Card */}
      <Card className="w-full">
        <CardContent className="p-4 flex items-center justify-between gap-6 h-full">
          {/* Leftmost Column: Mapping Template Name */}
          <div className="flex items-center gap-2 min-w-[120px] max-w-[300px]">
            <FileCode className="h-4 w-4 text-muted-foreground shrink-0" />
            <span className="text-sm font-bold text-foreground leading-tight break-words">
              {mappingName}
            </span>
          </div>

          {/* Right Group: Total + Divider + Breakdowns */}
          <div className="flex items-center gap-6 md:gap-8">
            {/* Middle Column: Total Records */}
            <div className="flex flex-col items-center justify-center min-w-[70px]">
              <span className="text-[10px] uppercase font-semibold text-muted-foreground leading-none">Total</span>
              <span className="text-xl font-bold text-foreground mt-2 leading-none">
                {total.toLocaleString()}
              </span>
              {run.status === "running" && total > 0 && (
                <span className="text-[10px] text-primary font-bold mt-1.5 animate-pulse">
                  {(() => {
                    const processed = (run.success_count ?? 0) + (run.failed_count ?? 0) + (run.skipped_count ?? 0);
                    return Math.min(100, Math.round((processed / total) * 100));
                  })()}%
                </span>
              )}
            </div>

            {/* Divider Line */}
            <div className="h-10 w-[1px] bg-border shrink-0" />

            {/* Rightmost Separation: Category, Count, and Percentage */}
            <div className="flex flex-col justify-center text-xs gap-1 min-w-[140px]">
              <div className="h-4 flex items-center">
                <span className="h-2 w-2 rounded-full bg-green-500 shrink-0 mr-1.5" />
                <span className="text-muted-foreground mr-1">Success:</span>
                <span className="font-semibold text-green-600">{(run.success_count ?? 0).toLocaleString()}</span>
                <span className="text-[10px] text-muted-foreground font-normal ml-1.5">
                  ({total > 0 ? Math.round(((run.success_count ?? 0) / total) * 100) : 0}%)
                </span>
              </div>
              <div className="h-4 flex items-center">
                <span className="h-2 w-2 rounded-full bg-red-500 shrink-0 mr-1.5" />
                <span className="text-muted-foreground mr-1">Failed:</span>
                <span className="font-semibold text-red-500">{(run.failed_count ?? 0).toLocaleString()}</span>
                <span className="text-[10px] text-muted-foreground font-normal ml-1.5">
                  ({total > 0 ? Math.round(((run.failed_count ?? 0) / total) * 100) : 0}%)
                </span>
              </div>
              <div className="h-4 flex items-center">
                <span className="h-2 w-2 rounded-full bg-gray-400 dark:bg-gray-600 shrink-0 mr-1.5" />
                <span className="text-muted-foreground mr-1">Skipped:</span>
                <span className="font-semibold text-muted-foreground">{(run.skipped_count ?? 0).toLocaleString()}</span>
                <span className="text-[10px] text-muted-foreground font-normal ml-1.5">
                  ({total > 0 ? Math.round(((run.skipped_count ?? 0) / total) * 100) : 0}%)
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {run.error_message && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive font-mono">
          {run.error_message}
        </div>
      )}

      {/* Records & Diagnostics */}
      <Tabs defaultValue={defaultTab}>
        <TabsList>
          <TabsTrigger value="summary">Summary</TabsTrigger>
          {run.failed_count > 0 && (
            <TabsTrigger value="diagnostics">
              Diagnostics ({groupedErrors.length})
            </TabsTrigger>
          )}
        </TabsList>

        {/* Summary Tab Content */}
        <TabsContent value="summary" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Table 1: Failed Summary */}
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-red-600 flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-red-500" />
                Failed Records Summary {formatPercent(run.failed_count, run.total_records || 0)}
              </h3>
              <div className="overflow-hidden rounded-lg border bg-card">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b bg-muted/30 text-xs font-semibold text-muted-foreground">
                      <th className="p-3">Category / Reason</th>
                      <th className="p-3 text-right w-36">Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y text-sm">
                    {groupedErrors.length === 0 ? (
                      <tr>
                        <td colSpan={2} className="p-3 text-center text-muted-foreground text-xs">
                          No failed records in this run.
                        </td>
                      </tr>
                    ) : (
                      groupedErrors.map((item, idx) => (
                        <tr key={idx} className="hover:bg-muted/10">
                          <td className="p-3 font-medium text-xs">{item.category}</td>
                          <td className="p-3 text-right font-mono font-semibold">
                            {item.count.toLocaleString()}
                            <span className="text-[11px] text-muted-foreground font-normal ml-1.5">
                              {formatPercent(item.count, run.total_records || 0)}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Table 2: Skipped Summary */}
            <div className="space-y-2">
              <h3 className="text-sm font-semibold text-zinc-600 flex items-center gap-1.5">
                <span className="h-2 w-2 rounded-full bg-zinc-400" />
                Skipped Records Summary {formatPercent(run.skipped_count, run.total_records || 0)}
              </h3>
              <div className="overflow-hidden rounded-lg border bg-card">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b bg-muted/30 text-xs font-semibold text-muted-foreground">
                      <th className="p-3">Category / Reason</th>
                      <th className="p-3 text-right w-36">Count</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y text-sm">
                    {skippedSummary.length === 0 ? (
                      <tr>
                        <td colSpan={2} className="p-3 text-center text-muted-foreground text-xs">
                          No skipped records in this run.
                        </td>
                      </tr>
                    ) : (
                      skippedSummary.map((item, idx) => (
                        <tr key={idx} className="hover:bg-muted/10">
                          <td className="p-3 font-medium text-xs">{item.category}</td>
                          <td className="p-3 text-right font-mono font-semibold">
                            {item.count.toLocaleString()}
                            <span className="text-[11px] text-muted-foreground font-normal ml-1.5">
                              {formatPercent(item.count, run.total_records || 0)}
                            </span>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </TabsContent>

        {run.failed_count > 0 && (
          <TabsContent value="diagnostics" className="mt-4 space-y-4">
            {groupedErrors.map((err, i) => (
              <Card key={i} className="border-red-100 bg-red-50/20 dark:bg-red-950/5">
                <CardHeader className="flex flex-row items-start justify-between space-y-0 p-4 pb-2">
                  <div className="space-y-1">
                    <CardTitle className="text-base font-semibold text-red-600">
                      {err.category}
                    </CardTitle>
                    <p className="text-sm text-muted-foreground pr-4">{err.detail}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <div className="rounded-full bg-red-100 px-3 py-1 text-xs font-bold text-red-600 dark:bg-red-950/50">
                      {err.count.toLocaleString()} records
                    </div>
                    <button
                      onClick={() => handleExportToExcel("failed", err.raw_messages, err.category)}
                      className="p-1.5 hover:text-green-600 hover:bg-green-50 dark:hover:bg-green-950/20 rounded transition-colors focus:outline-none"
                      title="Export to Excel"
                    >
                      <FileSpreadsheet className="h-4 w-4 text-zinc-500 hover:text-green-600" />
                    </button>
                  </div>
                </CardHeader>
                <CardContent className="p-4 pt-2 space-y-3">
                  <div className="rounded-lg bg-blue-50/50 p-3 dark:bg-blue-950/10 border border-blue-100 dark:border-blue-900/50 text-sm">
                    <p className="font-semibold text-blue-800 dark:text-blue-400 flex items-center gap-1.5 mb-1">
                      <Lightbulb className="h-4 w-4 text-blue-600 shrink-0" />
                      Recommendation
                    </p>
                    <p className="text-blue-900 dark:text-blue-300 leading-relaxed">
                      {err.recommendation}
                    </p>
                  </div>

                </CardContent>
              </Card>
            ))}
          </TabsContent>
        )}


      </Tabs>
    </div>
  );
}
