import { hasValidOwnerSession } from "@/lib/aion/owner-session"

async function proxy(req: Request, method: "GET" | "POST") {
  if (!hasValidOwnerSession(req.headers.get("cookie"))) {
    return Response.json({ error: "Owner authentication required." }, { status: 401 })
  }
  if (!process.env.AION_OWNER_TOKEN) {
    return Response.json({ error: "AION owner authentication is not configured." }, { status: 503 })
  }

  try {
    const init: RequestInit = {
      method,
      headers: { Authorization: `Bearer ${process.env.AION_OWNER_TOKEN}` },
      cache: "no-store",
    }
    if (method === "POST") {
      init.headers = {
        ...init.headers,
        "Content-Type": "application/json",
      }
      init.body = await req.text()
    }
    const response = await fetch(new URL("/api/internal/moltbook-reviews", req.url), init)
    const data = await response.json()
    if (!response.ok) {
      return Response.json(
        { error: data?.detail || data?.error || "Opportunity review feedback is unavailable." },
        { status: response.status },
      )
    }
    return Response.json(data, { headers: { "Cache-Control": "no-store" } })
  } catch (error) {
    console.error("[AION] Moltbook review proxy error:", error instanceof Error ? error.message : String(error))
    return Response.json({ error: "Opportunity review feedback is temporarily unavailable." }, { status: 500 })
  }
}

export async function GET(req: Request) {
  return proxy(req, "GET")
}

export async function POST(req: Request) {
  return proxy(req, "POST")
}
