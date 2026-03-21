"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { connectionsApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { cn, formatRelativeTime } from "@/lib/utils";
import { CheckCircle2, XCircle, AlertCircle, RefreshCw } from "lucide-react";
import { toast } from "@/components/ui/toaster";
import type { Connection } from "@/types";

function ConnStatus({ conn }: { conn: Connection }) {
  const qc = useQueryClient();

  const testMutation = useMutation({
    mutationFn: () => connectionsApi.test(conn.id),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["connections"] });
      toast({
        title: result.success ? "Connection OK" : "Connection failed",
        description: result.message,
        variant: result.success ? "default" : "destructive",
      });
    },
    onError: (err: Error) => {
      toast({ title: "Test failed", description: err.message, variant: "destructive" });
    },
  });

  const success = conn.last_test_success;
  const Icon =
    success === true
      ? CheckCircle2
      : success === false
      ? XCircle
      : AlertCircle;

  const iconClass =
    success === true
      ? "text-green-500"
      : success === false
      ? "text-red-500"
      : "text-yellow-500";

  return (
    <div className="flex items-center justify-between rounded-lg border p-3">
      <div className="flex items-center gap-3">
        <Icon className={cn("h-5 w-5", iconClass)} />
        <div>
          <p className="text-sm font-medium">{conn.name}</p>
          <p className="text-xs text-muted-foreground">
            {conn.connection_type === "tririga" ? "TRIRIGA SOAP" : "Kontracts REST"}
            {conn.last_tested_at
              ? ` · Tested ${formatRelativeTime(conn.last_tested_at)}`
              : " · Never tested"}
          </p>
          {conn.last_test_error && (
            <p className="mt-0.5 text-xs text-red-500">{conn.last_test_error}</p>
          )}
        </div>
      </div>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => testMutation.mutate()}
        disabled={testMutation.isPending}
      >
        <RefreshCw
          className={cn("h-4 w-4", testMutation.isPending && "animate-spin")}
        />
        <span className="ml-1 hidden sm:inline">Test</span>
      </Button>
    </div>
  );
}

export function ConnectionStatus() {
  const { data: connections, isLoading } = useQuery({
    queryKey: ["connections"],
    queryFn: () => connectionsApi.list(),
  });

  const active = connections?.filter((c) => c.is_active) ?? [];

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">Connection Status</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {isLoading ? (
          <p className="text-sm text-muted-foreground">Loading connections...</p>
        ) : !active.length ? (
          <p className="text-sm text-muted-foreground">
            No active connections. Configure connections to get started.
          </p>
        ) : (
          active.map((conn) => <ConnStatus key={conn.id} conn={conn} />)
        )}
      </CardContent>
    </Card>
  );
}
