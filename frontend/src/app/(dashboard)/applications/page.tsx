"use client";

import { useState, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { apiGet, apiDelete, getApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { Search, Trash2, Eye, ChevronLeft, ChevronRight } from "lucide-react";
import { toast } from "sonner";

interface Application {
  id: string;
  company_name: string;
  role_title: string;
  current_status: string;
  applied_at: string | null;
  last_activity_at: string;
}

interface ApplicationsResponse {
  items: Application[];
  limit: number;
  offset: number;
}

const STATUS_OPTIONS = [
  { value: "", label: "All Statuses" },
  { value: "applied", label: "Applied" },
  { value: "assessment", label: "Assessment" },
  { value: "interview", label: "Interview" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" },
  { value: "pending", label: "Pending" },
];

const STATUS_COLORS: Record<string, string> = {
  applied: "bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400",
  assessment: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400",
  interview: "bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400",
  offer: "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400",
  rejected: "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400",
  pending: "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400",
};

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const days = Math.floor(diff / 86400000);
  const hours = Math.floor(diff / 3600000);
  const minutes = Math.floor(diff / 60000);
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return "Just now";
}

const PAGE_SIZE = 20;

export default function ApplicationsPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // Build query params
  const buildUrl = useCallback(() => {
    const params = new URLSearchParams();
    params.set("limit", String(PAGE_SIZE));
    params.set("offset", String(offset));
    if (statusFilter) params.set("status", statusFilter);
    if (search.trim()) {
      // Search by company (backend supports company/role separately)
      params.set("company", search.trim());
    }
    return `/applications?${params.toString()}`;
  }, [statusFilter, search, offset]);

  const { data, isLoading, isFetching } = useQuery<ApplicationsResponse>({
    queryKey: ["applications", statusFilter, search, offset],
    queryFn: () => apiGet<ApplicationsResponse>(buildUrl()),
    keepPreviousData: true,
    staleTime: 30 * 1000,
  } as any);

  const deleteMutation = useMutation({
    mutationFn: (id: string) => apiDelete(`/applications/${id}`),
    onMutate: (id) => setDeletingId(id),
    onSuccess: () => {
      toast.success("Application moved to bin");
      queryClient.invalidateQueries({ queryKey: ["applications"] });
      queryClient.invalidateQueries({ queryKey: ["analytics"] });
    },
    onError: (error: unknown) => {
      const apiError = getApiError(error);
      toast.error(apiError.message || "Failed to delete application");
    },
    onSettled: () => setDeletingId(null),
  });

  const apps = data?.items ?? [];
  const hasMore = apps.length === PAGE_SIZE;
  const hasPrev = offset > 0;

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearch(e.target.value);
    setOffset(0);
  };

  const handleStatusChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setStatusFilter(e.target.value);
    setOffset(0);
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Applications</h2>
        {isFetching && !isLoading && (
          <span className="text-xs text-muted-foreground animate-pulse">Refreshing...</span>
        )}
      </div>

      <Card>
        <CardHeader className="py-4">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
            {/* Search */}
            <div className="relative flex-1 max-w-sm w-full">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                id="applications-search"
                type="search"
                placeholder="Search by company..."
                className="pl-8"
                value={search}
                onChange={handleSearchChange}
              />
            </div>
            {/* Status filter */}
            <select
              id="applications-status-filter"
              className="h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring min-w-[140px]"
              value={statusFilter}
              onChange={handleStatusChange}
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </CardHeader>

        <CardContent>
          <div className="rounded-md border">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b bg-muted/50 transition-colors">
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Company</th>
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Role</th>
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Status</th>
                  <th className="h-10 px-4 text-left align-middle font-medium text-muted-foreground">Last Updated</th>
                  <th className="h-10 px-4 text-right align-middle font-medium text-muted-foreground">Actions</th>
                </tr>
              </thead>
              <tbody>
                {isLoading ? (
                  // Skeleton rows
                  [...Array(5)].map((_, i) => (
                    <tr key={i} className="border-b">
                      <td className="p-4"><Skeleton className="h-4 w-28" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-36" /></td>
                      <td className="p-4"><Skeleton className="h-5 w-20 rounded-full" /></td>
                      <td className="p-4"><Skeleton className="h-4 w-16" /></td>
                      <td className="p-4 text-right"><Skeleton className="h-7 w-16 ml-auto" /></td>
                    </tr>
                  ))
                ) : apps.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-muted-foreground">
                      {search || statusFilter
                        ? "No applications match your filters."
                        : "No applications yet. Connect Gmail and sync to see your applications."}
                    </td>
                  </tr>
                ) : (
                  apps.map((app) => (
                    <tr key={app.id} className="border-b transition-colors hover:bg-muted/50">
                      <td className="p-4 align-middle font-medium max-w-[160px] truncate">
                        {app.company_name}
                      </td>
                      <td className="p-4 align-middle text-muted-foreground max-w-[180px] truncate">
                        {app.role_title}
                      </td>
                      <td className="p-4 align-middle">
                        <span
                          className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold capitalize ${
                            STATUS_COLORS[app.current_status] ?? STATUS_COLORS.pending
                          }`}
                        >
                          {app.current_status}
                        </span>
                      </td>
                      <td className="p-4 align-middle text-muted-foreground text-xs">
                        {timeAgo(app.last_activity_at)}
                      </td>
                      <td className="p-4 align-middle text-right">
                        <div className="flex justify-end gap-1">
                          <Button
                            id={`view-app-${app.id}`}
                            variant="ghost"
                            size="sm"
                            className="gap-1 h-7"
                            onClick={() => router.push(`/applications/${app.id}`)}
                          >
                            <Eye className="h-3 w-3" />
                            View
                          </Button>
                          <Button
                            id={`delete-app-${app.id}`}
                            variant="ghost"
                            size="sm"
                            className="gap-1 h-7 text-destructive hover:text-destructive hover:bg-destructive/10"
                            disabled={deletingId === app.id}
                            onClick={() => deleteMutation.mutate(app.id)}
                          >
                            <Trash2 className="h-3 w-3" />
                            {deletingId === app.id ? "Deleting..." : "Delete"}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          <div className="flex items-center justify-between py-4">
            <p className="text-xs text-muted-foreground">
              {apps.length > 0 ? `Showing ${offset + 1}–${offset + apps.length}` : "No results"}
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={!hasPrev || isLoading}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                className="gap-1"
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                disabled={!hasMore || isLoading}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                className="gap-1"
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
