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
const PROTECTED_PREFIXES = ["/dashboard", "/applications", "/analytics", "/bin", "/settings", "/onboarding"];

// Routes that authenticated users should not access
const AUTH_ROUTES = ["/login", "/register", "/forgot-password", "/reset-password"];

export function middleware(request: NextRequest): NextResponse {
  const { pathname } = request.nextUrl;
  const accessToken = request.cookies.get("access_token");
  const isAuthenticated = Boolean(accessToken?.value);

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
