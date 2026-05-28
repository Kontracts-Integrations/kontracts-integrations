"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList } from "@/components/ui/command";
import { SearchableSelect } from "@/components/ui/searchable-select";
import { TransformEditor } from "./TransformEditor";
import { cn } from "@/lib/utils";
import { Trash2, ChevronDown, ChevronUp, GripVertical, ChevronsUpDown } from "lucide-react";
import type { FieldMapping, TririgaField, KontractsField, TransformType } from "@/types";

const TRANSFORM_OPTIONS: { value: TransformType; label: string }[] = [
  { value: "direct", label: "Direct copy" },
  { value: "constant", label: "Constant value" },
  { value: "date_format", label: "Date format" },
  { value: "number_convert", label: "Number convert" },
  { value: "boolean_convert", label: "Boolean convert" },
  { value: "string_template", label: "String template" },
  { value: "lookup_table", label: "Lookup table" },
  { value: "json_path", label: "JSON path" },
  { value: "currency_code", label: "Currency code" },
  { value: "lease_lookup", label: "Lease lookup (TRIRIGA → Kontracts ID)" },
];

interface Props {
  mapping: FieldMapping;
  sourceFields: TririgaField[];
  assocFields?: TririgaField[];
  assocFieldsLoading?: boolean;
  targetFields: KontractsField[];
  sourceLoading?: boolean;
  onChange: (updated: FieldMapping) => void;
  onDelete: () => void;
  index: number;
}

export function MappingRow({
  mapping,
  sourceFields,
  assocFields = [],
  assocFieldsLoading,
  targetFields,
  sourceLoading,
  onChange,
  onDelete,
  index,
}: Props) {
  const activeFields = mapping.use_associated ? assocFields : sourceFields;
  const activeLoading = mapping.use_associated ? assocFieldsLoading : sourceLoading;
  const [expanded, setExpanded] = useState(false);
  const [sourceOpen, setSourceOpen] = useState(false);

  const update = (patch: Partial<FieldMapping>) => {
    onChange({ ...mapping, ...patch });
  };

  const showExpandButton = mapping.transform_type !== "direct";

  return (
    <div className={cn(
      "rounded-md border bg-card border-l-4",
      mapping.use_associated ? "border-l-purple-400" : "border-l-blue-400",
      expanded && "ring-1 ring-primary/20"
    )}>
      <div className="flex items-center gap-3 p-2">
        {/* Drag handle */}
        <GripVertical className="h-4 w-4 flex-shrink-0 cursor-grab text-muted-foreground" />

        {/* Row number */}
        <span className="w-5 text-center text-xs text-muted-foreground">{index + 1}</span>


        {/* Source field — searchable combobox */}
        <div className="flex-1">
          <Popover open={sourceOpen} onOpenChange={setSourceOpen}>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                role="combobox"
                disabled={activeLoading}
                className="h-8 w-full justify-between text-xs font-normal"
              >
                {mapping.source_field ? (
                  (() => {
                    const raw = mapping.source_field;
                    const [sec, name] = raw.includes("||") ? raw.split("||", 2) : ["", raw];
                    return (
                      <span className="truncate">
                        {sec && <span className="text-muted-foreground">{sec}::</span>}
                        <span className="font-mono">{name}</span>
                      </span>
                    );
                  })()
                ) : (
                  <span className="text-muted-foreground">{activeLoading ? "Loading fields..." : "Source field..."}</span>
                )}
                <ChevronsUpDown className="ml-1 h-3 w-3 shrink-0 opacity-50" />
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-[400px] p-0">
              <Command
                filter={(value, search) => {
                  // Search by field name (part after ||) and label — ignore section prefix
                  const fieldName = value.includes("||") ? value.split("||")[1] : value;
                  const field = activeFields.find((f) => f.name === fieldName);
                  const haystack = `${fieldName} ${field?.label ?? ""}`.toLowerCase();
                  return haystack.includes(search.toLowerCase()) ? 1 : 0;
                }}
              >
                <CommandInput placeholder="Search fields..." className="h-9" />
                <CommandList>
                  <CommandEmpty>No fields found.</CommandEmpty>
                  <CommandItem
                    value="__none__"
                    onSelect={() => { update({ source_field: "" }); setSourceOpen(false); }}
                  >
                    — none —
                  </CommandItem>
                  {(() => {
                    const grouped = activeFields.reduce((acc, f) => {
                      const sec = f.section || "General";
                      if (!acc[sec]) acc[sec] = [];
                      acc[sec].push(f);
                      return acc;
                    }, {} as Record<string, typeof sourceFields>);
                    return Object.entries(grouped).map(([section, fields]) => (
                      <CommandGroup key={section} heading={section}>
                        {fields.map((f) => {
                          const compositeValue = `${section}||${f.name}`;
                          return (
                            <CommandItem
                              key={compositeValue}
                              value={compositeValue}
                              onSelect={() => { update({ source_field: compositeValue }); setSourceOpen(false); }}
                            >
                              <span className="font-mono">{f.name}</span>
                              {f.label !== f.name && <span className="ml-1 text-muted-foreground">({f.label})</span>}
                            </CommandItem>
                          );
                        })}
                      </CommandGroup>
                    ));
                  })()}
                </CommandList>
              </Command>
            </PopoverContent>
          </Popover>
        </div>

        {/* Arrow */}
        <span className="text-muted-foreground">→</span>

        {/* Transform type */}
        <div className="w-56">
          <SearchableSelect
            options={TRANSFORM_OPTIONS}
            value={mapping.transform_type}
            onValueChange={(v) => {
              update({
                transform_type: v as TransformType,
                transform_config: {},
              });
              setExpanded(v !== "direct" && v !== "boolean_convert");
            }}
            placeholder="Transform type..."
            searchPlaceholder="Search transform..."
            widthClass="w-[280px]"
          />
        </div>

        {/* Arrow */}
        <span className="text-muted-foreground">→</span>

        {/* Target field */}
        <div className="flex-1">
          <SearchableSelect
            options={[
              { value: "__none__", label: "— none —" },
              ...targetFields.map((f) => ({
                value: f.name,
                label: f.required ? `${f.name} *` : f.name,
              })),
            ]}
            value={mapping.target_field || "__none__"}
            onValueChange={(v) => update({ target_field: v === "__none__" ? "" : v })}
            placeholder="Target field..."
            searchPlaceholder="Search target fields..."
            widthClass="w-[280px]"
          />
        </div>

        {/* Required toggle */}
        <button
          type="button"
          onClick={() => update({ is_required: !mapping.is_required })}
          className={cn(
            "flex-shrink-0 rounded px-1.5 py-0.5 text-xs font-medium transition-colors",
            mapping.is_required
              ? "bg-red-100 text-red-600 dark:bg-red-900 dark:text-red-300"
              : "bg-muted text-muted-foreground hover:text-foreground"
          )}
          title="Toggle required"
        >
          req
        </button>

        {/* Expand config */}
        {showExpandButton && (
          <button
            type="button"
            onClick={() => setExpanded((e) => !e)}
            className="flex-shrink-0 text-muted-foreground hover:text-foreground"
            title="Configure transform"
          >
            {expanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </button>
        )}

        {/* Delete */}
        <button
          type="button"
          onClick={onDelete}
          className="flex-shrink-0 text-muted-foreground hover:text-destructive"
          title="Remove mapping row"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>

      {/* Transform config panel */}
      {expanded && showExpandButton && (
        <div className="border-t bg-muted/30 px-10 py-3">
          <TransformEditor
            transformType={mapping.transform_type}
            config={(mapping.transform_config as Record<string, unknown>) ?? {}}
            onChange={(config) => update({ transform_config: config })}
          />
        </div>
      )}
    </div>
  );
}
