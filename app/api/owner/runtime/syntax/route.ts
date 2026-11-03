import { hasValidOwnerSession, requireCsrfHeader } from "@/lib/aion/owner-session"

export async function POST(req: Request) {
  const reply = (body: object, status = 200) => Response.json(body, {
    status, headers: { "Cache-Control": "no-store" },
  })
  if (!hasValidOwnerSession(req.headers.get("cookie"))) {
    return reply({ error: "Owner authentication required." }, 401)
  }
  const csrfError = requireCsrfHeader(req)
  if (csrfError) return csrfError
  const target = new URL(req.url)
  // Next's local proxy may normalize req.url to localhost. Host preserves the
  // browser's actual authority (for example 127.0.0.1 on a local owner session).
  if (req.headers.get("host")) target.host = req.headers.get("host")!
  if (req.headers.get("origin") !== target.origin) {
    return reply({ error: "Same-origin request required." }, 403)
  }
  if (new URL(req.url).search) return reply({ error: "Syntax check accepts no parameters." }, 400)
  try {
    const body: unknown = await req.json()
    if (!body || Array.isArray(body) || typeof body !== "object" || Object.keys(body).length) {
      return reply({ error: "Syntax check requires an empty JSON object." }, 400)
    }
  } catch {
    return reply({ error: "Syntax check requires an empty JSON object." }, 400)
  }

  if ((process.env.AION_RUNTIME_MODE ?? "").trim().toLowerCase() !== "local") {
    return reply({ status: "unavailable", error: "Local runtime unavailable." }, 503)
  }
  try {
    const runtime = new URL(process.env.AION_RUNTIME_URL ?? "http://127.0.0.1:8000")
    if (!['http:', 'https:'].includes(runtime.protocol) ||
        !['localhost', '127.0.0.1', '[::1]'].includes(runtime.hostname) ||
        runtime.username || runtime.password || runtime.search || runtime.hash || runtime.pathname !== "/") {
      return reply({ status: "unavailable", error: "Local runtime unavailable." }, 503)
    }
    const response = await fetch(new URL("/local-executive/validate", runtime), {
      method: "POST", cache: "no-store", redirect: "error",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${(process.env.AION_OWNER_TOKEN ?? "").trim()}` },
      body: "{}", signal: AbortSignal.any([req.signal, AbortSignal.timeout(35_000)]),
    })
    if (!response.ok) return reply({ status: "unavailable", error: "Local runtime unavailable." }, 503)
    const data = await response.json() as Record<string, unknown>
    if (data.job !== "runtime.syntax" || typeof data.status !== "string" || !["succeeded", "failed", "timeout", "unavailable"].includes(data.status)) {
      return reply({ status: "unavailable", error: "Local runtime unavailable." }, 503)
    }
    return reply({
      ok: data.ok === true && data.status === "succeeded", status: data.status,
      output: typeof data.output === "string" ? data.output.slice(0, 12_000) : "",
      truncated: data.truncated === true,
    })
  } catch {
    return reply({ status: "unavailable", error: "Local runtime unavailable." }, 503)
  }
}
