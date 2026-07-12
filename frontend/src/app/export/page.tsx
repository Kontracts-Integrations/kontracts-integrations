"use client";

import { useRef } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { mappingsApi, connectionsApi } from "@/lib/api";
import { MainLayout } from "@/components/layout/MainLayout";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "@/components/ui/toaster";
import { Download, Upload, Loader2, FileCode, Plug, ShieldCheck } from "lucide-react";

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export default function ExportImportPage() {
  const qc = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const exportMappings = useMutation({
    mutationFn: () => mappingsApi.exportAll(),
    onSuccess: (blob) => downloadBlob(blob, "mapping-templates.json"),
    onError: (err: Error) =>
      toast({ title: "Export failed", description: err.message, variant: "destructive" }),
  });

  const exportConnections = useMutation({
    mutationFn: () => connectionsApi.export(),
    onSuccess: (blob) => downloadBlob(blob, "connections.json"),
    onError: (err: Error) =>
      toast({ title: "Export failed", description: err.message, variant: "destructive" }),
  });

  const importMappings = useMutation({
    mutationFn: async (file: File) => {
      const text = await file.text();
      let parsed: Record<string, unknown>;
      try {
        parsed = JSON.parse(text);
      } catch {
        throw new Error("Selected file is not valid JSON");
      }
      // Accept a bundle ({ mappings: [...] }), a single export ({ template }), or a bare template.
      const templates: Record<string, unknown>[] = Array.isArray(parsed.mappings)
        ? (parsed.mappings as Record<string, unknown>[])
        : ["template" in parsed ? (parsed.template as Record<string, unknown>) : parsed];

      let ok = 0;
      const failures: string[] = [];
      for (const t of templates) {
        try {
          await mappingsApi.import({ template: t });
          ok += 1;
        } catch (e) {
          failures.push((e as Error).message);
        }
      }
      return { ok, failures };
    },
    onSuccess: ({ ok, failures }) => {
      qc.invalidateQueries({ queryKey: ["mappings"] });
      if (failures.length) {
        toast({
          title: `Imported ${ok}, ${failures.length} failed`,
          description: failures[0],
          variant: "destructive",
        });
      } else {
        toast({ title: `Imported ${ok} mapping${ok === 1 ? "" : "s"}` });
      }
    },
    onError: (err: Error) =>
      toast({ title: "Import failed", description: err.message, variant: "destructive" }),
  });

  const handleFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) importMappings.mutate(file);
    e.target.value = "";
  };

  return (
    <MainLayout title="Export / Import">
      <input
        ref={fileInputRef}
        type="file"
        accept="application/json,.json"
        className="hidden"
        onChange={handleFile}
      />
      <div className="flex-1 overflow-y-auto space-y-4 max-w-3xl">
        <p className="text-sm text-muted-foreground">
          Back up or move configuration between environments. Exports are portable JSON files.
        </p>

        {/* Mapping Templates */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <FileCode className="h-4 w-4 text-primary" />
              Mapping Templates
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-sm text-muted-foreground">
              Export all templates (config + current field mappings) as one file, or import them into
              this environment. Imported templates are created new; connection references that don&apos;t
              exist here are dropped.
            </p>
            <div className="flex flex-wrap gap-2">
              <Button
                onClick={() => exportMappings.mutate()}
                disabled={exportMappings.isPending}
              >
                {exportMappings.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Download className="mr-2 h-4 w-4" />
                )}
                Export all mappings
              </Button>
              <Button
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
                disabled={importMappings.isPending}
              >
                {importMappings.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="mr-2 h-4 w-4" />
                )}
                Import mappings
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Connections */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Plug className="h-4 w-4 text-primary" />
              Connections
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-2 text-xs text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-200">
              <ShieldCheck className="mt-0.5 h-4 w-4 flex-shrink-0" />
              <span>
                Secrets (passwords, client secrets, tokens) are <strong>never</strong> included in the
                export. Re-enter them after importing a connection.
              </span>
            </div>
            <Button
              onClick={() => exportConnections.mutate()}
              disabled={exportConnections.isPending}
            >
              {exportConnections.isPending ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Download className="mr-2 h-4 w-4" />
              )}
              Export connections (no passwords)
            </Button>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
