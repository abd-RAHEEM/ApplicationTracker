"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { apiGet, apiClient, getApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ArrowLeft, Clock, Info, Trash2 } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

interface Application {
  id: string;
  company_name: string;
  role_title: string;
  current_status: string;
  applied_at: string | null;
  last_activity_at: string;
  confidence_scores: Record<string, number> | null;
}

interface TimelineEvent {
  id: string;
  status: string;
  source: string;
  detected_at: string;
  notes: string | null;
  confidence_scores: Record<string, number> | null;
}

const STATUS_COLORS: Record<string, string> = {
  applied: "bg-blue-100 text-blue-800",
  assessment: "bg-yellow-100 text-yellow-800",
  interview: "bg-purple-100 text-purple-800",
  offer: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  pending: "bg-gray-100 text-gray-800",
};

const SOURCE_LABELS: Record<string, string> = {
  gmail_parse: "Gmail Parse",
  manual_update: "Manual Update",
  initial_import: "Initial Import",
};

function formatDateTime(dateStr: string): string {
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  const hours = Math.floor(diff / 3600000);
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  return "recently";
}

export default function ApplicationDetailPage({ params }: { params: { id: string } }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { id } = params;

  const { data: app, isLoading: loadingApp } = useQuery<Application>({
    queryKey: ["application", id],
    queryFn: async () => {
      // Fetch from list endpoint filtered — or use the timeline to get app details
      const list = await apiGet<{ items: Application[] }>(`/applications?limit=1&offset=0`);
      // Since there's no single-app GET endpoint, get from the list query cache
      // or fall back to a client-side search. We'll use a dedicated approach:
      const allApps = queryClient.getQueryData<{ items: Application[] }>(["applications", "", "", 0]);
      const cached = allApps?.items.find((a) => a.id === id);
      if (cached) return cached;
      // If not cached, fetch and find
      const fullList = await apiGet<{ items: Application[] }>(`/applications?limit=100&offset=0`);
      const found = fullList.items.find((a) => a.id === id);
      if (!found) throw new Error("Application not found");
      return found;
    },
    staleTime: 60 * 1000,
  });

  const { data: timeline, isLoading: loadingTimeline } = useQuery<TimelineEvent[]>({
    queryKey: ["application-timeline", id],
    queryFn: () => apiGet<TimelineEvent[]>(`/applications/${id}/timeline`),
    staleTime: 60 * 1000,
  });

  const deleteMutation = useMutation({
    mutationFn: () => apiClient.delete(`/applications/${id}`),
    onSuccess: () => {
      toast.success("Application moved to bin");
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
      router.push("/applications");
    },
    onError: (error: unknown) => {
      const apiError = getApiError(error);
      toast.error(apiError.message || "Failed to delete application");
    },
  });

  const isLoading = loadingApp || loadingTimeline;

  return (
    <div className="flex flex-col gap-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/applications">
          <Button variant="outline" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div className="flex-1 min-w-0">
          {isLoading ? (
            <>
              <Skeleton className="h-8 w-64 mb-1" />
              <Skeleton className="h-4 w-32" />
            </>
          ) : (
            <>
              <h2 className="text-3xl font-bold tracking-tight truncate">
                {app?.company_name} — {app?.role_title}
              </h2>
              <p className="text-muted-foreground text-sm">
                Last updated {app?.last_activity_at ? timeAgo(app.last_activity_at) : "—"}
              </p>
            </>
          )}
        </div>
        {app && (
          <div className="ml-auto flex items-center gap-2 shrink-0">
            <span
              className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-semibold capitalize ${
                STATUS_COLORS[app.current_status] ?? STATUS_COLORS.pending
              }`}
            >
              {app.current_status}
            </span>
            <Button
              id={`delete-app-${id}`}
              variant="destructive"
              size="sm"
              className="gap-1"
              disabled={deleteMutation.isPending}
              onClick={() => deleteMutation.mutate()}
            >
              <Trash2 className="h-3.5 w-3.5" />
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </div>
        )}
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        {/* Timeline */}
        <Card className="md:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              Status Timeline
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loadingTimeline ? (
              <div className="space-y-4">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="flex gap-4">
                    <Skeleton className="h-10 w-10 rounded-full shrink-0" />
                    <div className="flex-1 space-y-2">
                      <Skeleton className="h-4 w-32" />
                      <Skeleton className="h-3 w-48" />
                    </div>
                  </div>
                ))}
              </div>
            ) : !timeline || timeline.length === 0 ? (
              <div className="flex items-center justify-center h-24 text-sm text-muted-foreground">
                No timeline events yet.
              </div>
            ) : (
              <div className="space-y-6 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-muted before:to-transparent">
                {timeline.map((event) => (
                  <div key={event.id} className="relative flex items-start gap-4">
                    <div
                      className={`flex items-center justify-center w-10 h-10 rounded-full border border-background shrink-0 shadow text-xs font-bold capitalize ${
                        STATUS_COLORS[event.status] ?? STATUS_COLORS.pending
                      }`}
                    >
                      {event.status.slice(0, 2).toUpperCase()}
                    </div>
                    <div className="flex-1 p-3 rounded-lg border bg-card shadow-sm">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold capitalize">{event.status}</span>
                        <time className="text-xs text-muted-foreground">
                          {formatDateTime(event.detected_at)}
                        </time>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        Source: {SOURCE_LABELS[event.source] ?? event.source}
                      </p>
                      {event.notes && (
                        <p className="text-sm mt-1 text-muted-foreground italic">{event.notes}</p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Side Panel */}
        <div className="space-y-6">
          {/* Parser Confidence */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-sm">
                <Info className="h-4 w-4" />
                Parser Confidence
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              {loadingApp ? (
                <>
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                </>
              ) : app?.confidence_scores && Object.keys(app.confidence_scores).length > 0 ? (
                Object.entries(app.confidence_scores).map(([key, value]) => {
                  const pct = Math.round(Number(value) * 100);
                  return (
                    <div key={key} className="space-y-1">
                      <div className="flex justify-between">
                        <span className="text-muted-foreground capitalize">{key.replace(/_/g, " ")}</span>
                        <span
                          className={`font-medium ${
                            pct >= 80 ? "text-green-600" : pct >= 60 ? "text-amber-500" : "text-red-500"
                          }`}
                        >
                          {pct}%
                        </span>
                      </div>
                      <div className="h-1.5 w-full rounded-full bg-muted overflow-hidden">
                        <div
                          className={`h-full rounded-full ${
                            pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-amber-500" : "bg-red-500"
                          }`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="text-muted-foreground">No confidence scores available.</p>
              )}
            </CardContent>
          </Card>

          {/* Application Info */}
          {app && (
            <Card>
              <CardHeader>
                <CardTitle className="text-sm">Application Info</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Company</span>
                  <span className="font-medium">{app.company_name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Role</span>
                  <span className="font-medium">{app.role_title}</span>
                </div>
                {app.applied_at && (
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Applied</span>
                    <span className="font-medium">
                      {new Date(app.applied_at).toLocaleDateString("en-US", {
                        month: "short",
                        day: "numeric",
                        year: "numeric",
                      })}
                    </span>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
