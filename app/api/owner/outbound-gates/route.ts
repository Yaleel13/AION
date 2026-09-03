import { hasValidOwnerSession, requireCsrfHeader, AION_REQUEST_HEADER } from "@/lib/aion/owner-session"

async function proxy(req: Request, method: "GET" | "POST") {
  if (!hasValidOwnerSession(req.headers.get("cookie"))) {
    return Response.json({ error: "Owner authentication required." }, { status: 401 })
  }
  if (method === "POST") {
    const csrfError = requireCsrfHeader(req)
    if (csrfError) return csrfError
  }
  if (!process.env.AION_OWNER_TOKEN) {
    return Response.json({ error: "AION owner authentication is not configured." }, { status: 503 })
  }
  try {
    const body = method === "POST" ? await req.text() : undefined
    const response = await fetch(new URL("/api/internal/outbound-gates", req.url), {
      method,
      headers: {
        Authorization: `Bearer ${process.env.AION_OWNER_TOKEN}`,
        ...(method === "POST" ? { "Content-Type": "application/json" } : {}),
        ...AION_REQUEST_HEADER,
      },
      body,
      cache: "no-store",
    })
    const data = await response.json()
    return Response.json(data, { status: response.status, headers: { "Cache-Control": "no-store" } })
  } catch (error) {
    console.error("[AION] outbound-gates proxy error:", error instanceof Error ? error.message : String(error))
    return Response.json({ error: "Outbound gate controls are temporarily unavailable." }, { status: 500 })
  }
}

export async function GET(req: Request) { return proxy(req, "GET") }
export async function POST(req: Request) { return proxy(req, "POST") }
