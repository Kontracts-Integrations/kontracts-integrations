"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { TransformEditor } from "./TransformEditor";
import { cn } from "@/lib/utils";
import { Trash2, ChevronDown, ChevronUp, GripVertical } from "lucide-react";
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
];

interface Props {
  mapping: FieldMapping;
  sourceFields: TririgaField[];
  targetFields: KontractsField[];
  sourceLoading?: boolean;
  onChange: (updated: FieldMapping) => void;
  onDelete: () => void;
  index: number;
}

export function MappingRow({
  mapping,
  sourceFields,
  targetFields,
  sourceLoading,
  onChange,
  onDelete,
  index,
}: Props) {
  const [expanded, setExpanded] = useState(false);

  const update = (patch: Partial<FieldMapping>) => {
    onChange({ ...mapping, ...patch });
  };

  const showExpandButton = mapping.transform_type !== "direct";

  return (
    <div className={cn("rounded-md border bg-card", expanded && "ring-1 ring-primary/20")}>
      <div className="flex items-center gap-2 p-3">
        {/* Drag handle */}
        <GripVertical className="h-4 w-4 flex-shrink-0 cursor-grab text-muted-foreground" />

        {/* Row number */}
        <span className="w-5 text-center text-xs text-muted-foreground">{index + 1}</span>

        {/* Source field */}
        <div className="flex-1">
          <Select
            value={mapping.source_field || "__none__"}
            onValueChange={(v) => update({ source_field: v === "__none__" ? "" : v })}
            disabled={sourceLoading}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder={sourceLoading ? "Loading fields..." : "Source field..."} />
            </SelectTrigger>
            <SelectContent>
              {sourceLoading ? (
                <div className="py-2 text-center text-xs text-muted-foreground">Loading fields...</div>
              ) : sourceFields.length === 0 ? (
                <div className="py-2 text-center text-xs text-muted-foreground">No fields — select a Business Object above</div>
              ) : (
                <>
                  <SelectItem value="__none__">— none —</SelectItem>
                  {sourceFields.map((f) => (
                    <SelectItem key={f.name} value={f.name}>
                      <span className="font-mono">{f.name}</span>
                      <span className="ml-2 text-muted-foreground">({f.type})</span>
                    </SelectItem>
                  ))}
                </>
              )}
            </SelectContent>
          </Select>
        </div>

        {/* Arrow */}
        <span className="text-muted-foreground">→</span>

        {/* Transform type */}
        <div className="w-40">
          <Select
            value={mapping.transform_type}
            onValueChange={(v) => {
              update({
                transform_type: v as TransformType,
                transform_config: {},
              });
              setExpanded(v !== "direct" && v !== "boolean_convert");
            }}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {TRANSFORM_OPTIONS.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Arrow */}
        <span className="text-muted-foreground">→</span>

        {/* Target field */}
        <div className="flex-1">
          <Select
            value={mapping.target_field || "__none__"}
            onValueChange={(v) => update({ target_field: v === "__none__" ? "" : v })}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Target field..." />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">— none —</SelectItem>
              {targetFields.map((f) => (
                <SelectItem key={f.name} value={f.name}>
                  <span className="font-mono">{f.name}</span>
                  {f.required && <span className="ml-1 text-red-500">*</span>}
                  <span className="ml-2 text-muted-foreground">({f.type})</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
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
