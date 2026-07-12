"use client";

import { useState } from "react";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { Search } from "lucide-react";
import type { TririgaField, KontractsField } from "@/types";

type Field = TririgaField | KontractsField;

interface Props {
  title: string;
  fields: Field[];
  loading?: boolean;
  side: "source" | "target";
}

function getFieldTypeColor(type: string): string {
  const map: Record<string, string> = {
    string: "text-blue-600 dark:text-blue-400",
    number: "text-green-600 dark:text-green-400",
    currency: "text-green-600 dark:text-green-400",
    date: "text-orange-600 dark:text-orange-400",
    datetime: "text-orange-600 dark:text-orange-400",
    boolean: "text-purple-600 dark:text-purple-400",
    array: "text-pink-600 dark:text-pink-400",
    integer: "text-green-600 dark:text-green-400",
  };
  return map[type] ?? "text-muted-foreground";
}

export function FieldPanel({ title, fields, loading, side }: Props) {
  const [search, setSearch] = useState("");

  const filtered = fields.filter(
    (f) =>
      f.name.toLowerCase().includes(search.toLowerCase()) ||
      ("label" in f && f.label?.toLowerCase().includes(search.toLowerCase())) ||
      ("description" in f && (f as KontractsField).description?.toLowerCase().includes(search.toLowerCase()))
  );

  return (
    <div className="flex h-full flex-col rounded-lg border bg-card">
      <div className="border-b p-3">
        <h3 className="text-sm font-semibold">{title}</h3>
        <p className="text-xs text-muted-foreground">
          {fields.length} fields available
        </p>
      </div>

      <div className="border-b p-2">
        <div className="relative">
          <Search className="absolute left-2 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
          <Input
            className="h-7 pl-7 text-xs"
            placeholder="Filter fields..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-auto">
        {loading ? (
          <div className="p-4 text-center text-xs text-muted-foreground">
            Loading fields...
          </div>
        ) : filtered.length === 0 ? (
          <div className="p-4 text-center text-xs text-muted-foreground">
            {search ? "No fields match your search" : "No fields available"}
          </div>
        ) : (
          <div className="divide-y">
            {filtered.map((field) => {
              const label =
                "label" in field ? (field as TririgaField).label : field.name;
              const required =
                "required" in field ? (field as KontractsField).required : false;
              const description =
                "description" in field
                  ? (field as KontractsField).description
                  : undefined;

              return (
                <div
                  key={field.name}
                  className="cursor-default px-3 py-2 hover:bg-muted/50"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs">{field.name}</span>
                    {required && (
                      <span className="text-xs text-red-500">*</span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={cn("text-xs", getFieldTypeColor(field.type))}>
                      {field.type}
                    </span>
                    {label !== field.name && (
                      <span className="text-xs text-muted-foreground">{label}</span>
                    )}
                  </div>
                  {description && (
                    <p className="mt-0.5 text-xs text-muted-foreground line-clamp-1">
                      {description}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
