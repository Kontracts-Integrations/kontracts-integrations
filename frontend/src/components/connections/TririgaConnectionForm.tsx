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
  username: string;
  password: string;
  wsdl_path: string;
}

interface Props {
  existing?: Connection;
  onSuccess?: () => void;
}

export function TririgaConnectionForm({ existing, onSuccess }: Props) {
  const qc = useQueryClient();
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormValues>({
    defaultValues: {
      name: existing?.name ?? "TRIRIGA Production",
      base_url: existing?.base_url ?? "https://verizon.tririga.com",
      username: "",
      password: "",
      wsdl_path: "/ws/TririgaWS?wsdl",
    },
  });

  const mutation = useMutation({
    mutationFn: async (values: FormValues) => {
      const payload = {
        name: values.name,
        connection_type: "tririga" as const,
        base_url: values.base_url,
        credentials: {
          username: values.username,
          password: values.password,
          wsdl_path: values.wsdl_path,
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
        description: "TRIRIGA connection saved successfully.",
      });
      onSuccess?.();
    },
    onError: (err: Error) => {
      toast({
        title: "Save failed",
        description: err.message,
        variant: "destructive",
      });
    },
  });

  return (
    <form onSubmit={handleSubmit((v) => mutation.mutate(v))} className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="tririga-name">Connection Name</Label>
        <Input
          id="tririga-name"
          placeholder="TRIRIGA Production"
          {...register("name", { required: "Name is required" })}
        />
        {errors.name && <p className="text-xs text-red-500">{errors.name.message}</p>}
      </div>

      <div className="space-y-2">
        <Label htmlFor="tririga-url">Base URL</Label>
        <Input
          id="tririga-url"
          placeholder="https://verizon.tririga.com"
          {...register("base_url", { required: "Base URL is required" })}
        />
        <p className="text-xs text-muted-foreground">
          The root URL of your TRIRIGA instance (no trailing slash)
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="tririga-wsdl">WSDL Path</Label>
        <Input
          id="tririga-wsdl"
          placeholder="/ws/TririgaWS?wsdl"
          {...register("wsdl_path")}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="tririga-user">Username</Label>
        <Input
          id="tririga-user"
          placeholder="service_account@company.com"
          autoComplete="username"
          {...register("username", { required: !existing })}
        />
        {existing && (
          <p className="text-xs text-muted-foreground">Leave blank to keep existing username</p>
        )}
      </div>

      <div className="space-y-2">
        <Label htmlFor="tririga-pass">Password</Label>
        <div className="relative">
          <Input
            id="tririga-pass"
            type={showPassword ? "text" : "password"}
            autoComplete="current-password"
            {...register("password", { required: !existing })}
            className="pr-10"
          />
          <button
            type="button"
            className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
            onClick={() => setShowPassword((s) => !s)}
          >
            {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
        {existing && (
          <p className="text-xs text-muted-foreground">Leave blank to keep existing password</p>
        )}
      </div>

      <Button type="submit" className="w-full" disabled={mutation.isPending}>
        {mutation.isPending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        {existing ? "Update Connection" : "Save Connection"}
      </Button>
    </form>
  );
}
