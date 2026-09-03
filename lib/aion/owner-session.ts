import { createHmac, timingSafeEqual } from "node:crypto"

export const OWNER_SESSION_COOKIE = "aion_owner_session"
const OWNER_SESSION_CONTEXT = "aion-owner-session-v1"

function ownerToken() {
  return (process.env.AION_OWNER_TOKEN ?? "").trim()
}

function signExpiry(expiresAt: number) {
  const secret = ownerToken()
  if (!secret) return null
  return createHmac("sha256", secret)
    .update(`${OWNER_SESSION_CONTEXT}:${expiresAt}`)
    .digest("hex")
}

export function ownerSessionConfigured() {
  return ownerToken().length > 0
}

export function verifyOwnerToken(provided: string) {
  const expected = ownerToken()
  if (!expected || !provided) return false
  const left = Buffer.from(provided)
  const right = Buffer.from(expected)
  if (left.length !== right.length) return false
  return timingSafeEqual(left, right)
}

export function createOwnerSessionValue(maxAgeSeconds: number) {
  if (!ownerSessionConfigured()) return null
  const expiresAt = Math.floor(Date.now() / 1000) + maxAgeSeconds
  const signature = signExpiry(expiresAt)
  return signature ? `${expiresAt}.${signature}` : null
}

/** Header that must be present on all owner state-changing requests.  Set this
 *  on every owner POST/DELETE fetch in Boardroom components. */
export const AION_REQUEST_HEADER = { "X-AION-Request": "1" } as const

/**
 * Verify the CSRF double-submit header for owner state-changing requests.
 *
 * All owner POST/DELETE routes must call this in addition to
 * hasValidOwnerSession.  Browsers enforce the Same-Origin Policy for custom
 * request headers via CORS preflight, so a cross-origin attacker cannot set
 * this header — even if they somehow obtain a session cookie.
 *
 * The Next.js app sets `X-AION-Request: 1` on every fetch to an owner route.
 */
export function requireCsrfHeader(req: Request): Response | null {
  if (!req.headers.get("x-aion-request")) {
    return Response.json(
      { error: "Missing required request header. Ensure the request originates from the AION interface." },
      { status: 403 }
    )
  }
  return null
}

export function hasValidOwnerSession(cookieHeader: string | null) {
  if (!ownerSessionConfigured() || !cookieHeader) return false
  const raw = cookieHeader
    .split(";")
    .map((part) => part.trim())
    .find((part) => part.startsWith(`${OWNER_SESSION_COOKIE}=`))
    ?.slice(OWNER_SESSION_COOKIE.length + 1)
  if (!raw) return false

  const [expiresRaw, providedSignature, ...extra] = raw.split(".")
  if (extra.length > 0 || !expiresRaw || !providedSignature) return false
  const expiresAt = Number(expiresRaw)
  if (!Number.isInteger(expiresAt) || expiresAt <= Math.floor(Date.now() / 1000)) return false

  const expectedSignature = signExpiry(expiresAt)
  if (!expectedSignature) return false
  const left = Buffer.from(providedSignature)
  const right = Buffer.from(expectedSignature)
  if (left.length !== right.length) return false
  return timingSafeEqual(left, right)
}
