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
import { useRouter, usePathname } from "next/navigation";
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
  const pathname = usePathname();
  const queryClient = useQueryClient();

  // Don't fetch the current user on auth pages — they have no session cookies.
  // Doing so triggers 401 → refresh → 401 → redirect to /login → infinite loop.
  const AUTH_PATHS = ["/login", "/register", "/forgot-password", "/reset-password"];
  const isOnAuthPage = AUTH_PATHS.some((p) => pathname?.startsWith(p));

  // ── Hydrate user on mount ────────────────────────────────────────────────────
  const { isLoading: isFetchingMe } = useQuery({
    queryKey: ["me"],
    queryFn: () => apiGet<UserRead>("/users/me"),
    enabled: !user && !isOnAuthPage,          // Skip on auth pages — no session exists
    retry: false,
    onSuccess: (data: UserRead) => setUser(data),
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
          gmail_connected: false,
          gmail_email: null,
          initial_import_done: false,
          is_email_verified: true,
          is_onboarding_completed: false,
        });
      }

      // Route based on onboarding state
      // Use window.location.href (not router.push) to force a full page reload.
      // Auth cookies are set by the backend (different domain), so a SPA
      // client-side navigation may not re-evaluate cookie state correctly.
      let redirectPath: string;
      if (!loginData.user.gmail_connected) {
        redirectPath = "/onboarding/connect-gmail";
      } else if (!loginData.user.initial_import_done) {
        redirectPath = "/onboarding/import-config";
      } else {
        redirectPath = "/dashboard";
        if (typeof window !== "undefined") {
          const params = new URLSearchParams(window.location.search);
          const from = params.get("from");
          if (from && from.startsWith("/")) {
            redirectPath = from;
          }
        }
      }

      // Set a lightweight cookie on the frontend domain so Next.js middleware
      // can detect authenticated state (backend's HttpOnly cookies are invisible
      // to middleware since they're tied to the backend domain).
      // 30 days = 2592000 seconds, matching refresh token lifetime.
      document.cookie = "session_active=1; path=/; max-age=2592000; SameSite=Lax; Secure";

      toast.success(`Welcome back, ${loginData.user.username}!`);

      // Small delay so the toast is visible before navigation
      setTimeout(() => {
        window.location.href = redirectPath;
      }, 500);
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
      // Clear the frontend session indicator cookie
      document.cookie = "session_active=; path=/; max-age=0; SameSite=Lax; Secure";
      router.push("/login");
      toast.success("Logged out successfully");
    },
    onError: () => {
      // Force logout even if backend call fails
      clearAuth();
      queryClient.clear();
      document.cookie = "session_active=; path=/; max-age=0; SameSite=Lax; Secure";
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
