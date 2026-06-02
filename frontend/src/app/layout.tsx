import { Inter } from "next/font/google";
import { ThemeProvider } from "@/components/theme-provider";
import { QueryClientProviderWrapper } from "@/components/providers/query-provider";
import "@/app/globals.css";

const inter = Inter({ subsets: ["latin"] });

export const metadata = {
  title: "ApplicationTracker Dashboard",
  description: "Professional job application tracking",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={inter.className}>
        <ThemeProvider
          attribute="class"
          defaultTheme="system"
          enableSystem
          disableTransitionOnChange
        >
          <QueryClientProviderWrapper>
            {children}
          </QueryClientProviderWrapper>
        </ThemeProvider>
      </body>
    </html>
  );
}
