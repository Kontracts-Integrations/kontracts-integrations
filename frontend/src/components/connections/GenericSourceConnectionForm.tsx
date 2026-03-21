"use client";

import { useForm } from "react-hook-form";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { connectionsApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/toaster";
import { Loader2 } from "lucide-react";
import { SOURCE_SYSTEM_LABELS } from "@/types";
import type { Connection, SourceSystemType } from "@/types";

interface FormValues {
  name: string;
  base_url: string;
  api_key: string;
  username: string;
  password: string;
}

interface Props {
  systemType: SourceSystemType;
  existing?: Connection;
  onSuccess?: () => void;
}

export function GenericSourceConnectionForm({ systemType, existing, onSuccess }: Props) {
  const qc = useQueryClient();
  const label = SOURCE_SYSTEM_LABELS[systemType];

  const { register, handleSubmit, formState: { errors } } = useForm<FormValues>({
    defaultValues: {
      name: existing?.name ?? `${label} Connection`,
      base_url: existing?.base_url ?? "",
      api_key: "",
      username: "",
      password: "",
    },
  });

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const credentials: Record<string, string> = {};
      if (values.api_key) credentials.api_key = values.api_key;
      if (values.username) credentials.username = values.username;
      if (values.password) credentials.password = values.password;

      if (existing) {
        return connectionsApi.update(existing.id, {
          name: values.name,
          base_url: values.base_url,
          credentials,
        });
      }
      return connectionsApi.create({
        name: values.name,
        connection_type: systemType,
        base_url: values.base_url,
        credentials,
      });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["connections"] });
      toast({ title: existing ? "Connection updated" : "Connection created", description: `${label} connection saved.` });
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
        <Input placeholder={`${label} Production`} {...register("name", { required: "Name is required" })} />
        {errors.name && <p className="text-xs text-red-500">{errors.name.message}</p>}
      </div>

      <div className="space-y-2">
        <Label>Base URL</Label>
        <Input placeholder="https://your-instance.example.com" {...register("base_url", { required: "Base URL is required" })} />
      </div>

      <div className="space-y-2">
        <Label>API Key <span className="text-muted-foreground text-xs">(if applicable)</span></Label>
        <Input placeholder="sk-..." {...register("api_key")} />
        {existing && <p className="text-xs text-muted-foreground">Leave blank to keep existing</p>}
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label>Username <span className="text-muted-foreground text-xs">(if applicable)</span></Label>
          <Input placeholder="service_account" autoComplete="username" {...register("username")} />
        </div>
        <div className="space-y-2">
          <Label>Password <span className="text-muted-foreground text-xs">(if applicable)</span></Label>
          <Input type="password" autoComplete="current-password" {...register("password")} />
        </div>
      </div>

      <div className="rounded-md border border-yellow-200 bg-yellow-50 p-3 text-xs text-yellow-800 dark:border-yellow-800 dark:bg-yellow-950 dark:text-yellow-200">
        <strong>{label}</strong> integration is currently in preview. The connector will validate the connection but full data sync is not yet implemented.
      </div>

      <Button type="submit" className="w-full" disabled={mutation.isPending}>
        {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {existing ? "Update Connection" : "Save Connection"}
      </Button>
    </form>
  );
}
