/**
 * Axios-based API client with automatic token refresh.
 *
 * Design decisions:
 * - Credentials: "include" sends HttpOnly cookies on every request.
 * - Interceptor handles 401 → silent token refresh → retry original request.
 * - A single refresh lock prevents multiple simultaneous refresh attempts.
 */
import axios, {
  AxiosError,
  AxiosInstance,
  AxiosRequestConfig,
  AxiosResponse,
  InternalAxiosRequestConfig,
} from "axios";

const rawUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";
const API_BASE_URL = rawUrl.endsWith("/v1") || rawUrl.endsWith("/v1/")
  ? rawUrl
  : `${rawUrl.replace(/\/$/, "")}/v1`;

// ── Axios Instance ─────────────────────────────────────────────────────────────
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,     // Send HttpOnly cookies automatically
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  timeout: 30_000,
});

// ── Refresh Token Lock ─────────────────────────────────────────────────────────
let isRefreshing = false;
let pendingRequests: Array<{
  resolve: (value: unknown) => void;
  reject: (reason?: unknown) => void;
}> = [];

function processPendingRequests(error: Error | null): void {
  pendingRequests.forEach(({ resolve, reject }) => {
    if (error) reject(error);
    else resolve(null);
  });
  pendingRequests = [];
}

// ── Response Interceptor ───────────────────────────────────────────────────────
apiClient.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & {
      _retry?: boolean;
    };

    // If 401 and not already retried and not a refresh/login request
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes("/auth/refresh") &&
      !originalRequest.url?.includes("/auth/login")
    ) {
      if (isRefreshing) {
        // Queue this request until refresh completes
        return new Promise((resolve, reject) => {
          pendingRequests.push({ resolve, reject });
        }).then(() => apiClient(originalRequest));
      }

      originalRequest._retry = true;
      isRefreshing = true;

      try {
        await apiClient.post("/auth/refresh");
        processPendingRequests(null);
        return apiClient(originalRequest);
      } catch (refreshError) {
        processPendingRequests(refreshError as Error);
        // Only redirect to login if we are NOT already on an auth page.
        // Redirecting unconditionally causes an infinite reload loop:
        // auth page mounts → useQuery(["me"]) → 401 → refresh → 401 → redirect to /login → repeat.
        if (typeof window !== "undefined") {
          const AUTH_PATHS = ["/login", "/register", "/forgot-password", "/reset-password"];
          const isOnAuthPage = AUTH_PATHS.some((p) => window.location.pathname.startsWith(p));
          if (!isOnAuthPage) {
            // Clear the session_active cookie so Next.js middleware doesn't redirect us back to /dashboard
            document.cookie = "session_active=; path=/; max-age=0; SameSite=Lax";
            document.cookie = "session_active=; path=/; max-age=0; SameSite=Lax; Secure";
            window.location.href = "/login";
          }
        }
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }

    return Promise.reject(error);
  }
);

// ── Typed API helper ───────────────────────────────────────────────────────────
export async function apiGet<T>(url: string, config?: AxiosRequestConfig): Promise<T> {
  const response = await apiClient.get<{ data: T }>(url, config);
  return response.data.data;
}

export async function apiPost<T = unknown>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig
): Promise<T> {
  const response = await apiClient.post<{ data: T }>(url, data, config);
  return response.data.data;
}



export async function apiPatch<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig
): Promise<T> {
  const response = await apiClient.patch<{ data: T }>(url, data, config);
  return response.data.data;
}

export async function apiDelete<T>(
  url: string,
  config?: AxiosRequestConfig
): Promise<T> {
  const response = await apiClient.delete<{ data: T }>(url, config);
  return response.data.data;
}

// ── API Error Helper ───────────────────────────────────────────────────────────
export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

export function getApiError(error: unknown): ApiError {
  if (axios.isAxiosError(error) && error.response?.data?.error) {
    return error.response.data.error as ApiError;
  }
  return {
    code: "UNKNOWN_ERROR",
    message: "An unexpected error occurred",
  };
}
