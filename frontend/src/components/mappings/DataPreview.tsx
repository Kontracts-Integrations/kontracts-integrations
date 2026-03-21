"use client";

import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface Props {
  sourceRecords: Record<string, unknown>[];
  mappedPayloads?: Record<string, unknown>[];
  mappingWarnings?: string[][];
}

function JsonView({ data }: { data: unknown }) {
  return (
    <pre className="overflow-auto rounded-md bg-muted p-4 text-xs leading-relaxed">
      {JSON.stringify(data, null, 2)}
    </pre>
  );
}

export function DataPreview({ sourceRecords, mappedPayloads, mappingWarnings }: Props) {
  const [recordIndex, setRecordIndex] = useState(0);

  const total = sourceRecords.length;
  const source = sourceRecords[recordIndex] ?? {};
  const mapped = mappedPayloads?.[recordIndex] ?? null;
  const warnings = mappingWarnings?.[recordIndex] ?? [];

  return (
    <div className="space-y-2">
      {total > 1 && (
        <div className="flex items-center gap-2">
          <button
            type="button"
            disabled={recordIndex === 0}
            onClick={() => setRecordIndex((i) => i - 1)}
            className="rounded border px-2 py-1 text-xs disabled:opacity-40"
          >
            ← Prev
          </button>
          <span className="text-xs text-muted-foreground">
            Record {recordIndex + 1} of {total}
          </span>
          <button
            type="button"
            disabled={recordIndex >= total - 1}
            onClick={() => setRecordIndex((i) => i + 1)}
            className="rounded border px-2 py-1 text-xs disabled:opacity-40"
          >
            Next →
          </button>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="rounded-md border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-800 dark:bg-yellow-950">
          <p className="mb-1 text-xs font-medium text-yellow-800 dark:text-yellow-200">
            Transform warnings:
          </p>
          <ul className="space-y-0.5">
            {warnings.map((w, i) => (
              <li key={i} className="text-xs text-yellow-700 dark:text-yellow-300">
                • {w}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">Source (TRIRIGA)</CardTitle>
          </CardHeader>
          <CardContent>
            <JsonView data={source} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm text-muted-foreground">
              Mapped (Kontracts)
              {!mapped && (
                <span className="ml-2 text-xs font-normal text-muted-foreground">
                  — add field mappings to preview
                </span>
              )}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {mapped ? (
              <JsonView data={mapped} />
            ) : (
              <div className="rounded-md bg-muted p-4 text-xs text-muted-foreground">
                Add field mappings in the "Field Mappings" tab, then return here to see the
                transformed output.
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
