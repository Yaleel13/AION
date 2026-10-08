/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: false,
  },

  async rewrites() {
    const runtimeUrl =
      process.env.AION_RUNTIME_URL ?? "http://127.0.0.1:8000"

    return [
      {
        source: "/api/runtime/:path*",
        destination: `${runtimeUrl}/runtime/:path*`,
      },
    ]
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
