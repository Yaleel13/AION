import { hasValidOwnerSession, requireCsrfHeader } from "@/lib/aion/owner-session"

async function readUpstreamBody(response: Response) {
  const text = await response.text()
  if (!text) return {}

  try {
    return JSON.parse(text) as Record<string, unknown>
  } catch {
    return { detail: text.slice(0, 500) }
  }
}

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
    const response = await fetch(new URL("/api/internal/moltbook-research", req.url), {
      method,
      headers: {
        Authorization: `Bearer ${process.env.AION_OWNER_TOKEN}`,
      },
      cache: "no-store",
    })
    const data = await readUpstreamBody(response)
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : undefined
      const error = typeof data.error === "string" ? data.error : undefined
      return Response.json(
        { error: detail || error || "Moltbook research is unavailable." },
        { status: response.status },
      )
    }
    return Response.json(data, { headers: { "Cache-Control": "no-store" } })
  } catch (error) {
    console.error("[AION] Moltbook research proxy error:", error instanceof Error ? error.message : String(error))
    return Response.json({ error: "Moltbook research is temporarily unavailable." }, { status: 500 })
  }
}

export async function GET(req: Request) {
  return proxy(req, "GET")
}

export async function POST(req: Request) {
  return proxy(req, "POST")
}
