/** Server-side transport for the session-authenticated owner bridges. */
export async function fetchOwnerUpstream(url: URL, init: RequestInit): Promise<Response> {
  const failure = (status: number) => Response.json(
    { error: "Owner runtime is temporarily unavailable." },
    { status, headers: { "Cache-Control": "no-store" } },
  )
  try {
    const response = await fetch(url, { ...init, redirect: "error", cache: "no-store" })
    let data: unknown
    try {
      data = await response.json()
    } catch {
      return failure(502)
    }
    if (!data || typeof data !== "object" || Array.isArray(data)) return failure(502)
    const body = data as Record<string, unknown>
    if (response.status >= 500) {
      // This existing, non-sensitive configuration state is actionable in the UI.
      if (response.status === 503 && body.detail === "Durable Postgres is not configured") {
        return Response.json(body, { status: 503, headers: { "Cache-Control": "no-store" } })
      }
      return failure(response.status)
    }
    if (!response.ok) {
      body.error = typeof body.error === "string" ? body.error
        : typeof body.detail === "string" ? body.detail : "Owner runtime request failed."
    }
    return Response.json(body, { status: response.status, headers: { "Cache-Control": "no-store" } })
  } catch {
    return failure(503)
  }
}
