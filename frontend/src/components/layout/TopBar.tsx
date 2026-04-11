"use client";

import { useTheme } from "next-themes";
import { Sun, Moon, Workflow, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import { connectionsApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import { useEffect, useState } from "react";
import { useSession, signOut } from "next-auth/react";
import Image from "next/image";

function ConnectionStatusBadge({
  label,
  success,
  loading,
}: {
  label: string;
  success: boolean | null;
  loading: boolean;
}) {
  let statusClass = "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400";
  let dot = "bg-gray-400";
  let text = "Not configured";

  if (loading) {
    text = "Checking...";
  } else if (success === true) {
    statusClass = "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300";
    dot = "bg-green-500";
    text = "Connected";
  } else if (success === false) {
    statusClass = "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300";
    dot = "bg-red-500";
    text = "Error";
  }

  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium", statusClass)}>
      <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />
      {label}: {text}
    </span>
  );
}

export function TopBar() {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const { data: session } = useSession();

  const { data: connections, isLoading } = useQuery({
    queryKey: ["connections"],
    queryFn: () => connectionsApi.list(),
    refetchInterval: 60000,
  });

  const tririgaConn = connections?.find((c) => c.connection_type === "tririga");
  const kontractsConn = connections?.find((c) => c.connection_type === "kontracts");

  const cycleTheme = () => {
    if (theme === "light") setTheme("dark");
    else setTheme("light");
  };

  const ThemeIcon = !mounted ? Sun : theme === "light" ? Sun : Moon;

  return (
    <div className="flex h-14 w-full items-center justify-between border-b bg-card px-6 flex-shrink-0">
      <div className="flex items-center gap-2">
        <Workflow className="h-6 w-6 text-primary" />
        <span className="text-xl font-bold">Kontracts Integration</span>
      </div>
      <div className="flex items-center gap-3">
        <ConnectionStatusBadge
          label="TRIRIGA"
          success={tririgaConn?.last_test_success ?? null}
          loading={isLoading}
        />
        <ConnectionStatusBadge
          label="Kontracts"
          success={kontractsConn?.last_test_success ?? null}
          loading={isLoading}
        />
        <Button variant="ghost" size="icon" onClick={cycleTheme} title="Toggle theme">
          <ThemeIcon className="h-4 w-4" />
        </Button>
        {session?.user && (
          <div className="flex items-center gap-2 pl-2 border-l">
            {session.user.image ? (
              <Image
                src={session.user.image}
                alt={session.user.name ?? "User"}
                width={28}
                height={28}
                className="rounded-full"
              />
            ) : (
              <div className="h-7 w-7 rounded-full bg-primary/20 flex items-center justify-center text-xs font-medium">
                {session.user.name?.[0] ?? "U"}
              </div>
            )}
            <span className="text-sm font-medium hidden sm:block">{session.user.name}</span>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => signOut({ callbackUrl: "/login" })}
              title="Sign out"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
