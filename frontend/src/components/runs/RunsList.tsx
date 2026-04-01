import { useState, useEffect } from "react";
import { Loader2, Hourglass, Square } from "lucide-react";
import { parseISO } from "date-fns";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn, formatDateTime, formatDuration, getStatusColor } from "@/lib/utils";
import type { SyncRun, MappingTemplate } from "@/types";

function LiveDuration({ startedAt }: { startedAt: string }) {
  const [elapsed, setElapsed] = useState("");

  useEffect(() => {
    const tick = () => {
      const ms = Date.now() - parseISO(startedAt).getTime();
      if (ms < 60000) setElapsed(`${(ms / 1000).toFixed(0)}s`);
      else setElapsed(`${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`);
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [startedAt]);

  return <span className="text-white font-mono">{elapsed}</span>;
}

interface Props {
  runs: SyncRun[];
  mappings: MappingTemplate[];
  statusFilter: string;
  mappingFilter: string;
  onStatusFilterChange: (v: string) => void;
  onMappingFilterChange: (v: string) => void;
  onSelect?: (runId: number) => void;
  onCancel?: (runId: number) => void;
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-semibold",
        getStatusColor(status)
      )}
    >
      {status === "running" ? (
        <span className="inline-flex items-center gap-0">
          running
          <span className="inline-flex">
            <span className="animate-[subtle-bounce_1.4s_ease-in-out_infinite_0ms]">.</span>
            <span className="animate-[subtle-bounce_1.4s_ease-in-out_infinite_280ms]">.</span>
            <span className="animate-[subtle-bounce_1.4s_ease-in-out_infinite_560ms]">.</span>
          </span>
        </span>
      ) : status === "pending" ? (
        <span className="inline-flex items-center gap-1" style={{ color: "#ca8a04" }}>
          pending
          <Hourglass className="h-3 w-3 animate-[spin_2s_ease-in-out_infinite]" />
        </span>
      ) : status}
    </span>
  );
}

function RunRow({ run, mappingName, onSelect, onCancel }: { run: SyncRun; mappingName: string; onSelect?: () => void; onCancel?: () => void }) {
  return (
    <tr
      className={cn("border-b transition-colors cursor-pointer", run.status === "running" ? "bg-gray-100 dark:bg-gray-800/50 hover:bg-gray-200 dark:hover:bg-gray-800/70" : "hover:bg-muted/50")}
      onClick={onSelect}
    >
      <td className="p-3 text-sm font-medium">#{run.id}</td>
      <td className="p-3">
        <div className="flex items-center gap-1.5">
          <StatusBadge status={run.status} />
          {(run.status === "running" || run.status === "pending") && onCancel && (
            <button
              onClick={(e) => { e.stopPropagation(); onCancel(); }}
              className="text-muted-foreground hover:text-red-500 transition-colors"
              title="Stop run"
            >
              <Square className="h-3.5 w-3.5 fill-current" />
            </button>
          )}
        </div>
      </td>
      <td className="p-3 text-sm text-muted-foreground">
        {mappingName}
      </td>
      <td className="py-3 pl-0 pr-3 text-sm">
        {run.status === "running" && run.total_records != null && run.total_records > 0 ? (() => {
          const processed = (run.success_count ?? 0) + (run.failed_count ?? 0) + (run.skipped_count ?? 0);
          const pct = Math.min(100, Math.round((processed / run.total_records) * 100));
          return (
            <div className="flex flex-col gap-1 min-w-[140px]">
              <div className="flex items-center justify-between text-xs">
                <span className="font-medium">{pct}%</span>
                <div className="flex gap-2">
                  <span className="text-green-600">{run.success_count ?? 0} ✓</span>
                  <span className="text-red-500">{run.failed_count ?? 0} ✗</span>
                  <span className="text-muted-foreground">{run.skipped_count ?? 0} skip</span>
                  <span className="text-muted-foreground">/ {run.total_records}</span>
                </div>
              </div>
              <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-500"
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })() : run.total_records != null ? (
          <div className="flex flex-col items-start gap-0.5">
            <span className="text-xs text-muted-foreground">{run.total_records} total</span>
            <div className="flex gap-2 text-xs">
              <span className="text-green-600">{run.success_count ?? 0} success</span>
              <span className="text-red-500">{run.failed_count ?? 0} failed</span>
              <span className="text-muted-foreground">{run.skipped_count ?? 0} skipped</span>
            </div>
          </div>
        ) : "—"}
      </td>
      <td className="p-3 text-sm text-muted-foreground">
        {formatDateTime(run.created_at)}
      </td>
      <td className="p-3 text-sm text-muted-foreground">
        {run.status === "running" && run.started_at
          ? <LiveDuration startedAt={run.started_at} />
          : formatDuration(run.started_at, run.completed_at)}
      </td>
      <td className="p-3 text-sm text-muted-foreground">
        {run.triggered_by === "ui" ? "admin" : (run.triggered_by ?? "—")}
      </td>
    </tr>
  );
}

function ColumnFilter({
  value,
  onChange,
  options,
  allLabel,
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  allLabel: string;
}) {
  const isFiltered = value !== "all";
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="h-6 w-auto gap-1 border-0 bg-transparent p-0 text-xs font-semibold text-muted-foreground hover:text-foreground focus:ring-0">
        <span className={cn("flex items-center gap-1", isFiltered && "text-foreground")}>
          {allLabel}
          {isFiltered && <span className="h-1.5 w-1.5 rounded-full bg-primary" />}
        </span>
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">- All -</SelectItem>
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value}>
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

export function RunsList({ runs, mappings, statusFilter, mappingFilter, onStatusFilterChange, onMappingFilterChange, onSelect, onCancel }: Props) {
  const mappingMap = Object.fromEntries(mappings.map((m) => [m.id, m.name]));

  const filtered = runs.filter((r) => {
    if (statusFilter !== "all" && r.status !== statusFilter) return false;
    if (mappingFilter !== "all" && String(r.mapping_template_id) !== mappingFilter) return false;
    return true;
  });

  if (!runs.length) {
    return (
      <div className="py-12 text-center text-sm text-muted-foreground">
        No sync runs found.
      </div>
    );
  }

  const statusOptions = ["pending", "running", "completed", "failed", "stopped"].map((s) => ({
    value: s,
    label: s.charAt(0).toUpperCase() + s.slice(1),
  }));

  const mappingOptions = mappings.map((m) => ({ value: String(m.id), label: m.name }));

  return (
    <div className="overflow-auto rounded-lg border">
      <table className="w-full">
        <thead>
          <tr className="border-b bg-muted/50 text-left">
            <th className="p-3 text-xs font-semibold text-muted-foreground">Run</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">
              <ColumnFilter
                value={statusFilter}
                onChange={onStatusFilterChange}
                options={statusOptions}
                allLabel="Status"
              />
            </th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">
              <ColumnFilter
                value={mappingFilter}
                onChange={onMappingFilterChange}
                options={mappingOptions}
                allLabel="Mapping Template"
              />
            </th>
            <th className="py-3 pl-0 pr-3 text-xs font-semibold text-muted-foreground text-center">Record Count</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">Start Time (IST)</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">Duration</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">Triggered By</th>
          </tr>
        </thead>
        <tbody>
          {filtered.map((run) => (
            <RunRow
              key={run.id}
              run={run}
              mappingName={run.mapping_template_id ? (mappingMap[run.mapping_template_id] ?? `#${run.mapping_template_id}`) : "—"}
              onSelect={() => onSelect?.(run.id)}
              onCancel={() => onCancel?.(run.id)}
            />
          ))}
        </tbody>
      </table>
      {filtered.length === 0 && (
        <div className="py-8 text-center text-sm text-muted-foreground">
          No runs match the selected filters.
        </div>
      )}
    </div>
  );
}
