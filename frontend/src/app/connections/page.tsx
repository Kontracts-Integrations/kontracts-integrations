"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { connectionsApi } from "@/lib/api";
import { MainLayout } from "@/components/layout/MainLayout";
import { TririgaConnectionForm } from "@/components/connections/TririgaConnectionForm";
import { KontractsConnectionForm } from "@/components/connections/KontractsConnectionForm";
import { GenericSourceConnectionForm } from "@/components/connections/GenericSourceConnectionForm";
import { ConnectionTestButton } from "@/components/connections/ConnectionTestButton";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "@/components/ui/toaster";
import { cn, formatRelativeTime } from "@/lib/utils";
import { Trash2, CheckCircle2, XCircle, AlertCircle, Loader2, Pencil, Plus } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { SOURCE_SYSTEM_LABELS } from "@/types";
import type { Connection, SourceSystemType } from "@/types";

const SOURCE_TYPES: SourceSystemType[] = ["tririga", "sap_re", "planon", "costar", "servicenow_wsd"];

function ConnectionCard({ conn }: { conn: Connection }) {
  const qc = useQueryClient();
  const [editOpen, setEditOpen] = useState(false);

  const deleteMutation = useMutation({
    mutationFn: () => connectionsApi.delete(conn.id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["connections"] });
      toast({ title: "Connection deleted" });
    },
    onError: (err: Error) => {
      toast({ title: "Delete failed", description: err.message, variant: "destructive" });
    },
  });

  const StatusIcon =
    conn.last_test_success === true ? CheckCircle2
    : conn.last_test_success === false ? XCircle
    : AlertCircle;

  const statusClass =
    conn.last_test_success === true ? "text-green-500"
    : conn.last_test_success === false ? "text-red-500"
    : "text-yellow-500";

  function EditForm() {
    if (conn.connection_type === "tririga") return <TririgaConnectionForm existing={conn} onSuccess={() => setEditOpen(false)} />;
    if (conn.connection_type === "kontracts") return <KontractsConnectionForm existing={conn} onSuccess={() => setEditOpen(false)} />;
    return <GenericSourceConnectionForm systemType={conn.connection_type as SourceSystemType} existing={conn} onSuccess={() => setEditOpen(false)} />;
  }

  const typeLabel = conn.connection_type === "kontracts"
    ? "Kontracts"
    : SOURCE_SYSTEM_LABELS[conn.connection_type as SourceSystemType] ?? conn.connection_type;

  return (
    <>
      <div className="flex items-center justify-between rounded-lg border p-4">
        <div className="flex items-center gap-4">
          <StatusIcon className={cn("h-5 w-5 flex-shrink-0", statusClass)} />
          <div>
            <div className="flex items-center gap-2">
              <p className="font-medium">{conn.name}</p>
              <span className="inline-flex rounded-full bg-muted px-2 py-0.5 text-xs text-muted-foreground">
                {typeLabel}
              </span>
              <span className={cn(
                "inline-flex rounded-full px-2 py-0.5 text-xs font-medium",
                conn.is_active ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300" : "bg-gray-100 text-gray-600"
              )}>
                {conn.is_active ? "Active" : "Inactive"}
              </span>
            </div>
            <p className="text-sm text-muted-foreground">{conn.base_url}</p>
            {conn.last_tested_at && (
              <p className="text-xs text-muted-foreground">
                Last tested {formatRelativeTime(conn.last_tested_at)}
                {conn.last_test_error && <span className="ml-2 text-red-500">{conn.last_test_error}</span>}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <ConnectionTestButton connectionId={conn.id} />
          <Button variant="ghost" size="sm" onClick={() => setEditOpen(true)} className="text-muted-foreground hover:text-foreground">
            <Pencil className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost" size="sm"
            onClick={() => { if (confirm(`Delete "${conn.name}"?`)) deleteMutation.mutate(); }}
            disabled={deleteMutation.isPending}
            className="text-muted-foreground hover:text-destructive"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Edit Connection — {conn.name}</DialogTitle></DialogHeader>
          <EditForm />
        </DialogContent>
      </Dialog>
    </>
  );
}

export default function ConnectionsPage() {
  const { data: connections, isLoading } = useQuery({
    queryKey: ["connections"],
    queryFn: () => connectionsApi.list(),
  });

  const [addSystemType, setAddSystemType] = useState<SourceSystemType>("tririga");
  const [showAddForm, setShowAddForm] = useState(false);

  const sourceConns = connections?.filter((c) => SOURCE_TYPES.includes(c.connection_type as SourceSystemType)) ?? [];
  const kontractsConns = connections?.filter((c) => c.connection_type === "kontracts") ?? [];

  function AddSourceForm() {
    if (addSystemType === "tririga") return <TririgaConnectionForm onSuccess={() => setShowAddForm(false)} />;
    return <GenericSourceConnectionForm systemType={addSystemType} onSuccess={() => setShowAddForm(false)} />;
  }

  return (
    <MainLayout title="Connections">
      <div className="mx-auto max-w-4xl space-y-6">
        <div>
          <h2 className="text-xl font-semibold">Connection Settings</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Configure source IWMS systems and the Kontracts target API. Credentials are encrypted at rest.
          </p>
        </div>

        <Tabs defaultValue="source">
          <TabsList>
            <TabsTrigger value="source">
              Source Systems (IWMS)
              {sourceConns.length > 0 && (
                <span className="ml-2 rounded-full bg-primary/20 px-1.5 py-0.5 text-xs">{sourceConns.length}</span>
              )}
            </TabsTrigger>
            <TabsTrigger value="kontracts">
              Kontracts (Target)
              {kontractsConns.length > 0 && (
                <span className="ml-2 rounded-full bg-primary/20 px-1.5 py-0.5 text-xs">{kontractsConns.length}</span>
              )}
            </TabsTrigger>
          </TabsList>

          <TabsContent value="source" className="mt-4 space-y-4">
            {isLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading...
              </div>
            ) : sourceConns.length > 0 ? (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Configured Connections</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {sourceConns.map((conn) => <ConnectionCard key={conn.id} conn={conn} />)}
                </CardContent>
              </Card>
            ) : null}

            {showAddForm ? (
              <Card>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle>Add Source Connection</CardTitle>
                      <CardDescription>Connect an IWMS source system to pull data from.</CardDescription>
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => setShowAddForm(false)}>Cancel</Button>
                  </div>
                  <div className="pt-2">
                    <Select value={addSystemType} onValueChange={(v) => setAddSystemType(v as SourceSystemType)}>
                      <SelectTrigger className="w-56">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {SOURCE_TYPES.map((t) => (
                          <SelectItem key={t} value={t}>{SOURCE_SYSTEM_LABELS[t]}</SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </CardHeader>
                <CardContent>
                  <AddSourceForm />
                </CardContent>
              </Card>
            ) : (
              <Button variant="outline" onClick={() => setShowAddForm(true)}>
                <Plus className="mr-2 h-4 w-4" /> Add Source Connection
              </Button>
            )}
          </TabsContent>

          <TabsContent value="kontracts" className="mt-4 space-y-4">
            {isLoading ? (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-4 w-4 animate-spin" /> Loading...
              </div>
            ) : kontractsConns.length > 0 ? (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm font-medium text-muted-foreground">Existing Connections</CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {kontractsConns.map((conn) => <ConnectionCard key={conn.id} conn={conn} />)}
                </CardContent>
              </Card>
            ) : null}
            <Card>
              <CardHeader>
                <CardTitle>Configure Kontracts Connection</CardTitle>
                <CardDescription>Connect to the Kontracts REST API using Auth0 client credentials OAuth2 flow.</CardDescription>
              </CardHeader>
              <CardContent><KontractsConnectionForm /></CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  );
}
