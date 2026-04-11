"use client";

import { useParams, useRouter } from "next/navigation";
import { useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { mappingsApi } from "@/lib/api";
import { MainLayout } from "@/components/layout/MainLayout";
import { MappingBuilder } from "@/components/mappings/MappingBuilder";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/toaster";
import { Loader2, ArrowLeft, Save } from "lucide-react";
import Link from "next/link";
import type { MappingTemplateUpdate } from "@/types";

export default function MappingDetailPage() {
  const params = useParams();
  const router = useRouter();
  const qc = useQueryClient();
  const id = parseInt(params.id as string);

  const saveRef = useRef<(() => void) | null>(null);

  const { data: template, isLoading, error } = useQuery({
    queryKey: ["mapping", id],
    queryFn: () => mappingsApi.get(id),
    enabled: !!id,
  });

  const saveMutation = useMutation({
    mutationFn: (updates: MappingTemplateUpdate) => mappingsApi.update(id, updates),
    onSuccess: (updated) => {
      qc.setQueryData(["mapping", id], updated);
      qc.invalidateQueries({ queryKey: ["mappings"] });
      toast({
        title: "Mapping saved",
        description: `Version ${updated.current_version?.version_number} created`,
      });
    },
    onError: (err: Error) => {
      toast({ title: "Save failed", description: err.message, variant: "destructive" });
    },
  });

  if (isLoading) {
    return (
      <MainLayout title="Loading...">
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </MainLayout>
    );
  }

  if (error || !template) {
    return (
      <MainLayout title="Not Found">
        <div className="py-20 text-center">
          <p className="text-muted-foreground">Mapping template not found.</p>
          <Button asChild className="mt-4">
            <Link href="/mappings">Back to Mappings</Link>
          </Button>
        </div>
      </MainLayout>
    );
  }

  return (
    <MainLayout title={template.name}>
      <div className="flex min-h-0 flex-1 flex-col gap-4">
        <div className="flex items-center">
          <Button variant="outline" size="sm" asChild>
            <Link href="/mappings">
              <ArrowLeft className="mr-1 h-4 w-4" />
              Back
            </Link>
          </Button>
        </div>

        <MappingBuilder
          template={template}
          onSave={(updates) => void saveMutation.mutateAsync(updates)}
          saving={saveMutation.isPending}
          saveRef={saveRef}
        />
      </div>
    </MainLayout>
  );
}
