"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useAuth } from "@/hooks/useAuth";
import { apiClient, getApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Trash2, Loader2, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

export default function SettingsPage() {
  const { user, logout } = useAuth();
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [confirmText, setConfirmText] = useState("");

  const deleteAccountMutation = useMutation({
    mutationFn: async () => {
      const response = await apiClient.delete("/users/me", {
        data: {
          password,
          confirmation_text: confirmText,
        },
      });
      return response.data;
    },
    onSuccess: () => {
      toast.success("Account deleted successfully");
      setIsConfirmOpen(false);
      // Clean up local session and redirect
      logout();
    },
    onError: (error: unknown) => {
      const apiError = getApiError(error);
      toast.error(apiError.message || "Failed to delete account");
    },
  });

  const createdAt = user?.created_at
    ? new Date(user.created_at).toLocaleDateString("en-CA") // YYYY-MM-DD
    : "—";

  const handleOpenDialog = () => {
    setPassword("");
    setConfirmText("");
    setIsConfirmOpen(true);
  };

  const handleCloseDialog = () => {
    setIsConfirmOpen(false);
  };

  const handleDeleteSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (confirmText !== "DELETE") {
      toast.error("Confirmation text must be 'DELETE'");
      return;
    }
    deleteAccountMutation.mutate();
  };

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
          <Button
            id="delete-account-trigger"
            variant="destructive"
            className="gap-2"
            onClick={handleOpenDialog}
          >
            <Trash2 className="h-4 w-4" />
            Delete Account
          </Button>
        </CardContent>
      </Card>

      {/* Delete Account confirmation dialog */}
      <AlertDialog open={isConfirmOpen} onOpenChange={(open) => { if (!open) handleCloseDialog(); }}>
        <AlertDialogContent className="border-destructive/30">
          <form onSubmit={handleDeleteSubmit}>
            <AlertDialogHeader>
              <div className="flex items-center gap-2 text-destructive mb-2">
                <AlertTriangle className="h-5 w-5" />
                <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
              </div>
              <AlertDialogDescription>
                This action is permanent and <strong>cannot be undone</strong>. It will delete your account and all associated applications, synced emails, and status history.
              </AlertDialogDescription>
            </AlertDialogHeader>

            <div className="my-4 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="delete-password">Confirm Password</Label>
                <Input
                  id="delete-password"
                  type="password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="delete-confirm-text">
                  Type <span className="font-bold text-destructive select-none">DELETE</span> to confirm
                </Label>
                <Input
                  id="delete-confirm-text"
                  type="text"
                  placeholder="Type DELETE"
                  value={confirmText}
                  onChange={(e) => setConfirmText(e.target.value)}
                  required
                />
              </div>
            </div>

            <AlertDialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={handleCloseDialog}
                disabled={deleteAccountMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                id="delete-account-confirm"
                type="submit"
                variant="destructive"
                className="gap-2"
                disabled={deleteAccountMutation.isPending || confirmText !== "DELETE"}
              >
                {deleteAccountMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Deleting...
                  </>
                ) : (
                  <>
                    <Trash2 className="h-4 w-4" />
                    Permanently Delete Account
                  </>
                )}
              </Button>
            </AlertDialogFooter>
          </form>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
