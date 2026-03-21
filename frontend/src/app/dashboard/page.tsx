"use client";

import { useQuery } from "@tanstack/react-query";
import { MainLayout } from "@/components/layout/MainLayout";
import { StatsCard } from "@/components/dashboard/StatsCard";
import { RecentRuns } from "@/components/dashboard/RecentRuns";
import { ConnectionStatus } from "@/components/dashboard/ConnectionStatus";
import { runsApi, mappingsApi, connectionsApi } from "@/lib/api";
import { GitBranch, Play, CheckCircle2, XCircle, Plug, Activity } from "lucide-react";

export default function DashboardPage() {
  const { data: runs } = useQuery({
    queryKey: ["runs", "all"],
    queryFn: () => runsApi.list({ limit: 200 }),
    refetchInterval: 15000,
  });

  const { data: mappings } = useQuery({
    queryKey: ["mappings"],
    queryFn: () => mappingsApi.list(),
  });

  const { data: connections } = useQuery({
    queryKey: ["connections"],
    queryFn: () => connectionsApi.list(),
  });

  const totalRuns = runs?.length ?? 0;
  const successRuns = runs?.filter((r) => r.status === "completed").length ?? 0;
  const failedRuns = runs?.filter((r) => r.status === "failed").length ?? 0;
  const activeMappings = mappings?.filter((m) => m.is_active).length ?? 0;
  const activeConnections = connections?.filter((c) => c.is_active && c.last_test_success).length ?? 0;

  const totalRecordsProcessed =
    runs?.reduce((sum, r) => sum + (r.success_count ?? 0), 0) ?? 0;

  return (
    <MainLayout title="Dashboard">
      <div className="space-y-6">
        {/* Stats grid */}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <StatsCard
            title="Total Runs"
            value={totalRuns}
            subtitle="All time"
            icon={Play}
            className="col-span-1"
          />
          <StatsCard
            title="Successful"
            value={successRuns}
            subtitle={totalRuns ? `${Math.round((successRuns / totalRuns) * 100)}% success rate` : "No runs yet"}
            icon={CheckCircle2}
            trend="up"
            className="col-span-1"
          />
          <StatsCard
            title="Failed"
            value={failedRuns}
            subtitle="Need attention"
            icon={XCircle}
            trend={failedRuns > 0 ? "down" : "neutral"}
            className="col-span-1"
          />
          <StatsCard
            title="Active Mappings"
            value={activeMappings}
            subtitle={`${mappings?.length ?? 0} total`}
            icon={GitBranch}
            className="col-span-1"
          />
          <StatsCard
            title="Connections"
            value={activeConnections}
            subtitle={`${connections?.length ?? 0} configured`}
            icon={Plug}
            className="col-span-1"
          />
          <StatsCard
            title="Records Synced"
            value={totalRecordsProcessed.toLocaleString()}
            subtitle="Successfully pushed"
            icon={Activity}
            trend="up"
            className="col-span-1"
          />
        </div>

        {/* Main content */}
        <div className="grid gap-6 lg:grid-cols-2">
          <RecentRuns />
          <ConnectionStatus />
        </div>
      </div>
    </MainLayout>
  );
}
