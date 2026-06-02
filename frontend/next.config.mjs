/** @type {import('next').NextConfig} */
const nextConfig = {
  // Output standalone for Docker deployments
  output: "standalone",

  // Skip type checking on production builds to prevent OOM errors on Render
  typescript: {
    ignoreBuildErrors: true,
  },
  // Skip linting on production builds to prevent OOM errors on Render
  eslint: {
    ignoreDuringBuilds: true,
  },
  // Disable webpack build worker to save memory on 512MB RAM instances
  experimental: {
    webpackBuildWorker: false,
  },

  // Strict mode for catching React issues early
  reactStrictMode: true,

  // Allow images from external sources (future: company logos)
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "**",
      },
    ],
  },

  // Rewrite /api/v1/* → backend URL during development
  // In production, use the NEXT_PUBLIC_API_URL directly.
  async rewrites() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    return process.env.NODE_ENV === "development"
      ? [
          {
            source: "/api/:path*",
            destination: `${apiUrl}/:path*`,
          },
        ]
      : [];
  },
};

export default nextConfig;
