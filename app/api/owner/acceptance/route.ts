import { hasValidOwnerSession } from "@/lib/aion/owner-session"

export async function GET(req: Request) {
  if (!hasValidOwnerSession(req.headers.get("cookie"))) {
    return Response.json({ error: "Owner authentication required." }, { status: 401 })
  }
  if (!process.env.AION_OWNER_TOKEN) {
    return Response.json({ error: "AION owner authentication is not configured." }, { status: 503 })
  }
  try {
    const response = await fetch(new URL("/api/internal/acceptance", req.url), {
      headers: { Authorization: `Bearer ${process.env.AION_OWNER_TOKEN}` },
      cache: "no-store",
    })
    const raw = await response.text()
    let data: unknown
    try {
      data = raw ? JSON.parse(raw) : {}
    } catch {
      console.error("[AION] acceptance internal endpoint returned non-JSON:", response.status, raw.slice(0, 160))
      return Response.json(
        { error: "Reliability acceptance evidence is temporarily unavailable." },
        { status: response.ok ? 502 : response.status, headers: { "Cache-Control": "no-store" } },
      )
    }
    return Response.json(data, { status: response.status, headers: { "Cache-Control": "no-store" } })
  } catch (error) {
    console.error("[AION] acceptance proxy error:", error instanceof Error ? error.message : String(error))
    return Response.json({ error: "Reliability acceptance evidence is temporarily unavailable." }, { status: 500 })
  }
}
