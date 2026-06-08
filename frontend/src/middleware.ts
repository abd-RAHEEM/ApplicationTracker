/**
 * Next.js middleware — route protection and auth-based redirects.
 *
 * Runs on the Edge runtime before every request.
 * Uses the presence of the access_token cookie as a proxy for
 * authentication state (the actual JWT validation happens on the backend).
 *
 * Redirect logic:
 *   - Unauthenticated users hitting /app/* → /login
 *   - Authenticated users hitting /login or /register → /dashboard
 */
import { NextRequest, NextResponse } from "next/server";

// Routes that require authentication
const PROTECTED_PREFIXES = ["/dashboard", "/applications", "/analytics", "/bin", "/settings"];
// Note: /onboarding is NOT protected by middleware — it's guarded client-side.
// This is because the auth cookie is set by the backend (different domain) and
// is not visible to this Next.js middleware running on the frontend domain.
// Instead we check a lightweight 'session_active' cookie set client-side on login.

// Routes that authenticated users should not access
const AUTH_ROUTES = ["/login", "/register", "/forgot-password", "/reset-password"];

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  // Check EITHER the backend access_token cookie (present on same-domain setups)
  // OR the lightweight session_active cookie set by the frontend after login.
  // The backend's HttpOnly cookies are on the backend domain and invisible here;
  // session_active is a plain cookie the frontend sets on its own domain.
  const accessToken = request.cookies.get("access_token");
  const sessionActive = request.cookies.get("session_active");
  const isAuthenticated = Boolean(accessToken?.value || sessionActive?.value);

  // Authenticated user trying to access auth pages → redirect to dashboard
  if (isAuthenticated && AUTH_ROUTES.some((r) => pathname.startsWith(r))) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  // Unauthenticated user trying to access protected pages → redirect to login
  if (!isAuthenticated && PROTECTED_PREFIXES.some((p) => pathname.startsWith(p))) {
    const loginUrl = new URL("/login", request.url);
    loginUrl.searchParams.set("from", pathname); // Preserve intended destination
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    // Apply to all routes except static files and Next.js internals
    "/((?!_next/static|_next/image|favicon.ico|icons|images).*)",
  ],
};
