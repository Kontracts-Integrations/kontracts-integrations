"use client";

import { useState } from "react";
import { cn, getStatusColor } from "@/lib/utils";
import type { SyncRecord } from "@/types";

interface Props {
  records: SyncRecord[];
}

function RecordRow({ record }: { record: SyncRecord }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        className="cursor-pointer border-b hover:bg-muted/50"
        onClick={() => setExpanded((e) => !e)}
      >
        <td className="p-3 text-sm font-mono text-muted-foreground">
          {record.tririga_record_id ?? "—"}
        </td>
        <td className="p-3 text-sm font-mono text-muted-foreground">
          {record.kontracts_record_id ?? "—"}
        </td>
        <td className="p-3">
          <span
            className={cn(
              "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
              getStatusColor(record.status)
            )}
          >
            {record.status}
          </span>
        </td>
        <td className="p-3 text-sm text-muted-foreground">
          {record.error_message ? (
            <span className="text-red-500">{record.error_message}</span>
          ) : (
            "—"
          )}
        </td>
        <td className="p-3 text-center text-xs text-muted-foreground">
          {expanded ? "▲" : "▼"}
        </td>
      </tr>
      {expanded && (
        <tr className="border-b bg-muted/20">
          <td colSpan={5} className="p-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="mb-1 text-xs font-semibold text-muted-foreground">
                  Source Data (TRIRIGA)
                </p>
                <pre className="overflow-auto rounded-md bg-muted p-3 text-xs">
                  {JSON.stringify(record.source_data ?? {}, null, 2)}
                </pre>
              </div>
              <div>
                <p className="mb-1 text-xs font-semibold text-muted-foreground">
                  Mapped Data (Kontracts)
                </p>
                <pre className="overflow-auto rounded-md bg-muted p-3 text-xs">
                  {JSON.stringify(record.mapped_data ?? {}, null, 2)}
                </pre>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export function RecordResults({ records }: Props) {
  if (!records.length) {
    return (
      <p className="py-4 text-center text-sm text-muted-foreground">No records to display.</p>
    );
  }

  return (
    <div className="overflow-auto rounded-lg border">
      <table className="w-full">
        <thead>
          <tr className="border-b bg-muted/50 text-left">
            <th className="p-3 text-xs font-semibold text-muted-foreground">TRIRIGA ID</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">Kontracts ID</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">Status</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground">Error</th>
            <th className="p-3 text-xs font-semibold text-muted-foreground" />
          </tr>
        </thead>
        <tbody>
          {records.map((r) => (
            <RecordRow key={r.id} record={r} />
          ))}
        </tbody>
      </table>
    </div>
  );
}
