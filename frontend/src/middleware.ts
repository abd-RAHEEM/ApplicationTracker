/**
 * Next.js middleware — route protection and auth-based redirects.
 *
 * Runs on the Edge runtime before every request.
 * Uses the presence of the session_active cookie (set client-side on login)
 * as a proxy for authentication state.
 *
 * Why session_active and not access_token:
 *   - The backend sets access_token as HttpOnly SameSite=None on the backend domain.
 *   - The frontend (Next.js) middleware runs on the frontend domain and cannot see
 *     cross-domain HttpOnly cookies.
 *   - session_active is a plain cookie set by the frontend JS on login and cleared on logout.
 *
 * Redirect logic:
 *   - Unauthenticated users hitting protected routes → /login
 *   - Authenticated users hitting /login or /register → /dashboard
 */
import { NextRequest, NextResponse } from "next/server";

// Routes that require authentication
const PROTECTED_PREFIXES = [
  "/dashboard",
  "/applications",
  "/analytics",
  "/bin",
  "/settings",
  "/onboarding",  // Onboarding also requires auth — user must be logged in
];

// Routes that authenticated users should not access
const AUTH_ROUTES = ["/login", "/register", "/forgot-password", "/reset-password"];

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;

  // Check the lightweight session_active cookie set by the frontend after login.
  // This is NOT the actual JWT — just a signal that the user successfully logged in.
  // Real JWT validation happens on the backend for every protected API call.
  const sessionActive = request.cookies.get("session_active");
  const isAuthenticated = Boolean(sessionActive?.value);

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
