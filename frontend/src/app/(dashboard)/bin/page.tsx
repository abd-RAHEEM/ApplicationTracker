"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiGet, apiClient, getApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { RefreshCw, Trash2, Inbox } from "lucide-react";
import { toast } from "sonner";

interface BinItem {
  id: string;
  company_name: string;
  role_title: string;
  deleted_at: string | null;
  purge_after: string | null;
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function daysRemaining(purgeAfter: string | null): { label: string; urgent: boolean } {
  if (!purgeAfter) return { label: "—", urgent: false };
  const diff = new Date(purgeAfter).getTime() - Date.now();
  const days = Math.ceil(diff / 86400000);
  if (days <= 0) return { label: "Due for purge", urgent: true };
  if (days === 1) return { label: "1 day left", urgent: true };
  return { label: `${days} days left`, urgent: days <= 3 };
}

export default function BinPage() {
  const queryClient = useQueryClient();
  const [purgeTarget, setPurgeTarget] = useState<BinItem | null>(null);
  const [actionId, setActionId] = useState<string | null>(null);

  const { data, isLoading } = useQuery<BinItem[]>({
    queryKey: ["bin"],
    queryFn: () => apiGet<BinItem[]>("/applications/bin/list"),
    staleTime: 30 * 1000,
  });

  const restoreMutation = useMutation({
    mutationFn: (id: string) => apiClient.post(`/applications/${id}/restore`),
    onMutate: (id) => setActionId(id),
    onSuccess: () => {
      toast.success("Application restored successfully");
      queryClient.invalidateQueries({ queryKey: ["bin"] });
      queryClient.invalidateQueries({ queryKey: ["applications"] });
    },
    onError: (error: unknown) => {
      const apiError = getApiError(error);
      toast.error(apiError.message || "Failed to restore application");
    },
    onSettled: () => setActionId(null),
  });

  const purgeMutation = useMutation({
    mutationFn: (id: string) => apiClient.delete(`/applications/bin/${id}/purge`),
    onMutate: (id) => setActionId(id),
    onSuccess: () => {
      toast.success("Application permanently deleted");
      queryClient.invalidateQueries({ queryKey: ["bin"] });
      setPurgeTarget(null);
    },
    onError: (error: unknown) => {
      const apiError = getApiError(error);
      toast.error(apiError.message || "Failed to purge application");
      setPurgeTarget(null);
    },
    onSettled: () => setActionId(null),
  });

  const items = data ?? [];

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Bin</h2>
        <p className="text-muted-foreground">
          Applications here will be permanently deleted after 15 days.
        </p>
      </div>

      <Card>
        {items.length > 0 && (
          <CardHeader className="py-3 border-b">
            <CardTitle className="text-sm font-normal text-muted-foreground">
              {items.length} item{items.length !== 1 ? "s" : ""} in bin
            </CardTitle>
          </CardHeader>
        )}
        <CardContent className="pt-0">
          <div className="rounded-md border mt-4">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50 transition-colors">
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Company</th>
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Role</th>
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Deleted</th>
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Time Remaining</th>
                  <th className="h-10 px-4 text-right align-middle font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  [...Array(3)].map((_, i) => (
                    <tr key={i} className="border-b">
                      <td className="p-4"><Skeleton className="h-4 w-24" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-32" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-20" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-16" /></td>
                      <td className="p-4 text-right">
                        <div className="flex justify-end gap-2">
                          <Skeleton className="h-7 w-20" />
                          <Skeleton className="h-7 w-16" />
                        </div>
                      </td>
                    </tr>
                  ))
                ) : items.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-12 text-center">
                      <div className="flex flex-col items-center gap-2 text-muted-foreground">
                        <Inbox className="h-8 w-8 opacity-40" />
                        <p>Bin is empty</p>
                        <p className="text-xs">Deleted applications will appear here.</p>
                      </div>
                    </td>
                  </tr>
                ) : (
                  items.map((item) => {
                    const remaining = daysRemaining(item.purge_after);
                    const isActing = actionId === item.id;
                    return (
                      <tr key={item.id} className="border-b transition-colors hover:bg-muted/50">
                        <td className="p-4 align-middle font-medium">{item.company_name}</td>
                        <td className="p-4 align-middle text-muted-foreground">{item.role_title}</td>
                        <td className="p-4 align-middle text-muted-foreground text-xs">
                          {formatDate(item.deleted_at)}
                        </td>
                        <td className={`p-4 align-middle font-medium text-xs ${remaining.urgent ? "text-destructive" : "text-muted-foreground"}`}>
                          {remaining.label}
                        </td>
                        <td className="p-4 align-middle text-right">
                          <div className="flex justify-end gap-2">
                            <Button
                              id={`restore-${item.id}`}
                              variant="outline"
                              size="sm"
                              className="gap-1 h-7"
                              disabled={isActing}
                              onClick={() => restoreMutation.mutate(item.id)}
                            >
                              <RefreshCw className={`h-3 w-3 ${isActing && restoreMutation.isPending ? "animate-spin" : ""}`} />
                              {isActing && restoreMutation.isPending ? "Restoring..." : "Restore"}
                            </Button>
                            <Button
                              id={`purge-${item.id}`}
                              variant="destructive"
                              size="sm"
                              className="gap-1 h-7"
                              disabled={isActing}
                              onClick={() => setPurgeTarget(item)}
                            >
                              <Trash2 className="h-3 w-3" />
                              Purge
                            </Button>
                          </div>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Purge Confirmation Dialog */}
      <AlertDialog open={!!purgeTarget} onOpenChange={(open) => { if (!open) setPurgeTarget(null); }}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Permanently delete this application?</AlertDialogTitle>
            <AlertDialogDescription>
              <strong>{purgeTarget?.company_name}</strong> — {purgeTarget?.role_title}
              <br /><br />
              This will permanently remove the application and all its history. This action{" "}
              <strong>cannot be undone</strong>.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              onClick={() => purgeTarget && purgeMutation.mutate(purgeTarget.id)}
            >
              Yes, permanently delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
