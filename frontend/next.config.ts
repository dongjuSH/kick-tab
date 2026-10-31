import type { NextConfig } from "next";

// Server-only origin of the FastAPI backend. The browser always calls same-origin /api/*.
const backendOrigin = (process.env.BACKEND_ORIGIN ?? "http://localhost:8000").replace(/\/+$/, "");

const nextConfig: NextConfig = {
  cacheComponents: true,
  partialPrefetching: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backendOrigin}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
