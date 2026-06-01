"use client";

import { Mail, Lock } from "lucide-react";
import { useAuthStore } from "@/store/auth-store";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function GmailSettingsPage() {
  const { user } = useAuthStore();

  if (!user) return null;

  return (
    <div className="max-w-2xl mx-auto py-8">
      <h2 className="text-2xl font-bold tracking-tight mb-6">Integration Settings</h2>
      
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="w-5 h-5 text-primary" />
            Gmail Connection
          </CardTitle>
          <CardDescription>
            View your permanently connected Google account
          </CardDescription>
        </CardHeader>
        
        <CardContent>
          {user.gmail_connected ? (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg bg-muted/30">
                <div>
                  <h4 className="font-medium">Connected Account</h4>
                  <p className="text-sm text-muted-foreground">{user.gmail_email}</p>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground bg-muted px-3 py-1.5 rounded-full">
                  <Lock className="w-4 h-4" />
                  <span>Permanent</span>
                </div>
              </div>
              
              <div className="text-sm text-muted-foreground px-1">
                <p>
                  To preserve the integrity of your applications and analytics, JobTracker 
                  operates on a strict one-user-one-mailbox model. Your connected Gmail 
                  account cannot be switched or disconnected.
                </p>
                <p className="mt-2">
                  If you need to change your email account, you must delete your JobTracker 
                  account completely and create a new one.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg bg-muted/50">
                <div>
                  <h4 className="font-medium">Not Connected</h4>
                  <p className="text-sm text-muted-foreground">Please complete onboarding to connect your Gmail.</p>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
