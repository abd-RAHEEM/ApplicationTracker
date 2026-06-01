"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth-store";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function DashboardPage() {
  const router = useRouter();
  const { user, isLoading } = useAuthStore();

  useEffect(() => {
    if (!isLoading && user) {
      if (!user.is_email_verified) {
        router.push("/onboarding/connect-gmail");
      } else if (!user.is_onboarding_completed) {
        router.push("/onboarding/import-config");
      }
    }
  }, [user, isLoading, router]);

  if (isLoading || !user) return null;

  return (
    <div className="space-y-6">
      <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
      <Card>
        <CardHeader>
          <CardTitle>Welcome back, {user.full_name}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Your Gmail is connected and your initial import configuration is saved.
            Phase 3 will begin fetching and parsing your emails.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
