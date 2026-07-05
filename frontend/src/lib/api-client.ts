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
import { toast } from "sonner";


const rawUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/v1";
const absoluteUrl = rawUrl.endsWith("/v1") || rawUrl.endsWith("/v1/")
  ? rawUrl
  : `${rawUrl.replace(/\/$/, "")}/v1`;

export const API_BASE_URL = typeof window !== "undefined"
  ? "/api/v1"
  : absoluteUrl;

// ── Axios Instance ─────────────────────────────────────────────────────────────
export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,     // Send HttpOnly cookies automatically
  headers: {
    "Content-Type": "application/json",
    Accept: "application/json",
  },
  timeout: 15_000,
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

    // If 401 and not already retried and not a refresh/login/register request
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest.url?.includes("auth/refresh") &&
      !originalRequest.url?.includes("auth/login") &&
      !originalRequest.url?.includes("auth/register")
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
      } catch (refreshError: any) {
        processPendingRequests(refreshError as Error);

        // If the refresh call itself failed with 429 (Too Many Requests),
        // we do NOT redirect to login and do NOT retry.
        if (refreshError?.response?.status === 429) {
          if (typeof window !== "undefined") {
            toast.error("Too many requests, please wait a moment and try again.");
          }
          return Promise.reject(refreshError);
        }

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

    // Never attempt token refresh for 429 responses — just propagate the error.
    // The caller (useAuth mutations) will handle 429 with a user-friendly toast.
    if (error.response?.status === 429) {
      return Promise.reject(error);
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
  if (axios.isAxiosError(error)) {
    console.error("API Error details:", error);

    // Handle request timeout (e.g. Render cold start)
    if (error.code === "ECONNABORTED" || error.message.toLowerCase().includes("timeout")) {
      return {
        code: "TIMEOUT",
        message: "Server is starting up, please wait... (request timed out)",
      };
    }

    // Handle Network Error (server down or starting up)
    if (error.message === "Network Error") {
      return {
        code: "NETWORK_ERROR",
        message: "Network error. The server might be down or starting up. Please try again.",
      };
    }

    // 429 — Too Many Requests
    if (error.response?.status === 429) {
      return {
        code: "RATE_LIMIT_EXCEEDED",
        message: "Too many attempts. Please wait a moment and try again.",
      };
    }

    // Structured backend error response
    if (error.response?.data?.error) {
      const backendError = error.response.data.error as ApiError;

      // Map well-known error codes to friendly messages
      switch (backendError.code) {
        case "INVALID_CREDENTIALS":
          return {
            ...backendError,
            message: "Incorrect username or password.",
          };
        case "USERNAME_TAKEN":
          return {
            ...backendError,
            message: "That username is already taken. Please choose a different one.",
          };
        case "SESSION_REVOKED":
          return {
            ...backendError,
            message: "Your session has expired. Please log in again.",
          };
        case "WEAK_PASSWORD":
          return {
            ...backendError,
            message: backendError.message, // Already descriptive from backend
          };
        case "RATE_LIMIT_EXCEEDED":
          return {
            ...backendError,
            message: "Too many attempts. Please wait a minute and try again.",
          };
        default:
          return backendError;
      }
    }
  }
  return {
    code: "UNKNOWN_ERROR",
    message: "An unexpected error occurred",
  };
}
