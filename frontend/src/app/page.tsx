import { redirect } from "next/navigation";

/**
 * Root page — redirects based on auth state.
 * The actual redirect logic is in middleware.ts.
 * This page handles the case where a user hits / directly.
 */
export default function RootPage() {
  redirect("/dashboard");
}
