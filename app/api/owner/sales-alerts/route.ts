import { hasValidOwnerSession } from "@/lib/aion/owner-session"

async function proxy(req: Request, method: "GET" | "POST") {
  if (!hasValidOwnerSession(req.headers.get("cookie"))) {
    return Response.json({ error: "Owner authentication required." }, { status: 401 })
  }
  if (!process.env.AION_OWNER_TOKEN) {
    return Response.json({ error: "AION owner authentication is not configured." }, { status: 503 })
  }

  try {
    const body = method === "POST" ? await req.text() : undefined
    const response = await fetch(new URL("/api/internal/sales-alerts", req.url), {
      method,
      headers: {
        Authorization: `Bearer ${process.env.AION_OWNER_TOKEN}`,
        ...(method === "POST" ? { "Content-Type": "application/json" } : {}),
      },
      body,
      cache: "no-store",
    })

    const text = await response.text()
    let data: unknown
    try {
      data = text ? JSON.parse(text) : {}
    } catch {
      data = { error: text || `Internal sales alert endpoint returned ${response.status}` }
    }

    return Response.json(data, {
      status: response.status,
      headers: { "Cache-Control": "no-store" },
    })
  } catch (error) {
    console.error("[AION] sales alert proxy error:", error instanceof Error ? error.message : String(error))
    return Response.json({ error: "Sales alerts are temporarily unavailable." }, { status: 500 })
  }
}

export async function GET(req: Request) { return proxy(req, "GET") }
export async function POST(req: Request) { return proxy(req, "POST") }
