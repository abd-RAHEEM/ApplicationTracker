"use client";

import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Mail, Shield, Zap, CheckCircle, AlertCircle } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { useGmail } from "@/hooks/useGmail";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useQueryClient } from "@tanstack/react-query";

export default function ConnectGmailPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { user, setUser } = useAuthStore();
  const { getAuthUrl, isLoading, error: hookError } = useGmail();
  const [pageError, setPageError] = useState<string | null>(null);
  const [justConnected, setJustConnected] = useState(false);

  // Check for OAuth return parameters (backend redirects here with ?gmail=connected or ?error=...)
  useEffect(() => {
    const gmailParam = searchParams.get("gmail");
    const errorParam = searchParams.get("error");

    if (gmailParam === "connected") {
      // OAuth succeeded — refresh user data and proceed
      setJustConnected(true);
      (async () => {
        try {
          await queryClient.refetchQueries({ queryKey: ["me"] });
        } catch (err) {
          console.error("Failed to refetch user status:", err);
        } finally {
          router.push("/onboarding/import-config");
        }
      })();
    } else if (errorParam) {
      const errorMessages: Record<string, string> = {
        access_denied: "You denied Gmail access. Please grant permission to continue.",
        oauth_failed: "Gmail connection failed. Please try again.",
      };
      setPageError(errorMessages[errorParam] ?? "An error occurred. Please try again.");
    }
  }, [searchParams, router, queryClient]);

  useEffect(() => {
    // If user already connected Gmail, move them to the next step
    if (user?.gmail_connected && !justConnected) {
      if (user?.is_onboarding_completed) {
        router.push("/dashboard");
      } else {
        router.push("/onboarding/import-config");
      }
    }
  }, [user, router, justConnected]);

  const handleConnect = async () => {
    setPageError(null);
    await getAuthUrl();
  };

  const displayError = pageError || hookError;

  if (justConnected) {
    return (
      <Card className="shadow-lg border-0 bg-white/50 backdrop-blur-sm">
        <CardHeader className="text-center pb-2">
          <div className="mx-auto w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mb-4">
            <CheckCircle className="w-8 h-8" />
          </div>
          <CardTitle className="text-3xl font-bold text-green-700">Gmail Connected!</CardTitle>
          <CardDescription className="text-base mt-2">
            Your Gmail account has been successfully connected. Setting up your import configuration...
          </CardDescription>
        </CardHeader>
        <CardContent className="flex justify-center py-8">
          <Spinner size="lg" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="shadow-lg border-0 bg-white/50 backdrop-blur-sm">
      <CardHeader className="text-center pb-2">
        <div className="mx-auto w-12 h-12 bg-primary/10 text-primary rounded-full flex items-center justify-center mb-4">
          <Mail className="w-6 h-6" />
        </div>
        <CardTitle className="text-3xl font-bold">Connect your Gmail</CardTitle>
        <CardDescription className="text-base mt-2">
          ApplicationTracker needs read-only access to your inbox to automatically parse 
          job application statuses and upcoming interviews.
        </CardDescription>
      </CardHeader>
      
      <CardContent className="mt-6 space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="flex gap-3 p-4 bg-muted/50 rounded-lg">
            <Shield className="w-5 h-5 text-green-600 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-sm">Read-Only Access</h4>
              <p className="text-sm text-muted-foreground">We can only read emails. We can never send or delete them.</p>
            </div>
          </div>
          <div className="flex gap-3 p-4 bg-muted/50 rounded-lg">
            <Zap className="w-5 h-5 text-amber-500 shrink-0 mt-0.5" />
            <div>
              <h4 className="font-semibold text-sm">Automated Tracking</h4>
              <p className="text-sm text-muted-foreground">We instantly identify applications, assessments, and offers.</p>
            </div>
          </div>
        </div>
        
        {displayError && (
          <div className="flex items-start gap-2 p-3 bg-destructive/10 text-destructive text-sm rounded-md font-medium">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{displayError}</span>
          </div>
        )}
      </CardContent>
      
      <CardFooter className="flex flex-col gap-3 pt-6">
        <Button 
          id="connect-gmail-button"
          size="lg" 
          className="w-full text-base font-semibold h-12"
          onClick={handleConnect}
          disabled={isLoading}
        >
          {isLoading ? (
            <><Spinner className="mr-2" size="sm" /> Redirecting to Google...</>
          ) : (
            "Connect Gmail Securely"
          )}
        </Button>
        <p className="text-xs text-center text-muted-foreground mt-2">
          By connecting, you agree to our Terms of Service and Privacy Policy.
        </p>
      </CardFooter>
    </Card>
  );
}
