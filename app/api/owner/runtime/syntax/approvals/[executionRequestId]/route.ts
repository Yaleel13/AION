import { hasValidOwnerSession, requireCsrfHeader } from "@/lib/aion/owner-session"

const requestId = /^[0-9a-f]{32}$/

function reply(body: object, status = 200) {
  return Response.json(body, { status, headers: { "Cache-Control": "no-store" } })
}

function runtimeUrl() {
  const runtime = new URL(process.env.AION_RUNTIME_URL ?? "http://127.0.0.1:8000")
  if (!["http:", "https:"].includes(runtime.protocol) ||
      !["localhost", "127.0.0.1", "[::1]"].includes(runtime.hostname) ||
      runtime.username || runtime.password || runtime.search || runtime.hash || runtime.pathname !== "/") {
    return null
  }
  return runtime
}

function validApproval(data: unknown): data is Record<string, unknown> {
  if (!data || Array.isArray(data) || typeof data !== "object") return false
  const row = data as Record<string, unknown>
  return requestId.test(String(row.execution_request_id)) &&
    row.capability === "runtime.syntax" &&
    typeof row.requester_principal === "string" &&
    ["pending", "approved", "denied"].includes(String(row.decision)) &&
    typeof row.created_at === "string" &&
    typeof row.expires_at === "string"
}

async function proxy(
  req: Request,
  executionRequestId: string,
  body?: { approved: boolean },
) {
  if (!hasValidOwnerSession(req.headers.get("cookie"))) return reply({ error: "Owner authentication required." }, 401)
  if (!requestId.test(executionRequestId)) return reply({ error: "Invalid runtime syntax approval ID." }, 400)
  const ownerToken = (process.env.AION_OWNER_TOKEN ?? "").trim()
  if ((process.env.AION_RUNTIME_MODE ?? "").trim().toLowerCase() !== "local" || !ownerToken) {
    return reply({ error: "Runtime syntax approvals are unavailable." }, 503)
  }
  const runtime = runtimeUrl()
  if (!runtime) return reply({ error: "Runtime syntax approvals are unavailable." }, 503)
  const path = body
    ? `/owner/runtime-syntax-approvals/${executionRequestId}/decision`
    : `/owner/runtime-syntax-approvals/${executionRequestId}`
  try {
    const response = await fetch(new URL(path, runtime), {
      method: body ? "POST" : "GET",
      cache: "no-store",
      redirect: "error",
      signal: AbortSignal.any([req.signal, AbortSignal.timeout(5_000)]),
      headers: {
        Authorization: `Bearer ${ownerToken}`,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    })
    const data: unknown = await response.json()
    if (!response.ok) {
      return reply(
        { error: "Runtime syntax approvals are unavailable." },
        response.status >= 500 ? 503 : response.status,
      )
    }
    if (!validApproval(data) || data.execution_request_id !== executionRequestId) {
      return reply({ error: "Runtime syntax approvals are unavailable." }, 502)
    }
    return reply(data)
  } catch {
    return reply({ error: "Runtime syntax approvals are unavailable." }, 503)
  }
}

export async function GET(
  req: Request,
  { params }: { params: Promise<{ executionRequestId: string }> },
) {
  const { executionRequestId } = await params
  return proxy(req, executionRequestId)
}

export async function POST(
  req: Request,
  { params }: { params: Promise<{ executionRequestId: string }> },
) {
  if (!hasValidOwnerSession(req.headers.get("cookie"))) return reply({ error: "Owner authentication required." }, 401)
  const csrfError = requireCsrfHeader(req)
  if (csrfError) return csrfError
  const target = new URL(req.url)
  if (req.headers.get("host")) target.host = req.headers.get("host")!
  if (req.headers.get("origin") !== target.origin) return reply({ error: "Same-origin request required." }, 403)
  let body: unknown
  try {
    body = await req.json()
  } catch {
    return reply({ error: "Approval decision requires an approved boolean." }, 400)
  }
  if (!body || Array.isArray(body) || typeof body !== "object" ||
      Object.keys(body).length !== 1 || typeof (body as { approved?: unknown }).approved !== "boolean") {
    return reply({ error: "Approval decision requires an approved boolean." }, 400)
  }
  const { executionRequestId } = await params
  return proxy(req, executionRequestId, { approved: (body as { approved: boolean }).approved })
}
