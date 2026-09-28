import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  devIndicators: false,
  experimental: { proxyTimeout: 180000 },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${process.env.BACKEND_URL || "http://127.0.0.1:8000"}/api/:path*` }];
  },
};
export default nextConfig;
