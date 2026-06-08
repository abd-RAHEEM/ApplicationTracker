"use client";

import { useAuthStore } from "@/store/auth-store";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Trash2 } from "lucide-react";

export default function SettingsPage() {
  const { user } = useAuthStore();

  const createdAt = user?.created_at
    ? new Date(user.created_at).toLocaleDateString("en-CA") // YYYY-MM-DD
    : "—";

  return (
    <div className="flex flex-col gap-6 max-w-4xl">
      <div>
        <h3 className="text-2xl font-bold tracking-tight">Settings</h3>
        <p className="text-muted-foreground">Manage your account settings and preferences.</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Profile Information</CardTitle>
          <CardDescription>Your account details. These are immutable.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <Input id="username" value={user?.username ?? "—"} disabled />
          </div>
          <div className="space-y-2">
            <Label htmlFor="fullname">Full Name</Label>
            <Input id="fullname" value={user?.full_name ?? "—"} disabled />
          </div>
          <div className="space-y-2">
            <Label htmlFor="gmail">Connected Gmail</Label>
            <Input
              id="gmail"
              value={user?.gmail_email ?? "Not connected"}
              disabled
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="created">Account Creation Date</Label>
            <Input id="created" value={createdAt} disabled />
          </div>
        </CardContent>
      </Card>

      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="text-destructive">Danger Zone</CardTitle>
          <CardDescription>Permanently delete your account and all of your data.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="destructive" className="gap-2">
            <Trash2 className="h-4 w-4" />
            Delete Account
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
