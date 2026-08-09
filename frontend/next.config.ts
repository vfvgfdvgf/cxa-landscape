import type { NextConfig } from "next";

const apiUrl = (process.env.DJANGO_API_URL || "https://nakheel-najd.onrender.com").replace(/\/$/, "");
const apiOrigin = new URL(apiUrl).origin;
const apiHostname = new URL(apiUrl).hostname;

function isSafeRedirectPath(value: string): boolean {
  return value.startsWith("/") && !value.startsWith("//") && !value.includes("://") && !/[\r\n]/.test(value);
}

const nextConfig: NextConfig = {
  poweredByHeader: false,
  compress: true,
  trailingSlash: true,
  images: {
    // Render already serves compressed WebP/JPEG assets. Serving them directly avoids
    // the trailing-slash redirect that turns /_next/image into a 400 in production.
    unoptimized: true,
    formats: ["image/avif", "image/webp"],
    minimumCacheTTL: 86400,
    remotePatterns: [
      { protocol: "https", hostname: apiHostname },
      { protocol: "https", hostname: "res.cloudinary.com" },
      { protocol: "https", hostname: "getsiaq.online" },
      { protocol: "https", hostname: "www.getsiaq.online" }
    ]
  },
  async headers() {
    const contentSecurityPolicy = [
      "default-src 'self'",
      "base-uri 'self'",
      "form-action 'self'",
      "frame-ancestors 'none'",
      "object-src 'none'",
      "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com",
      "style-src 'self' 'unsafe-inline'",
      "font-src 'self' data:",
      "media-src 'self' blob:",
      `img-src 'self' data: blob: ${apiOrigin} https://res.cloudinary.com https://getsiaq.online https://www.getsiaq.online https://www.google-analytics.com https://stats.g.doubleclick.net`,
      "connect-src 'self' https://www.google-analytics.com https://region1.google-analytics.com https://stats.g.doubleclick.net",
      "frame-src https://www.googletagmanager.com",
      "upgrade-insecure-requests"
    ].join("; ");
    return [
      {
        source: "/videos/:path*",
        headers: [
          { key: "Cache-Control", value: "public, max-age=31536000, immutable" },
          { key: "X-Content-Type-Options", value: "nosniff" },
        ],
      },
      {
        source: "/video-posters/:path*",
        headers: [
          { key: "Cache-Control", value: "public, max-age=31536000, immutable" },
          { key: "X-Content-Type-Options", value: "nosniff" },
        ],
      },
      {
        source: "/media/:path*",
        headers: [
          { key: "Cache-Control", value: "public, max-age=86400, s-maxage=31536000, stale-while-revalidate=604800" },
          { key: "X-Content-Type-Options", value: "nosniff" },
        ],
      },
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: contentSecurityPolicy },
          { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains; preload" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" }
        ]
      }
    ];
  },
  async rewrites() {
    return [
      {
        source: "/google:token([A-Za-z0-9_-]+).html",
        destination: "/api/site-verification/google/:token",
      },
    ];
  },
  async redirects() {
    const domainRedirect = {
      source: "/:path*",
      has: [{ type: "host" as const, value: "www.getsiaq.online" }],
      destination: "https://getsiaq.online/:path*",
      permanent: true
    };
    try {
      const response = await fetch(`${apiUrl}/api/v1/redirects/`, {
        headers: { Accept: "application/json" },
        signal: AbortSignal.timeout(8000)
      });
      if (!response.ok) return [domainRedirect];
      const items = (await response.json()) as Array<{ source: string; destination: string; permanent: boolean }>;
      return [domainRedirect, ...items.filter((item) => (
        isSafeRedirectPath(item.source)
        && isSafeRedirectPath(item.destination)
        && item.source !== item.destination
      ))];
    } catch {
      return [domainRedirect];
    }
  }
};

export default nextConfig;
