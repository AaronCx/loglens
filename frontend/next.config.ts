import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'export',
  basePath: '/loglens',
  images: {
    unoptimized: true,
  },
};

export default nextConfig;
