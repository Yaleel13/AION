import { hasValidOwnerSession } from "@/lib/aion/owner-session"

async function proxy(req: Request, method: "GET" | "POST") {
  if (!hasValidOwnerSession(req.headers.get("cookie"))) {
    return Response.json({ error: "Owner authentication required." }, { status: 401 })
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
    const data = await response.json()
    if (!response.ok) {
      return Response.json(
        { error: data?.detail || data?.error || "Moltbook research is unavailable." },
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
