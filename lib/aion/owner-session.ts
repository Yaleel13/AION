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
