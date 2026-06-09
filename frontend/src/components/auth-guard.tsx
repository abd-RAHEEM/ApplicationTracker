/**
 * AuthGuard — client-side auth gate for dashboard routes.
 *
 * Wraps dashboard layout children. While auth state is resolving (isLoading),
 * renders a full-screen spinner so pages don't flash with empty data.
 * If auth fails (no valid session), redirects to /login.
 *
 * This complements the middleware (which handles the initial request) by
 * also guarding against cases where the middleware lets a user through
 * (e.g., session_active cookie present) but the backend session has
 * actually expired.
 */
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/hooks/useAuth";
import { Loader2 } from "lucide-react";

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    // Only redirect once loading is complete — don't redirect while fetching /users/me
    if (!isLoading && !isAuthenticated) {
      // Clear stale session_active cookie in case it wasn't cleared on logout
      document.cookie = "session_active=; path=/; max-age=0; SameSite=Lax";
      router.replace("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  // Show loading spinner while verifying session with backend
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3 text-muted-foreground">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm">Loading...</p>
        </div>
      </div>
    );
  }

  // If not authenticated, return null (the useEffect will redirect)
  if (!isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
