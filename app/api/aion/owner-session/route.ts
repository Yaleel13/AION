import {
  OWNER_SESSION_COOKIE,
  createOwnerSessionValue,
  hasValidOwnerSession,
  ownerSessionConfigured,
  verifyOwnerToken,
} from "@/lib/aion/owner-session"

const COOKIE_MAX_AGE_SECONDS = 8 * 60 * 60
const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1", "[::1]"])

function submittedOwnerToken(value: string) {
  const trimmed = value.trim()
  const assignment = /^AION_OWNER_TOKEN\s*=\s*(.*)$/.exec(trimmed)
  if (!assignment) return trimmed

  const configured = assignment[1].trim()
  if (
    configured.length >= 2
    && (configured.startsWith("\"") && configured.endsWith("\"")
      || configured.startsWith("'") && configured.endsWith("'"))
  ) {
    return configured.slice(1, -1)
  }
  return configured
}

function cookieAttributes(request: Request, maxAge: number) {
  let secure = true
  try {
    const url = new URL(request.url)
    secure = url.protocol === "https:" || !LOOPBACK_HOSTS.has(url.hostname)
    // Next can normalize its internal URL to localhost behind a proxy. The
    // public Host must also be loopback before allowing a local HTTP cookie.
    const host = request.headers.get("host")
    if (host) {
      const authority = new URL(`http://${host}`)
      secure ||= !LOOPBACK_HOSTS.has(authority.hostname) || Boolean(authority.username || authority.password || authority.search || authority.hash) || authority.pathname !== "/"
    }
    secure ||= request.headers.get("x-forwarded-proto")?.split(",")[0].trim() === "https"
  } catch {
    // Keep the production-safe default if the request URL is malformed.
    secure = true
  }
  return `HttpOnly; ${secure ? "Secure; " : ""}SameSite=Strict; Path=/; Max-Age=${maxAge}`
}

export async function GET(req: Request) {
  return Response.json({
    configured: ownerSessionConfigured(),
    authenticated: hasValidOwnerSession(req.headers.get("cookie")),
  }, { headers: { "Cache-Control": "no-store" } })
}

export async function POST(req: Request) {
  if (!ownerSessionConfigured()) {
    return Response.json({ error: "AION owner authentication is not configured." }, { status: 503 })
  }

  let body: unknown
  try {
    body = await req.json()
  } catch {
    return Response.json({ error: "A valid JSON body is required." }, { status: 400 })
  }

  if (!body || typeof body !== "object" || Array.isArray(body) || !("token" in body) || typeof body.token !== "string") {
    return Response.json({ error: "An owner token is required." }, { status: 400 })
  }
  if (!verifyOwnerToken(submittedOwnerToken(body.token))) {
    return Response.json({ error: "Invalid owner token." }, { status: 403 })
  }

  const session = createOwnerSessionValue(COOKIE_MAX_AGE_SECONDS)
  if (!session) {
    return Response.json({ error: "AION owner authentication is not configured." }, { status: 503 })
  }

  return new Response(JSON.stringify({ authenticated: true }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Set-Cookie": `${OWNER_SESSION_COOKIE}=${session}; ${cookieAttributes(req, COOKIE_MAX_AGE_SECONDS)}`,
      "Cache-Control": "no-store",
    },
  })
}

export async function DELETE(req: Request) {
  return new Response(JSON.stringify({ authenticated: false }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Set-Cookie": `${OWNER_SESSION_COOKIE}=; ${cookieAttributes(req, 0)}`,
      "Cache-Control": "no-store",
    },
  })
}
