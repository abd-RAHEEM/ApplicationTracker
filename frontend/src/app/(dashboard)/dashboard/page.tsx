"use client";

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "@/lib/api-client";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Briefcase, CheckCircle, Mail, TrendingUp, Clock, XCircle, Activity } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";

interface Analytics {
  total_applications: number;
  applied_count: number;
  assessment_count: number;
  interview_count: number;
  offer_count: number;
  rejected_count: number;
  pending_count: number;
  interview_rate: number;
  offer_rate: number;
  response_rate: number;
  monthly_data: Array<{ month: string; count: number }>;
  computed_at: string | null;
}

interface Application {
  id: string;
  company_name: string;
  role_title: string;
  current_status: string;
  last_activity_at: string;
}

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
  const minutes = Math.floor(diff / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return "Just now";
}

export default function DashboardPage() {
  const { data: analytics, isLoading: loadingAnalytics } = useQuery<Analytics>({
    queryKey: ["analytics"],
    queryFn: () => apiGet<Analytics>("/analytics"),
    staleTime: 2 * 60 * 1000,
  });

  const { data: recentData, isLoading: loadingApps } = useQuery<{ items: Application[] }>({
    queryKey: ["applications", "recent"],
    queryFn: () => apiGet<{ items: Application[] }>("/applications?limit=5&offset=0"),
    staleTime: 60 * 1000,
  });

  const recentApps = recentData?.items ?? [];

  const statCards = [
    {
      title: "Total Applications",
      value: analytics?.total_applications ?? 0,
      icon: Briefcase,
      sub: null,
      color: "text-blue-500",
    },
    {
      title: "Interviews",
      value: analytics?.interview_count ?? 0,
      icon: Mail,
      sub: `${analytics?.interview_rate?.toFixed(1) ?? 0}% rate`,
      color: "text-purple-500",
    },
    {
      title: "Offers",
      value: analytics?.offer_count ?? 0,
      icon: CheckCircle,
      sub: `${analytics?.offer_rate?.toFixed(1) ?? 0}% rate`,
      color: "text-green-500",
    },
    {
      title: "Response Rate",
      value: `${analytics?.response_rate?.toFixed(1) ?? 0}%`,
      icon: Activity,
      sub: `${analytics?.rejected_count ?? 0} rejections`,
      color: "text-orange-500",
    },
  ];

  return (
    <>
      <div className="flex items-center justify-between space-y-2">
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        {analytics?.computed_at && (
          <p className="text-xs text-muted-foreground">
            Last computed: {timeAgo(analytics.computed_at)}
          </p>
        )}
      </div>

      {/* Stat Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statCards.map((card) => (
          <Card key={card.title}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{card.title}</CardTitle>
              <card.icon className={`h-4 w-4 ${card.color}`} />
            </CardHeader>
            <CardContent>
              {loadingAnalytics ? (
                <>
                  <Skeleton className="h-8 w-16 mb-1" />
                  {card.sub !== null && <Skeleton className="h-3 w-20" />}
                </>
              ) : (
                <>
                  <div className="text-2xl font-bold">{card.value}</div>
                  {card.sub && (
                    <p className="text-xs text-muted-foreground">{card.sub}</p>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
        {/* Monthly Trend */}
        <Card className="col-span-4">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              Monthly Trend
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loadingAnalytics ? (
              <div className="flex items-end gap-2 h-32">
                {[...Array(6)].map((_, i) => (
                  <Skeleton key={i} className="flex-1" style={{ height: `${20 + i * 15}%` }} />
                ))}
              </div>
            ) : analytics?.monthly_data && analytics.monthly_data.length > 0 ? (
              <div className="flex items-end gap-2 h-32">
                {analytics.monthly_data.slice(-6).map((d) => {
                  const maxCount = Math.max(...analytics.monthly_data.map((m) => m.count), 1);
                  const heightPct = Math.max((d.count / maxCount) * 100, 4);
                  return (
                    <div key={d.month} className="flex flex-col items-center gap-1 flex-1">
                      <span className="text-xs text-muted-foreground">{d.count}</span>
                      <div
                        className="w-full rounded-t bg-primary/80 transition-all"
                        style={{ height: `${heightPct}%` }}
                      />
                      <span className="text-xs text-muted-foreground truncate w-full text-center">
                        {d.month?.slice(0, 3) ?? ""}
                      </span>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
                No monthly data yet. Applications will appear here after syncing.
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Applications */}
        <Card className="col-span-3">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              Recent Applications
            </CardTitle>
          </CardHeader>
          <CardContent className="px-0">
            {loadingApps ? (
              <div className="space-y-3 px-6">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="flex items-center justify-between">
                    <div className="space-y-1">
                      <Skeleton className="h-4 w-24" />
                      <Skeleton className="h-3 w-32" />
                    </div>
                    <Skeleton className="h-5 w-16 rounded-full" />
                  </div>
                ))}
              </div>
            ) : recentApps.length === 0 ? (
              <div className="flex h-24 items-center justify-center text-sm text-muted-foreground px-6">
                No applications yet. Connect Gmail and sync to get started.
              </div>
            ) : (
              <div className="divide-y">
                {recentApps.map((app) => (
                  <div
                    key={app.id}
                    className="flex items-center justify-between px-6 py-3"
                  >
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{app.company_name}</p>
                      <p className="text-xs text-muted-foreground truncate">{app.role_title}</p>
                    </div>
                    <div className="flex flex-col items-end gap-1 ml-3 shrink-0">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold capitalize ${
                          STATUS_COLORS[app.current_status] ?? STATUS_COLORS.pending
                        }`}
                      >
                        {app.current_status}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {timeAgo(app.last_activity_at)}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Status Breakdown */}
      {!loadingAnalytics && (analytics?.total_applications ?? 0) > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <XCircle className="h-4 w-4 text-muted-foreground" />
              Status Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4">
              {[
                { label: "Applied", value: analytics?.applied_count, color: "bg-blue-500" },
                { label: "Assessment", value: analytics?.assessment_count, color: "bg-yellow-500" },
                { label: "Interview", value: analytics?.interview_count, color: "bg-purple-500" },
                { label: "Offer", value: analytics?.offer_count, color: "bg-green-500" },
                { label: "Rejected", value: analytics?.rejected_count, color: "bg-red-500" },
                { label: "Pending", value: analytics?.pending_count, color: "bg-gray-400" },
              ].map((stat) => (
                <div key={stat.label} className="flex flex-col items-center gap-2 p-3 rounded-lg bg-muted/30">
                  <div className={`h-2 w-2 rounded-full ${stat.color}`} />
                  <span className="text-2xl font-bold">{stat.value ?? 0}</span>
                  <span className="text-xs text-muted-foreground">{stat.label}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </>
  );
}
