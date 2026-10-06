import type { NextConfig } from "next";

const isMobileBuild = process.env.NEXT_BUILD_TARGET === "mobile";
const devApiProxyUrl = (process.env.NEXT_DEV_API_PROXY_URL ?? "").trim().replace(/\/+$/, "");

const nextConfig: NextConfig = {
  reactStrictMode: true,
  experimental: {
    webpackBuildWorker: false,
  },
  ...(isMobileBuild
    ? {
        output: "export",
        trailingSlash: true,
        images: {
          unoptimized: true,
        },
      }
    : {}),
  ...(!isMobileBuild && devApiProxyUrl
    ? {
        async rewrites() {
          if (process.env.NODE_ENV !== "development") {
            return [];
          }

          return [
            {
              source: "/api/:path*",
              destination: `${devApiProxyUrl}/api/:path*`,
            },
          ];
        },
      }
    : {}),
};

export default nextConfig;
