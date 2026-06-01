/**
 * Zustand auth store — lightweight client-side auth state.
 *
 * Stores the current user profile. The source of truth for authentication
 * is the HttpOnly cookie (managed by the browser). This store is a cache
 * of the user's identity for UI rendering purposes only.
 *
 * On page load, the app calls GET /users/me to hydrate this store.
 * If the request fails with 401, the user is unauthenticated.
 */
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import type { UserRead } from "@/types/auth";

interface AuthState {
  user: UserRead | null;
  isLoading: boolean;
  isAuthenticated: boolean;

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

      setUser: (user) =>
        set({
          user,
          isAuthenticated: user !== null,
          isLoading: false,
        }),

      setLoading: (isLoading) => set({ isLoading }),

      clearAuth: () =>
        set({
          user: null,
          isAuthenticated: false,
          isLoading: false,
        }),
    }),
    {
      name: "auth-store",
      storage: createJSONStorage(() => sessionStorage), // sessionStorage: cleared on tab close
      partialize: (state) => ({ user: state.user }),     // Only persist user, not loading state
    }
  )
);
