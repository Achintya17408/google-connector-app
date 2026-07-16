import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  turbopack: {
    root: process.cwd(),
  },
  async rewrites() {
    const backend = process.env.BACKEND_API_URL ??
      "https://google-connector-app-production.up.railway.app";
    return [{source: "/api/:path*", destination: `${backend}/:path*`}];
  },
};

export default nextConfig;
