import { hasValidOwnerSession } from "@/lib/aion/owner-session"

export async function GET(req: Request) {
  if (!hasValidOwnerSession(req.headers.get("cookie"))) {
    return Response.json({ error: "Owner authentication required." }, { status: 401 })
  }
  if (!process.env.AION_OWNER_TOKEN) {
    return Response.json({ error: "AION owner authentication is not configured." }, { status: 503 })
  }
  try {
    const response = await fetch(new URL("/api/internal/capabilities", req.url), {
      headers: { Authorization: `Bearer ${process.env.AION_OWNER_TOKEN}` },
      cache: "no-store",
    })
    const data = await response.json()
    if (!response.ok) return Response.json({ error: data?.detail || data?.error || "Capability registry unavailable." }, { status: response.status })
    return Response.json(data, { headers: { "Cache-Control": "no-store" } })
  } catch (error) {
    console.error("[AION] capability registry proxy error:", error instanceof Error ? error.message : String(error))
    return Response.json({ error: "Capability registry is temporarily unavailable." }, { status: 500 })
  }
}
