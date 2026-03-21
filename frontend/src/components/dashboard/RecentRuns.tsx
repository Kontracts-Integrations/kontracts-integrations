"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { runsApi } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, formatRelativeTime, formatDuration, getStatusColor } from "@/lib/utils";
import { Loader2, ArrowRight } from "lucide-react";
import type { SyncRun } from "@/types";

function RunRow({ run }: { run: SyncRun }) {
  return (
    <div className="flex items-center justify-between py-3">
      <div className="flex items-center gap-3">
        <span
          className={cn(
            "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold",
            getStatusColor(run.status)
          )}
        >
          {run.status}
        </span>
        <div>
          <p className="text-sm font-medium">Run #{run.id}</p>
          <p className="text-xs text-muted-foreground">
            {run.total_records ?? "?"} records · {formatRelativeTime(run.created_at)}
          </p>
        </div>
      </div>
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        {run.status === "completed" || run.status === "failed" ? (
          <>
            <span className="text-green-600 dark:text-green-400">{run.success_count} ok</span>
            {run.failed_count > 0 && (
              <span className="text-red-600 dark:text-red-400">{run.failed_count} failed</span>
            )}
            <span>{formatDuration(run.started_at, run.completed_at)}</span>
          </>
        ) : null}
        <Link href={`/runs`}>
          <ArrowRight className="h-4 w-4 hover:text-foreground" />
        </Link>
      </div>
    </div>
  );
}

export function RecentRuns() {
  const { data: runs, isLoading } = useQuery({
    queryKey: ["runs", "recent"],
    queryFn: () => runsApi.list({ limit: 8 }),
    refetchInterval: 10000,
  });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-base">Recent Sync Runs</CardTitle>
        <Button variant="ghost" size="sm" asChild>
          <Link href="/runs">View all</Link>
        </Button>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : !runs?.length ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            No sync runs yet. Create a mapping and trigger your first run.
          </div>
        ) : (
          <div className="divide-y">
            {runs.map((run) => (
              <RunRow key={run.id} run={run} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
