"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { connectionsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/toaster";
import { Loader2, Eye, EyeOff } from "lucide-react";
import type { Connection } from "@/types";

interface FormValues {
  name: string;
  base_url: string;
  auth0_domain: string;
  client_id: string;
  client_secret: string;
  audience: string;
}

interface Props {
  existing?: Connection;
  onSuccess?: () => void;
}

export function KontractsConnectionForm({ existing, onSuccess }: Props) {
  const qc = useQueryClient();
  const [showSecret, setShowSecret] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: {
      name: existing?.name ?? "Kontracts Production",
      base_url: existing?.base_url ?? "https://api-dev.kontracts.pro",
      auth0_domain: "",
      client_id: "",
      client_secret: "",
      audience: "https://api-dev.kontracts.pro",
    },
  });

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const payload = {
        name: values.name,
        connection_type: "kontracts" as const,
        base_url: values.base_url,
        credentials: {
          auth0_domain: values.auth0_domain,
          client_id: values.client_id,
          client_secret: values.client_secret,
          audience: values.audience,
        },
      };
      if (existing) {
        return connectionsApi.update(existing.id, {
          name: values.name,
          base_url: values.base_url,
          credentials: payload.credentials,
        });
      }
      return connectionsApi.create(payload);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["connections"] });
      toast({
        title: existing ? "Connection updated" : "Connection created",
        description: "Kontracts connection saved successfully.",
      });
      onSuccess?.();
    },
    onError: (err: Error) => {
      toast({ title: "Save failed", description: err.message, variant: "destructive" });
    },
  });

  return (
    <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
      <div className="space-y-2">
        <Label>Connection Name</Label>
        <Input
          placeholder="Kontracts Production"
          {...register("name", { required: "Name is required" })}
        />
      </div>

      <div className="space-y-2">
        <Label>Base URL</Label>
        <Input
          placeholder="https://api-dev.kontracts.pro"
          {...register("base_url", { required: "Base URL is required" })}
        />
      </div>

      <div className="space-y-2">
        <Label>Auth0 Domain</Label>
        <Input
          placeholder="your-tenant.auth0.com"
          {...register("auth0_domain", { required: !existing })}
        />
        <p className="text-xs text-muted-foreground">
          Your Auth0 tenant domain (without https://)
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Client ID</Label>
          <Input
            placeholder="your_client_id"
            {...register("client_id", { required: !existing })}
          />
        </div>
        <div className="space-y-2">
          <Label>Audience</Label>
          <Input
            placeholder="https://api-dev.kontracts.pro"
            {...register("audience", { required: !existing })}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label>Client Secret</Label>
        <div className="relative">
          <Input
            type={showSecret ? "text" : "password"}
            placeholder="your_client_secret"
            {...register("client_secret", { required: !existing })}
            className="pr-10"
          />
          <button
            type="button"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            onClick={() => setShowSecret((s) => !s)}
          >
            {showSecret ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        {existing && (
          <p className="text-xs text-muted-foreground">Leave blank to keep existing secret</p>
        )}
      </div>

      <Button type="submit" className="w-full" disabled={mutation.isPending}>
        {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {existing ? "Update Connection" : "Save Connection"}
      </Button>
    </form>
  );
}
