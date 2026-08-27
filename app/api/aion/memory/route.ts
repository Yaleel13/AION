type MemoryBody = {
  clientSessionId?: string
}

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as MemoryBody
    const clientSessionId = body.clientSessionId?.trim()

    if (!clientSessionId) {
      return Response.json({ error: "A client session ID is required." }, { status: 400 })
    }
    if (!process.env.AION_OWNER_TOKEN) {
      return Response.json({ error: "AION owner authentication is not configured." }, { status: 503 })
    }

    const memoryUrl = new URL("/api/internal/conversation", req.url)
    const response = await fetch(memoryUrl, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.AION_OWNER_TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        action: "load",
        client_session_id: clientSessionId,
      }),
      cache: "no-store",
    })

    const data = await response.json()
    if (!response.ok) {
      console.error("[AION] durable memory load failed:", response.status)
      return Response.json({ error: "AION memory is temporarily unavailable." }, { status: 502 })
    }

    return Response.json(data)
  } catch (error) {
    console.error("[AION] memory proxy error:", error instanceof Error ? error.message : String(error))
    return Response.json({ error: "AION memory is temporarily unavailable." }, { status: 500 })
  }
}
