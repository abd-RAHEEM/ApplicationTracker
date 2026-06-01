"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Mail, Shield, Zap } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { useGmail } from "@/hooks/useGmail";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";

export default function ConnectGmailPage() {
  const router = useRouter();
  const { user } = useAuthStore();
  const { getAuthUrl, isLoading, error } = useGmail();

  useEffect(() => {
    // If user already connected Gmail, move them to the next step
    if (user?.is_email_verified) {
      if (user?.is_onboarding_completed) {
        router.push("/dashboard");
      } else {
        router.push("/onboarding/import-config");
      }
    }
  }, [user, router]);

  const handleConnect = async () => {
    await getAuthUrl();
  };

  return (
    <Card className="shadow-lg border-0 bg-white/50 backdrop-blur-sm">
      <CardHeader className="text-center pb-2">
        <div className="mx-auto w-12 h-12 bg-primary/10 text-primary rounded-full flex items-center justify-center mb-4">
          <Mail className="w-6 h-6" />
        </div>
        <CardTitle className="text-3xl font-bold">Connect your Gmail</CardTitle>
        <CardDescription className="text-base mt-2">
          JobTracker needs read-only access to your inbox to automatically parse 
          job application statuses and upcoming interviews.
        </CardDescription>
      </CardHeader>
      
      <CardContent className="mt-6 space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div className="flex gap-3 p-4 bg-muted/50 rounded-lg">
            <Shield className="w-5 h-5 text-green-600 shrink-0" />
            <div>
              <h4 className="font-semibold text-sm">Read-Only Access</h4>
              <p className="text-sm text-muted-foreground">We can only read emails. We can never send or delete them.</p>
            </div>
          </div>
          <div className="flex gap-3 p-4 bg-muted/50 rounded-lg">
            <Zap className="w-5 h-5 text-amber-500 shrink-0" />
            <div>
              <h4 className="font-semibold text-sm">Automated Tracking</h4>
              <p className="text-sm text-muted-foreground">We instantly identify applications, assessments, and offers.</p>
            </div>
          </div>
        </div>
        
        {error && (
          <div className="p-3 bg-destructive/10 text-destructive text-sm rounded-md font-medium text-center">
            {error}
          </div>
        )}
      </CardContent>
      
      <CardFooter className="flex flex-col gap-3 pt-6">
        <Button 
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
