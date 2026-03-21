"use client";

import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import type { TransformType } from "@/types";

interface Props {
  transformType: TransformType;
  config: Record<string, unknown>;
  onChange: (config: Record<string, unknown>) => void;
}

export function TransformEditor({ transformType, config, onChange }: Props) {
  const [local, setLocal] = useState<Record<string, unknown>>(config);

  useEffect(() => {
    setLocal(config);
  }, [transformType]);

  const update = (key: string, value: unknown) => {
    const next = { ...local, [key]: value };
    setLocal(next);
    onChange(next);
  };

  if (transformType === "direct") {
    return (
      <div className="text-xs text-muted-foreground">
        Copies value as-is from source to target field.
      </div>
    );
  }

  if (transformType === "constant") {
    return (
      <div className="space-y-2">
        <Label className="text-xs">Constant Value</Label>
        <Input
          className="h-8 text-xs"
          placeholder="e.g. USD"
          value={String(local.value ?? "")}
          onChange={(e) => update("value", e.target.value)}
        />
      </div>
    );
  }

  if (transformType === "date_format") {
    return (
      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <Label className="text-xs">Input Format</Label>
          <Input
            className="h-8 text-xs"
            placeholder="Auto-detect"
            value={String(local.input_format ?? "")}
            onChange={(e) => update("input_format", e.target.value || undefined)}
          />
          <p className="text-xs text-muted-foreground">e.g. %d/%m/%Y</p>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Output Format</Label>
          <Input
            className="h-8 text-xs"
            placeholder="%Y-%m-%d"
            value={String(local.output_format ?? "%Y-%m-%d")}
            onChange={(e) => update("output_format", e.target.value)}
          />
          <p className="text-xs text-muted-foreground">e.g. %Y-%m-%d</p>
        </div>
      </div>
    );
  }

  if (transformType === "number_convert") {
    return (
      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <Label className="text-xs">Type</Label>
          <select
            className="h-8 w-full rounded-md border border-input bg-background px-2 text-xs"
            value={String(local.as_type ?? "float")}
            onChange={(e) => update("as_type", e.target.value)}
          >
            <option value="float">Float</option>
            <option value="int">Integer</option>
          </select>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Decimals</Label>
          <Input
            className="h-8 text-xs"
            type="number"
            min={0}
            max={10}
            placeholder="2"
            value={String(local.decimals ?? "")}
            onChange={(e) =>
              update("decimals", e.target.value ? parseInt(e.target.value) : undefined)
            }
          />
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Divisor</Label>
          <Input
            className="h-8 text-xs"
            type="number"
            placeholder="1"
            value={String(local.divisor ?? "")}
            onChange={(e) =>
              update("divisor", e.target.value ? parseFloat(e.target.value) : undefined)
            }
          />
          <p className="text-xs text-muted-foreground">e.g. 100 for % to decimal</p>
        </div>
        <div className="space-y-1">
          <Label className="text-xs">Default</Label>
          <Input
            className="h-8 text-xs"
            placeholder="0"
            value={String(local.default ?? "")}
            onChange={(e) =>
              update("default", e.target.value ? parseFloat(e.target.value) : undefined)
            }
          />
        </div>
      </div>
    );
  }

  if (transformType === "boolean_convert") {
    return (
      <div className="text-xs text-muted-foreground">
        Converts "true"/"yes"/"1" to true and "false"/"no"/"0" to false.
      </div>
    );
  }

  if (transformType === "string_template") {
    return (
      <div className="space-y-2">
        <Label className="text-xs">Template</Label>
        <Input
          className="h-8 font-mono text-xs"
          placeholder="{fieldName} - {otherField}"
          value={String(local.template ?? "")}
          onChange={(e) => update("template", e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          Use {"{fieldName}"} placeholders. {"{value}"} refers to the source field value.
        </p>
      </div>
    );
  }

  if (transformType === "lookup_table") {
    const tableStr = local.table ? JSON.stringify(local.table, null, 2) : "{}";
    return (
      <div className="space-y-2">
        <Label className="text-xs">Lookup Table (JSON)</Label>
        <textarea
          className="h-28 w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs focus:outline-none focus:ring-2 focus:ring-ring"
          defaultValue={tableStr}
          onChange={(e) => {
            try {
              const parsed = JSON.parse(e.target.value);
              update("table", parsed);
            } catch {
              // ignore parse errors while typing
            }
          }}
        />
        <div className="space-y-1">
          <Label className="text-xs">Default (if no match)</Label>
          <Input
            className="h-8 text-xs"
            placeholder="original value"
            value={String(local.default ?? "")}
            onChange={(e) => update("default", e.target.value || undefined)}
          />
        </div>
      </div>
    );
  }

  if (transformType === "json_path") {
    return (
      <div className="space-y-2">
        <Label className="text-xs">JSONPath Expression</Label>
        <Input
          className="h-8 font-mono text-xs"
          placeholder="$.address.city"
          value={String(local.path ?? "")}
          onChange={(e) => update("path", e.target.value)}
        />
        <div className="space-y-1">
          <Label className="text-xs">Default</Label>
          <Input
            className="h-8 text-xs"
            placeholder="N/A"
            value={String(local.default ?? "")}
            onChange={(e) => update("default", e.target.value || undefined)}
          />
        </div>
      </div>
    );
  }

  return null;
}
