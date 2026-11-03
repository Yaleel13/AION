/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: false,
  },

  async rewrites() {
    const runtimeUrl =
      process.env.AION_RUNTIME_URL ?? "http://127.0.0.1:8000"
    const localRuntime =
      (process.env.AION_RUNTIME_MODE ?? "").trim().toLowerCase() === "local"

    const rewrites = [
      {
        source: "/api/runtime/:path*",
        destination: `${runtimeUrl}/runtime/:path*`,
      },
    ]

    if (localRuntime) {
      rewrites.push({
        source: "/api/internal/conversation",
        destination: `${runtimeUrl}/api/internal/conversation`,
      })
      for (const name of [
        "acceptance", "capabilities", "operator-briefing", "outbound-gates",
        "sales-alerts", "moltbook-research", "moltbook-preparation",
        "moltbook-reviews", "moltbook-approvals", "commercial-execution",
      ]) {
        rewrites.push({
          source: `/api/internal/${name}`,
          destination: `${runtimeUrl}/api/internal/${name}`,
        })
      }
    }

    return rewrites
  },

  // Server-only secrets must never be exposed through NEXT_PUBLIC_*.
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          { key: "X-Frame-Options", value: "SAMEORIGIN" },
          {
            key: "Permissions-Policy",
            value: "camera=(self), microphone=(self), geolocation=()",
          },
        ],
      },
    ]
  },
}

export default nextConfig
