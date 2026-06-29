"use client";

import { cn, getStatusColor } from "@/lib/utils";

interface Props {
  groupedRecords: {
    status: string;
    error_message: string | null;
    count: number;
    examples: string[];
  }[];
  successCount: number;
}

export function RecordResults({ groupedRecords, successCount }: Props) {
  const summaries = (groupedRecords || [])
    .filter((gr) => gr.status !== "success")
    .map((gr) => ({
      status: gr.status as "failed" | "skipped",
      reason: gr.error_message || "Unknown error/reason",
      count: gr.count,
      examples: gr.examples,
    }))
    .sort((a, b) => b.count - a.count);

  const totalCount = successCount + summaries.reduce((acc, curr) => acc + curr.count, 0);

  if (totalCount === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">No records to display.</p>
    );
  }

  return (
    <div className="space-y-4">
      {/* Success summary banner */}
      {successCount > 0 && (
        <div className="rounded-lg border border-green-100 bg-green-50/30 p-3 text-sm text-green-800 dark:border-green-900/30 dark:bg-green-950/10 dark:text-green-400 flex items-center justify-between">
          <span className="font-medium">
            ✅ {successCount.toLocaleString()} records were successfully synced to Kontracts.
          </span>
        </div>
      )}

      {/* Grouped summary table */}
      <div className="overflow-auto rounded-lg border">
        <table className="w-full">
          <thead>
            <tr className="border-b bg-muted/50 text-left">
              <th className="p-3 text-xs font-semibold text-muted-foreground w-28">Status</th>
              <th className="p-3 text-xs font-semibold text-muted-foreground">Error / Reason</th>
              <th className="p-3 text-xs font-semibold text-muted-foreground w-32 text-right">Count</th>
              <th className="p-3 text-xs font-semibold text-muted-foreground">Example TRIRIGA Record IDs</th>
            </tr>
          </thead>
          <tbody>
            {summaries.length === 0 ? (
              <tr>
                <td colSpan={4} className="p-4 text-center text-sm text-muted-foreground">
                  No failed or skipped records in this run.
                </td>
              </tr>
            ) : (
              summaries.map((summary, idx) => (
                <tr key={idx} className="border-b hover:bg-muted/30">
                  <td className="p-3 align-top">
                    <span
                      className={cn(
                        "inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold uppercase",
                        getStatusColor(summary.status)
                      )}
                    >
                      {summary.status}
                    </span>
                  </td>
                  <td className="p-3 text-sm text-foreground align-top break-words max-w-lg font-mono text-xs">
                    {summary.reason}
                  </td>
                  <td className="p-3 text-sm font-semibold text-right align-top">
                    {summary.count.toLocaleString()}
                  </td>
                  <td className="p-3 align-top">
                    <div className="flex flex-wrap gap-1">
                      {summary.examples.map((id) => (
                        <span
                          key={id}
                          className="inline-flex items-center rounded border bg-muted px-1.5 py-0.5 font-mono text-xs text-muted-foreground"
                        >
                          {id}
                        </span>
                      ))}
                      {summary.count > summary.examples.length && (
                        <span className="text-xs text-muted-foreground self-center ml-1">
                          + {(summary.count - summary.examples.length).toLocaleString()} more
                        </span>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
