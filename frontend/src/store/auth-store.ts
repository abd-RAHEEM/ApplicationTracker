/**
 * Zustand auth store — lightweight client-side auth state.
 *
 * Stores the current user profile. The source of truth for authentication
 * is the HttpOnly cookie (managed by the browser). This store is a cache
 * of the user's identity for UI rendering purposes only.
 *
 * On page load, the app ALWAYS calls GET /users/me to revalidate.
 * If the request fails with 401, the user is unauthenticated and the
 * store is cleared.
 *
 * Storage: localStorage (not sessionStorage) so the cached user profile
 * persists across browser restarts, matching the 30-day refresh token.
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { UserRead } from "@/types/auth";

interface AuthState {
  user: UserRead | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  lastValidatedAt: number | null; // Unix ms timestamp of last successful /users/me

  // Actions
  setUser: (user: UserRead | null) => void;
  setLoading: (loading: boolean) => void;
  clearAuth: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isLoading: true,
      isAuthenticated: false,
      lastValidatedAt: null,

      setUser: (user) =>
        set({
          user,
          isAuthenticated: user !== null,
          isLoading: false,
          lastValidatedAt: user !== null ? Date.now() : null,
        }),

      setLoading: (isLoading) => set({ isLoading }),

      clearAuth: () =>
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          lastValidatedAt: null,
        }),
    }),
    {
      name: "auth-store",
      storage: createJSONStorage(() => localStorage), // localStorage: persists across browser restarts
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.user !== null,
        lastValidatedAt: state.lastValidatedAt,
      }),
    }
  )
);
