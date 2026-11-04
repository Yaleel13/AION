import { NextResponse } from "next/server"
import { hasValidOwnerSession, requireCsrfHeader } from "@/lib/aion/owner-session"
import { runtimeRequestId } from "@/lib/aion/runtime-correlation"

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

  return NextResponse.json({ available: hasValidOwnerSession(request.headers.get("cookie")) })
}

export async function POST(request: Request) {
  if (!requestIsLocalAndSameOrigin(request)) {
    return NextResponse.json({ error: "AION local voice is available only from the loopback interface." }, { status: 403 })
  }

  if (!localRuntimeEnabled()) {
    return NextResponse.json({ error: "Local voice is unavailable outside AION local mode." }, { status: 503 })
  }
  if (!hasValidOwnerSession(request.headers.get("cookie"))) {
    return NextResponse.json({ error: "Owner authentication required." }, { status: 401 })
  }
  const csrfError = requireCsrfHeader(request)
  if (csrfError) return csrfError
  const target = new URL(request.url)
  if (request.headers.get("host")) target.host = request.headers.get("host")!
  if (request.headers.get("origin") !== target.origin || new URL(request.url).search) {
    return NextResponse.json({ error: "Same-origin voice request required." }, { status: 403 })
  }
  try {
    const body: unknown = await request.json()
    if (!body || Array.isArray(body) || typeof body !== "object" || Object.keys(body).length) {
      return NextResponse.json({ error: "Voice turn requires an empty JSON object." }, { status: 400 })
    }
  } catch {
    return NextResponse.json({ error: "Voice turn requires an empty JSON object." }, { status: 400 })
  }
  try {
    const runtime = new URL(process.env.AION_RUNTIME_URL ?? "http://127.0.0.1:8000")
    if (runtime.protocol !== "http:" || !isLoopbackHostname(runtime.hostname) || runtime.username || runtime.password || runtime.search || runtime.hash || runtime.pathname !== "/") {
      return NextResponse.json({ error: "Local voice unavailable." }, { status: 503 })
    }
    const response = await fetch(new URL("/owner/voice/turn", runtime), {
      method: "POST", cache: "no-store", redirect: "error",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${process.env.AION_OWNER_TOKEN ?? ""}` },
      body: "{}", signal: AbortSignal.any([request.signal, AbortSignal.timeout(400_000)]),
    })
    const requestId = runtimeRequestId(response.headers.get("x-aion-request-id"))
    const data = await response.json() as Record<string, unknown>
    if (!response.ok || data.ok !== true || data.status !== "succeeded" || typeof data.transcript !== "string" || typeof data.reply !== "string") {
      return NextResponse.json({ error: "Local voice unavailable." }, { status: 503 })
    }
    return NextResponse.json({
      transcript: data.transcript.slice(0, 2_000), reply: data.reply.slice(0, 2_000),
      status: "succeeded", ...(requestId ? { requestId } : {}),
    }, { headers: { "Cache-Control": "no-store" } })
  } catch {
    return NextResponse.json({ error: "Local voice unavailable." }, { status: 503 })
  }
}
