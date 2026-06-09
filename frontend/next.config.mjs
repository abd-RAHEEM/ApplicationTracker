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

  // Rewrite /api/* → backend URL in both development and production.
  // This enables Same-Origin proxying so that the browser treats backend requests
  // as first-party, avoiding third-party cookie blocking on Render subdomains.
  async rewrites() {
    const rawUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const apiUrl = rawUrl.replace(/\/v1\/?$/, "");
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/:path*`,
      },
    ];
  },
};

export default nextConfig;
