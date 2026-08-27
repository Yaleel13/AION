import { createHmac, timingSafeEqual } from "node:crypto"

export const OWNER_SESSION_COOKIE = "aion_owner_session"
const OWNER_SESSION_CONTEXT = "aion-owner-session-v1"

function ownerToken() {
  return (process.env.AION_OWNER_TOKEN ?? "").trim()
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

export function ownerSessionValue() {
  const secret = ownerToken()
  if (!secret) return null
  return createHmac("sha256", secret).update(OWNER_SESSION_CONTEXT).digest("hex")
}

export function hasValidOwnerSession(cookieHeader: string | null) {
  const expected = ownerSessionValue()
  if (!expected || !cookieHeader) return false
  const cookies = cookieHeader.split(";").map((part) => part.trim())
  const raw = cookies
    .find((part) => part.startsWith(`${OWNER_SESSION_COOKIE}=`))
    ?.slice(OWNER_SESSION_COOKIE.length + 1)
  if (!raw) return false

  const left = Buffer.from(raw)
  const right = Buffer.from(expected)
  if (left.length !== right.length) return false
  return timingSafeEqual(left, right)
}
