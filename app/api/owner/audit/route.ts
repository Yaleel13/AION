import { hasValidOwnerSession } from "@/lib/aion/owner-session"
import { runtimeRequestId } from "@/lib/aion/runtime-correlation"
import { auditLookup } from "@/lib/aion/capability-audit"

export async function GET(req: Request) {
  const reply = (body: object, status = 200) => Response.json(body, {
    status, headers: { "Cache-Control": "no-store" },
  })
  if (!hasValidOwnerSession(req.headers.get("cookie"))) return reply({ error: "Owner authentication required." }, 401)
  const query = new URL(req.url).searchParams
  const id = runtimeRequestId(query.get("request_id"))
  if (!id || query.getAll("request_id").length !== 1 || [...query.keys()].some(key => key !== "request_id")) {
    return reply({ error: "Enter a valid runtime request ID." }, 400)
  }
  if (!(process.env.AION_OWNER_TOKEN ?? "").trim()) return reply({ error: "Audit lookup unavailable." }, 503)
  try {
    const runtime = new URL(process.env.AION_RUNTIME_URL ?? "http://127.0.0.1:8000")
    if (!["http:", "https:"].includes(runtime.protocol) ||
        !["localhost", "127.0.0.1", "[::1]"].includes(runtime.hostname) ||
        runtime.username || runtime.password || runtime.search || runtime.hash || runtime.pathname !== "/") {
      return reply({ error: "Audit lookup unavailable." }, 503)
    }
    const url = new URL("/owner/audit", runtime)
    url.searchParams.set("request_id", id)
    const response = await fetch(url, {
      cache: "no-store", redirect: "error", signal: AbortSignal.any([req.signal, AbortSignal.timeout(5_000)]),
      headers: { Authorization: `Bearer ${process.env.AION_OWNER_TOKEN!.trim()}` },
    })
    if (!response.ok) return reply({ error: "Audit lookup unavailable." }, 503)
    const data = auditLookup(await response.json(), id)
    return data ? reply(data) : reply({ error: "Audit lookup unavailable." }, 502)
  } catch {
    return reply({ error: "Audit lookup unavailable." }, 503)
  }
}
