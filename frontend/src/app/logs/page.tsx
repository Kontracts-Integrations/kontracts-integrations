"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { logsApi } from "@/lib/api";
import { MainLayout } from "@/components/layout/MainLayout";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { cn, formatDateTime, getLogLevelColor } from "@/lib/utils";
import { Search, RefreshCw, Loader2 } from "lucide-react";
import type { LogEntry } from "@/types";

function LogRow({ log }: { log: LogEntry }) {
  const [expanded, setExpanded] = useState(false);
  const hasExtra = log.extra && Object.keys(log.extra).length > 0;

  return (
    <>
      <tr
        className={cn(
          "border-b",
          hasExtra && "cursor-pointer hover:bg-muted/50",
          log.level === "error" && "bg-red-50/30 dark:bg-red-950/20"
        )}
        onClick={() => hasExtra && setExpanded((e) => !e)}
      >
        <td className="p-3 text-xs font-mono text-muted-foreground whitespace-nowrap">
          {formatDateTime(log.created_at)}
        </td>
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
        <td className="p-3 text-sm">
          {log.message}
          {hasExtra && !expanded && (
            <span className="ml-2 text-xs text-muted-foreground">
              [{Object.keys(log.extra!).join(", ")}]
            </span>
          )}
        </td>
        <td className="p-3 text-xs text-muted-foreground">
          {log.run_id ? `#${log.run_id}` : "—"}
        </td>
      </tr>
      {expanded && hasExtra && (
        <tr className="border-b bg-muted/20">
          <td colSpan={5} className="px-8 py-2">
            <pre className="text-xs">{JSON.stringify(log.extra, null, 2)}</pre>
          </td>
        </tr>
      )}
    </>
  );
}

export default function LogsPage() {
  const [levelFilter, setLevelFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");

  const { data: logs, isLoading, refetch } = useQuery({
    queryKey: ["logs", levelFilter, search],
    queryFn: () =>
      logsApi.list({
        level: levelFilter !== "all" ? levelFilter : undefined,
        search: search || undefined,
        limit: 200,
      }),
    refetchInterval: 15000,
  });

  const { data: stats } = useQuery({
    queryKey: ["log-stats"],
    queryFn: () => logsApi.stats(),
    refetchInterval: 30000,
  });

  return (
    <MainLayout title="Logs">
      <div className="flex-1 overflow-y-auto space-y-4">
        {/* Stats bar */}
        {stats && (
          <div className="flex flex-wrap gap-4 text-sm">
            {Object.entries(stats.stats).map(([level, count]) => (
              <div key={level} className="flex items-center gap-1">
                <span
                  className={cn(
                    "inline-flex rounded px-2 py-0.5 text-xs font-medium",
                    getLogLevelColor(level)
                  )}
                >
                  {level}
                </span>
                <span className="font-medium">{count.toLocaleString()}</span>
              </div>
            ))}
          </div>
        )}

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3">
          <Select value={levelFilter} onValueChange={setLevelFilter}>
            <SelectTrigger className="w-32">
              <SelectValue placeholder="All levels" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All levels</SelectItem>
              <SelectItem value="debug">Debug</SelectItem>
              <SelectItem value="info">Info</SelectItem>
              <SelectItem value="warning">Warning</SelectItem>
              <SelectItem value="error">Error</SelectItem>
            </SelectContent>
          </Select>

          <form
            className="flex flex-1 items-center gap-2"
            onSubmit={(e) => {
              e.preventDefault();
              setSearch(searchInput);
            }}
          >
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                className="pl-9"
                placeholder="Search log messages..."
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
              />
            </div>
            <Button type="submit" variant="outline" size="sm">
              Search
            </Button>
          </form>

          <Button variant="ghost" size="sm" onClick={() => refetch()}>
            <RefreshCw className="mr-1 h-4 w-4" />
            Refresh
          </Button>
        </div>

        {/* Count */}
        {logs && (
          <p className="text-sm text-muted-foreground">
            Showing {logs.length} log entries
            {levelFilter !== "all" && ` (filtered by ${levelFilter})`}
            {search && ` matching "${search}"`}
          </p>
        )}

        {/* Log table */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : !logs?.length ? (
          <div className="py-12 text-center text-sm text-muted-foreground">
            No log entries found.
          </div>
        ) : (
          <div className="overflow-auto rounded-lg border">
            <table className="w-full">
              <thead>
                <tr className="border-b bg-muted/50 text-left">
                  <th className="p-3 text-xs font-semibold text-muted-foreground whitespace-nowrap">
                    Timestamp
                  </th>
                  <th className="p-3 text-xs font-semibold text-muted-foreground">Level</th>
                  <th className="p-3 text-xs font-semibold text-muted-foreground">Component</th>
                  <th className="p-3 text-xs font-semibold text-muted-foreground">Message</th>
                  <th className="p-3 text-xs font-semibold text-muted-foreground">Run</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <LogRow key={log.id} log={log} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </MainLayout>
  );
}
