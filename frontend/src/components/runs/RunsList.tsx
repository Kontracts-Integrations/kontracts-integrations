import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { cn, formatDateTime, formatDuration, getStatusColor } from "@/lib/utils";
import type { SyncRun, MappingTemplate } from "@/types";

interface Props {
  runs: SyncRun[];
  mappings: MappingTemplate[];
  statusFilter: string;
  mappingFilter: string;
  onStatusFilterChange: (v: string) => void;
  onMappingFilterChange: (v: string) => void;
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

function RunRow({ run, mappingName }: { run: SyncRun; mappingName: string }) {
  return (
    <tr className="border-b transition-colors hover:bg-muted/50">
      <td className="p-3 text-sm font-medium">#{run.id}</td>
      <td className="p-3">
        <StatusBadge status={run.status} />
      </td>
      <td className="p-3 text-sm text-muted-foreground">
        {mappingName}
      </td>
      <td className="py-3 pl-0 pr-3 text-sm">
        {run.total_records != null ? (
          <div className="flex flex-col items-center gap-0.5">
            <span>{run.total_records}</span>
            <div className="flex gap-2 text-xs">
              <span className="text-green-600">{run.success_count ?? 0} success</span>
              <span className="text-red-500">{run.failed_count ?? 0} failed</span>
              <span className="text-muted-foreground">{run.skipped_count ?? 0} skipped</span>
            </div>
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

export function RunsList({ runs, mappings, statusFilter, mappingFilter, onStatusFilterChange, onMappingFilterChange }: Props) {
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

  const statusOptions = ["pending", "running", "completed", "failed"].map((s) => ({
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
