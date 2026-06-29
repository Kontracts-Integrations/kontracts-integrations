import { useState, useEffect } from "react";
import { Loader2, Hourglass, Square, Search, X, Timer, ChevronDown } from "lucide-react";
import { parseISO } from "date-fns";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
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
  searchText: string;
  runSearchText: string;
  onStatusFilterChange: (v: string) => void;
  onMappingFilterChange: (v: string) => void;
  onSearchTextChange: (v: string) => void;
  onRunSearchTextChange: (v: string) => void;
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
      <td className="p-3 text-sm text-muted-foreground font-medium text-center">
        {mappingName}
      </td>
      <td className="p-2 text-sm">
        {run.total_records != null ? (
          <div className="flex items-center justify-center gap-3 py-1">
            {/* Left Separation: Total Records */}
            <div className="flex flex-col items-center justify-center min-w-[70px]">
              <span className="text-[10px] uppercase font-semibold text-muted-foreground leading-none">Total</span>
              <span className="text-base font-bold text-foreground mt-1.5 leading-none">
                {run.total_records.toLocaleString()}
              </span>
              {run.status === "running" && (
                <span className="text-[10px] text-primary font-bold mt-1.5 animate-pulse">
                  {(() => {
                    const processed = (run.success_count ?? 0) + (run.failed_count ?? 0) + (run.skipped_count ?? 0);
                    return Math.min(100, Math.round((processed / run.total_records) * 100));
                  })()}%
                </span>
              )}
            </div>
            
            {/* Divider Line 1 */}
            <div className="h-10 w-[1px] bg-border shrink-0" />
            
            {/* Middle Separation: Category & Count */}
            <div className="flex flex-col justify-center text-xs gap-0.5 min-w-[105px]">
              <div className="h-4 flex items-center gap-1.5 justify-between">
                <div className="flex items-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-green-500 shrink-0" />
                  <span className="text-muted-foreground">Success:</span>
                </div>
                <span className="font-semibold text-green-600">{(run.success_count ?? 0).toLocaleString()}</span>
              </div>
              <div className="h-4 flex items-center gap-1.5 justify-between">
                <div className="flex items-center gap-1">
                  <span className="h-2 w-2 rounded-full bg-red-500 shrink-0" />
                  <span className="text-muted-foreground">Failed:</span>
                </div>
                <span className="font-semibold text-red-500">{(run.failed_count ?? 0).toLocaleString()}</span>
              </div>
              <div className="h-4 flex items-center gap-1.5 justify-between">
                <div className="flex items-center gap-1">
                  <span className="h-2.5 w-2.5 rounded-full bg-gray-400 dark:bg-gray-600 shrink-0 scale-75" />
                  <span className="text-muted-foreground">Skipped:</span>
                </div>
                <span className="font-semibold text-muted-foreground">{(run.skipped_count ?? 0).toLocaleString()}</span>
              </div>
            </div>

            {/* Right Separation: Percentages in Brackets (no divider) */}
            <div className="flex flex-col justify-center text-xs gap-0.5 text-right min-w-[36px] font-semibold text-muted-foreground">
              <div className="h-4 flex items-center justify-end">
                ({run.total_records > 0 ? Math.round(((run.success_count ?? 0) / run.total_records) * 100) : 0}%)
              </div>
              <div className="h-4 flex items-center justify-end">
                ({run.total_records > 0 ? Math.round(((run.failed_count ?? 0) / run.total_records) * 100) : 0}%)
              </div>
              <div className="h-4 flex items-center justify-end">
                ({run.total_records > 0 ? Math.round(((run.skipped_count ?? 0) / run.total_records) * 100) : 0}%)
              </div>
            </div>
          </div>
        ) : (
          <span className="text-muted-foreground">—</span>
        )}
      </td>
      <td className="p-3 text-xs text-muted-foreground text-center">
        <div className="flex flex-col gap-1 items-center justify-center text-center text-xs text-muted-foreground">
          <span className="whitespace-nowrap">{formatDateTime(run.created_at)}</span>
          <div className="flex items-center gap-1 text-[11px] text-muted-foreground/80 mt-0.5">
            <Timer className="h-3.5 w-3.5 shrink-0" />
            <span>
              {run.status === "running" && run.started_at
                ? <LiveDuration startedAt={run.started_at} />
                : formatDuration(run.started_at, run.completed_at)}
            </span>
          </div>
        </div>
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
  searchPlaceholder = "Search Status...",
}: {
  value: string;
  onChange: (v: string) => void;
  options: { value: string; label: string }[];
  allLabel: string;
  searchPlaceholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const isFiltered = value !== "all";

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button className="flex items-center gap-1 h-6 border-0 bg-transparent p-0 text-xs font-semibold text-muted-foreground hover:text-foreground focus:outline-none select-none">
          <span className={cn("flex items-center gap-1", isFiltered && "text-foreground font-bold")}>
            {allLabel}
            {isFiltered && <span className="h-1.5 w-1.5 rounded-full bg-primary" />}
          </span>
          <ChevronDown className="h-3.5 w-3.5 opacity-60 ml-0.5" />
        </button>
      </PopoverTrigger>
      <PopoverContent className="w-[180px] p-0" align="start">
        <Command filter={(val, search) => {
          if (val === "all") return 1;
          const opt = options.find(o => o.value === val);
          const haystack = `${val} ${opt?.label ?? ""}`.toLowerCase();
          return haystack.includes(search.toLowerCase()) ? 1 : 0;
        }}>
          <CommandInput placeholder={searchPlaceholder} className="h-8 text-xs" />
          <CommandList className="max-h-[200px] overflow-y-auto">
            <CommandEmpty className="py-2 text-center text-xs text-muted-foreground">No matches found.</CommandEmpty>
            <CommandGroup>
              <CommandItem
                value="all"
                onSelect={() => {
                  onChange("all");
                  setOpen(false);
                }}
                className="text-xs"
              >
                - All -
              </CommandItem>
              {options.map((opt) => (
                <CommandItem
                  key={opt.value}
                  value={opt.value}
                  onSelect={() => {
                    onChange(opt.value);
                    setOpen(false);
                  }}
                  className="text-xs"
                >
                  <span className="truncate">{opt.label}</span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

export function RunsList({
  runs,
  mappings,
  statusFilter,
  mappingFilter,
  searchText,
  runSearchText,
  onStatusFilterChange,
  onMappingFilterChange,
  onSearchTextChange,
  onRunSearchTextChange,
  onSelect,
  onCancel,
}: Props) {
  const [isSearchExpanded, setIsSearchExpanded] = useState(false);
  const [isRunSearchExpanded, setIsRunSearchExpanded] = useState(false);
  const mappingMap = Object.fromEntries(mappings.map((m) => [m.id, m.name]));

  useEffect(() => {
    if (!isSearchExpanded && !isRunSearchExpanded) return;

    const handleOutsideClick = (e: MouseEvent) => {
      if (isSearchExpanded) {
        const container = document.getElementById("mapping-search-container");
        if (container && !container.contains(e.target as Node)) {
          setIsSearchExpanded(false);
        }
      }
      if (isRunSearchExpanded) {
        const container = document.getElementById("run-search-container");
        if (container && !container.contains(e.target as Node)) {
          setIsRunSearchExpanded(false);
        }
      }
    };

    document.addEventListener("mousedown", handleOutsideClick);
    return () => {
      document.removeEventListener("mousedown", handleOutsideClick);
    };
  }, [isSearchExpanded, isRunSearchExpanded]);

  useEffect(() => {
    if (searchText === "") {
      setIsSearchExpanded(false);
    }
  }, [searchText]);

  useEffect(() => {
    if (runSearchText === "") {
      setIsRunSearchExpanded(false);
    }
  }, [runSearchText]);

  const filtered = runs.filter((r) => {
    if (statusFilter !== "all" && r.status !== statusFilter) return false;
    if (mappingFilter !== "all" && String(r.mapping_template_id) !== mappingFilter) return false;
    if (searchText) {
      const templateName = r.mapping_template_id ? (mappingMap[r.mapping_template_id] ?? "").toLowerCase() : "";
      if (!templateName.includes(searchText.toLowerCase())) return false;
    }
    if (runSearchText) {
      const cleanSearch = runSearchText.startsWith("#") ? runSearchText.slice(1) : runSearchText;
      if (cleanSearch && !String(r.id).includes(cleanSearch)) return false;
    }
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
      <table className="w-full min-w-[1080px] table-fixed">
        <thead>
          <tr className="border-b bg-muted/50 text-left">
            <th className="p-3 text-xs font-semibold text-muted-foreground w-[130px]">
              <div className="flex items-center gap-1.5">
                <span className={cn(runSearchText && "text-foreground font-bold")}>
                  Run
                </span>
                {isRunSearchExpanded ? (
                  <div
                    id="run-search-container"
                    className="flex items-center gap-0.5 bg-white border border-zinc-300 rounded-md px-1.5 py-0.5 w-[75px] shadow-sm"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <span className="select-none text-zinc-500 font-medium text-[11px] mr-[1px]">#</span>
                    <input
                      type="text"
                      placeholder=""
                      value={runSearchText}
                      onChange={(e) => onRunSearchTextChange(e.target.value)}
                      className="bg-transparent border-0 outline-none text-[11px] w-full text-zinc-900 placeholder:text-zinc-900 focus:ring-0 p-0 font-medium"
                      autoFocus
                    />
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onRunSearchTextChange("");
                        setIsRunSearchExpanded(false);
                      }}
                      className="text-zinc-400 hover:text-zinc-600 shrink-0"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setIsRunSearchExpanded(true)}
                    className="p-1 hover:text-foreground hover:bg-muted rounded transition-colors focus:outline-none select-none shrink-0"
                    title="Search run ID"
                  >
                    <Search className="h-3.5 w-3.5 fill-white text-zinc-500 dark:text-zinc-400" />
                  </button>
                )}
              </div>
            </th>
            <th className="p-3 text-xs font-semibold text-muted-foreground w-[110px]">
              <ColumnFilter
                value={statusFilter}
                onChange={onStatusFilterChange}
                options={statusOptions}
                allLabel="Status"
              />
            </th>
            <th className="p-3 text-xs font-semibold text-muted-foreground text-center w-[280px]">
              <div className="flex items-center justify-center gap-2">
                <span className={cn(searchText && "text-foreground font-bold")}>
                  Mapping Template
                </span>
                {isSearchExpanded ? (
                  <div
                    id="mapping-search-container"
                    className="flex items-center gap-1.5 bg-white border border-zinc-300 rounded-md px-2 py-0.5 w-[140px] shadow-sm"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="text"
                      placeholder="Search..."
                      value={searchText}
                      onChange={(e) => onSearchTextChange(e.target.value)}
                      className="bg-transparent border-0 outline-none text-[11px] w-full text-zinc-900 placeholder:text-zinc-900 focus:ring-0 p-0 font-medium"
                      autoFocus
                    />
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onSearchTextChange("");
                        setIsSearchExpanded(false);
                      }}
                      className="text-zinc-400 hover:text-zinc-600 shrink-0"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </div>
                ) : (
                  <button
                    onClick={() => setIsSearchExpanded(true)}
                    className="p-1 hover:text-foreground hover:bg-muted rounded transition-colors focus:outline-none select-none shrink-0"
                    title="Search mapping template"
                  >
                    <Search className="h-3.5 w-3.5 fill-white text-zinc-500 dark:text-zinc-400" />
                  </button>
                )}
              </div>
            </th>
            <th className="p-3 text-xs font-semibold text-muted-foreground text-center w-[260px]">Record Count</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground text-center w-[200px]">Start Time (IST) & Duration</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground w-[100px]">Ran by</th>
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
