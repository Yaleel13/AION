import { hasValidOwnerSession } from "@/lib/aion/owner-session"

const INSPECTOR_SESSION_ID = "owner-memory-inspector-v1"

export async function GET(req: Request) {
  if (!hasValidOwnerSession(req.headers.get("cookie"))) {
    return Response.json({ error: "Owner authentication required." }, { status: 401 })
  }
  if (!process.env.AION_OWNER_TOKEN) {
    return Response.json({ error: "AION owner authentication is not configured." }, { status: 503 })
  }

  try {
    const url = new URL(req.url)
    const includeInactive = url.searchParams.get("includeInactive") === "true"
    const response = await fetch(new URL("/api/internal/conversation", req.url), {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.AION_OWNER_TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        action: "facts",
        client_session_id: INSPECTOR_SESSION_ID,
        include_inactive: includeInactive,
        limit: 50,
      }),
      cache: "no-store",
    })

    const data = await response.json()
    if (!response.ok) {
      console.error("[AION] owner memory inspector failed:", response.status)
      return Response.json({ error: "AION memory inspector is temporarily unavailable." }, { status: 502 })
    }

    return Response.json(data, { headers: { "Cache-Control": "no-store" } })
  } catch (error) {
    console.error("[AION] owner memory inspector error:", error instanceof Error ? error.message : String(error))
    return Response.json({ error: "AION memory inspector is temporarily unavailable." }, { status: 500 })
  }
}
