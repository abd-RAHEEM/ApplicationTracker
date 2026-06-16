/**
 * useAuth hook — authentication actions via TanStack Query + Zustand.
 *
 * Provides:
 *   - user, isAuthenticated, isLoading from Zustand store
 *   - login, register, logout, forgotPassword, resetPassword mutations
 *   - fetchMe query to hydrate and REVALIDATE the auth store on every mount
 *
 * Session revalidation strategy:
 *   - We ALWAYS call GET /users/me on mount (even if Zustand has cached user).
 *   - This ensures that if the backend session has expired or was revoked, we
 *     immediately clear the stale local cache and redirect to login.
 *   - We skip the call ONLY on auth pages (/login, /register, etc.) since those
 *     pages have no session and the 401 → refresh → 401 loop would occur.
 */
"use client";

import { useEffect } from "react";
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
  const { user, isAuthenticated, isLoading, setUser, clearAuth, setLoading } = useAuthStore();
  const router = useRouter();
  const pathname = usePathname();
  const queryClient = useQueryClient();

  // Don't fetch the current user on auth pages — they have no session cookies.
  // Doing so triggers 401 → refresh → 401 → redirect to /login → infinite loop.
  const AUTH_PATHS = ["/login", "/register", "/forgot-password", "/reset-password"];
  const isOnAuthPage = AUTH_PATHS.some((p) => pathname?.startsWith(p));

  // ── Hydrate & Revalidate user on mount ───────────────────────────────────────
  // Note: We always call /users/me (not just when !user) to ensure stale cached
  // data from localStorage is caught immediately if the backend session is gone.
  const { data: fetchedUser, error: fetchMeError, isSuccess, isError, isPending: isFetchingMe } = useQuery({
    queryKey: ["me"],
    queryFn: () => apiGet<UserRead>("/users/me"),
    enabled: !isOnAuthPage,           // Skip on auth pages — no session exists
    retry: false,
    staleTime: 30 * 1000,             // Re-fetch at most every 30s (not every render)
  });

  useEffect(() => {
    if (isOnAuthPage) {
      setLoading(false);
      return;
    }
    if (isSuccess && fetchedUser) {
      setUser(fetchedUser);
    } else if (isError || fetchMeError) {
      document.cookie = "session_active=; path=/; max-age=0; SameSite=Lax";
      document.cookie = "session_active=; path=/; max-age=0; SameSite=Lax; Secure";
      clearAuth();
    }
  }, [fetchedUser, fetchMeError, isSuccess, isError, isOnAuthPage, setUser, clearAuth, setLoading]);

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
    onSuccess: (response) => {
      const loginData = response.data.data;

      // Set the frontend session cookie immediately so middleware can detect auth.
      // 30 days = 2592000 seconds, matching refresh token lifetime.
      document.cookie = "session_active=1; path=/; max-age=2592000; SameSite=Lax";

      // Trust loginData.user directly to avoid a redundant /users/me API request
      const freshUser: UserRead = {
        id: loginData.user.id,
        username: loginData.user.username,
        full_name: loginData.user.full_name,
        is_active: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        gmail_connected: loginData.user.gmail_connected,
        gmail_email: null,
        initial_import_done: loginData.user.initial_import_done,
        is_email_verified: true,
        is_onboarding_completed: loginData.user.gmail_connected && loginData.user.initial_import_done,
      };
      setUser(freshUser);
      queryClient.setQueryData(["me"], freshUser);

      // Route based on FRESH user onboarding state
      let redirectPath: string;
      if (!freshUser.gmail_connected) {
        // New user or user who never connected Gmail → must go through onboarding
        redirectPath = "/onboarding/connect-gmail";
      } else if (!freshUser.initial_import_done) {
        // Gmail connected but initial import not configured
        redirectPath = "/onboarding/import-config";
      } else {
        // Fully onboarded — send to intended destination or dashboard
        redirectPath = "/dashboard";
        if (typeof window !== "undefined") {
          const params = new URLSearchParams(window.location.search);
          const from = params.get("from");
          if (from && from.startsWith("/") && !AUTH_PATHS.some(p => from.startsWith(p))) {
            redirectPath = from;
          }
        }
      }

      toast.success(`Welcome back, ${freshUser.username}!`);

      // Use window.location.href (not router.push) to force a full page reload.
      // This ensures the middleware re-evaluates the session_active cookie we just set.
      setTimeout(() => {
        window.location.href = redirectPath;
      }, 100);
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
      _performLogoutCleanup();
      toast.success("Logged out successfully");
    },
    onError: () => {
      // Force logout even if backend call fails
      _performLogoutCleanup();
    },
  });

  function _performLogoutCleanup() {
    clearAuth();
    queryClient.clear();
    // Clear the frontend session indicator cookie (both Secure and non-Secure variants)
    document.cookie = "session_active=; path=/; max-age=0; SameSite=Lax";
    document.cookie = "session_active=; path=/; max-age=0; SameSite=Lax; Secure";
    // Use window.location for a hard redirect so all state is cleared
    window.location.href = "/login";
  }

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
