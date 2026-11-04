import { NextResponse } from "next/server"

const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1", "[::1]"])

function localRuntimeEnabled(): boolean {
  return (process.env.AION_RUNTIME_MODE ?? "").trim().toLowerCase() === "local"
}

function isLoopbackHostname(hostname: string): boolean {
  return LOOPBACK_HOSTS.has(hostname.trim().toLowerCase())
}

function effectivePort(url: URL): string {
  if (url.port) return url.port
  return url.protocol === "https:" ? "443" : "80"
}

function requestIsLocalAndSameOrigin(request: Request): boolean {
  try {
    const requestUrl = new URL(request.url)
    let requestHostname = requestUrl.hostname
    let requestPort = effectivePort(requestUrl)

    const hostHeader = request.headers.get("host")
    if (hostHeader) {
      const hostUrl = new URL(`${requestUrl.protocol}//${hostHeader}`)
      if (isLoopbackHostname(hostUrl.hostname)) {
        requestHostname = hostUrl.hostname
        requestPort = effectivePort(hostUrl)
      }
    }

    if (!isLoopbackHostname(requestHostname)) return false

    const fetchSite = request.headers.get("sec-fetch-site")
    if (fetchSite && fetchSite !== "same-origin" && fetchSite !== "none") return false

    const origin = request.headers.get("origin")
    if (!origin) return true

    const originUrl = new URL(origin)
    return (
      isLoopbackHostname(originUrl.hostname) &&
      originUrl.protocol === requestUrl.protocol &&
      effectivePort(originUrl) === requestPort
    )
  } catch {
    return false
  }
}

export async function GET(request: Request) {
  if (!requestIsLocalAndSameOrigin(request)) {
    return NextResponse.json({ available: false, reason: "loopback-only" }, { status: 403 })
  }

  if (!localRuntimeEnabled()) {
    return NextResponse.json({ available: false, reason: "local-runtime-disabled" })
  }

  return NextResponse.json({
    available: false,
    reason: "scoped-voice-authorization-required",
  })
}

export async function POST(request: Request) {
  if (!requestIsLocalAndSameOrigin(request)) {
    return NextResponse.json({ error: "AION local voice is available only from the loopback interface." }, { status: 403 })
  }

  if (!localRuntimeEnabled()) {
    return NextResponse.json({ error: "Local voice is unavailable outside AION local mode." }, { status: 503 })
  }
  return NextResponse.json(
    { error: "Local voice is unavailable until scoped voice authorization is implemented." },
    { status: 503 },
  )
}
