/**
 * useAuth hook — authentication actions via TanStack Query + Zustand.
 *
 * Provides:
 *   - user, isAuthenticated, isLoading from Zustand store
 *   - login, register, logout, forgotPassword, resetPassword mutations
 *   - fetchMe query to hydrate the auth store on mount
 */
"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import { apiClient, apiGet, getApiError } from "@/lib/api-client";
import { useAuthStore } from "@/store/auth-store";
import type {
  LoginRequest,
  LoginResponse,
  RegisterRequest,
  RegisterResponse,
  UserRead,
  PasswordResetRequest,
  PasswordResetConfirm,
} from "@/types/auth";

export function useAuth() {
  const { user, isAuthenticated, isLoading, setUser, clearAuth } = useAuthStore();
  const router = useRouter();
  const queryClient = useQueryClient();

  // ── Hydrate user on mount ────────────────────────────────────────────────────
  const { isLoading: isFetchingMe } = useQuery({
    queryKey: ["me"],
    queryFn: () => apiGet<UserRead>("/users/me"),
    enabled: !user,                      // Only fetch if no cached user
    retry: false,
    onSuccess: (data) => setUser(data),
    onError: () => clearAuth(),
  } as any);

  // ── Register ─────────────────────────────────────────────────────────────────
  const registerMutation = useMutation({
    mutationFn: (data: RegisterRequest) =>
      apiClient.post<{ data: RegisterResponse }>("/auth/register", data),
    onSuccess: () => {
      toast.success("Account created! Please log in.");
      router.push("/login");
    },
    onError: (error: unknown) => {
      const apiError = getApiError(error);
      toast.error(apiError.message);
    },
  });

  // ── Login ─────────────────────────────────────────────────────────────────────
  const loginMutation = useMutation({
    mutationFn: (data: LoginRequest) =>
      apiClient.post<{ data: LoginResponse }>("/auth/login", data),
    onSuccess: async (response) => {
      const loginData = response.data.data;
      // Fetch full user profile after login
      try {
        const userRead = await apiGet<UserRead>("/users/me");
        setUser(userRead);
        queryClient.setQueryData(["me"], userRead);
      } catch {
        setUser({
          id: loginData.user.id,
          username: loginData.user.username,
          full_name: loginData.user.full_name,
          is_active: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          gmail_connected: loginData.user.gmail_connected,
          gmail_email: null,
          initial_import_done: loginData.user.initial_import_done,
        });
      }

      // Route based on onboarding state
      if (!loginData.user.gmail_connected) {
        router.push("/onboarding/connect-gmail");
      } else if (!loginData.user.initial_import_done) {
        router.push("/onboarding/import-config");
      } else {
        router.push("/dashboard");
      }

      toast.success(`Welcome back, ${loginData.user.username}!`);
    },
    onError: (error: unknown) => {
      const apiError = getApiError(error);
      toast.error(apiError.message);
    },
  });

  // ── Logout ────────────────────────────────────────────────────────────────────
  const logoutMutation = useMutation({
    mutationFn: () => apiClient.post("/auth/logout"),
    onSuccess: () => {
      clearAuth();
      queryClient.clear();
      router.push("/login");
      toast.success("Logged out successfully");
    },
    onError: () => {
      // Force logout even if backend call fails
      clearAuth();
      queryClient.clear();
      router.push("/login");
    },
  });

  // ── Forgot Password ───────────────────────────────────────────────────────────
  const forgotPasswordMutation = useMutation({
    mutationFn: (data: PasswordResetRequest) =>
      apiClient.post("/auth/forgot-password", data),
    onSuccess: () => {
      toast.success(
        "If that account exists, a reset link has been sent to your Gmail."
      );
    },
    onError: () => {
      // Still show success — don't reveal user existence
      toast.success(
        "If that account exists, a reset link has been sent to your Gmail."
      );
    },
  });

  // ── Reset Password ────────────────────────────────────────────────────────────
  const resetPasswordMutation = useMutation({
    mutationFn: (data: PasswordResetConfirm) =>
      apiClient.post("/auth/reset-password", data),
    onSuccess: () => {
      toast.success("Password reset! Please log in with your new password.");
      router.push("/login");
    },
    onError: (error: unknown) => {
      const apiError = getApiError(error);
      toast.error(apiError.message);
    },
  });

  return {
    // State
    user,
    isAuthenticated,
    isLoading: isLoading || isFetchingMe,

    // Actions
    register: registerMutation.mutate,
    isRegistering: registerMutation.isPending,

    login: loginMutation.mutate,
    isLoggingIn: loginMutation.isPending,

    logout: logoutMutation.mutate,
    isLoggingOut: logoutMutation.isPending,

    forgotPassword: forgotPasswordMutation.mutate,
    isSendingReset: forgotPasswordMutation.isPending,

    resetPassword: resetPasswordMutation.mutate,
    isResettingPassword: resetPasswordMutation.isPending,
  };
}
