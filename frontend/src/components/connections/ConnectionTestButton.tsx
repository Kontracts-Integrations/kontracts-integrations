"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { connectionsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/toaster";
import { Loader2, Zap } from "lucide-react";

interface Props {
  connectionId: number;
  variant?: "default" | "outline" | "ghost";
  size?: "default" | "sm" | "lg";
}

export function ConnectionTestButton({
  connectionId,
  variant = "outline",
  size = "sm",
}: Props) {
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => connectionsApi.test(connectionId),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ["connections"] });
      toast({
        title: result.success ? "Connection successful" : "Connection failed",
        description: result.message,
        variant: result.success ? "default" : "destructive",
      });
    },
    onError: (err: Error) => {
      toast({ title: "Test error", description: err.message, variant: "destructive" });
    },
  });

  return (
    <Button
      variant={variant}
      size={size}
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending}
    >
      {mutation.isPending ? (
        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
      ) : (
        <Zap className="mr-2 h-4 w-4" />
      )}
      Test Connection
    </Button>
  );
}
