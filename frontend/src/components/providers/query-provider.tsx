"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { ReactQueryDevtools } from "@tanstack/react-query-devtools";
import { useState } from "react";

export function QueryClientProviderWrapper({
  children,
}: {
  children: React.ReactNode;
}) {
  // useState ensures a new QueryClient per request (RSC-safe)
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 60 * 1000,       // 1 minute — cache is fresh
            gcTime: 5 * 60 * 1000,      // 5 minutes — keep in memory
            retry: (failureCount, error: any) => {
              // Don't retry 401/403 — these are auth issues
              if ([401, 403].includes(error?.response?.status)) return false;
              return failureCount < 2;
            },
            refetchOnWindowFocus: false, // Disable aggressive refetching
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
