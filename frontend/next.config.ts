import type { NextConfig } from "next";

// Backend access goes through app/api/[...path]/route.ts, which attaches the
// server-only API key. The previous rewrite proxied requests unauthenticated.
const nextConfig: NextConfig = {};

export default nextConfig;
