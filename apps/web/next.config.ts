import type { NextConfig } from "next";
const nextConfig: NextConfig = {
  output: "standalone",
  devIndicators: false,
  experimental: {
    staleTimes: {dynamic: 30},
  },
};
export default nextConfig;
