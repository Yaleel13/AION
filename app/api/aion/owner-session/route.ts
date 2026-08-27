import {
  OWNER_SESSION_COOKIE,
  hasValidOwnerSession,
  ownerSessionConfigured,
  ownerSessionValue,
  verifyOwnerToken,
} from "@/lib/aion/owner-session"

const COOKIE_MAX_AGE_SECONDS = 8 * 60 * 60

type OwnerSessionBody = {
  token?: string
}

export async function GET(req: Request) {
  return Response.json({
    configured: ownerSessionConfigured(),
    authenticated: hasValidOwnerSession(req.headers.get("cookie")),
  })
}

export async function POST(req: Request) {
  if (!ownerSessionConfigured()) {
    return Response.json({ error: "AION owner authentication is not configured." }, { status: 503 })
  }

  let body: OwnerSessionBody
  try {
    body = (await req.json()) as OwnerSessionBody
  } catch {
    return Response.json({ error: "A valid JSON body is required." }, { status: 400 })
  }

  if (!verifyOwnerToken(body.token?.trim() ?? "")) {
    return Response.json({ error: "Invalid owner token." }, { status: 403 })
  }

  const session = ownerSessionValue()
  if (!session) {
    return Response.json({ error: "AION owner authentication is not configured." }, { status: 503 })
  }

  return new Response(JSON.stringify({ authenticated: true }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Set-Cookie": `${OWNER_SESSION_COOKIE}=${session}; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=${COOKIE_MAX_AGE_SECONDS}`,
      "Cache-Control": "no-store",
    },
  })
}

export async function DELETE() {
  return new Response(JSON.stringify({ authenticated: false }), {
    status: 200,
    headers: {
      "Content-Type": "application/json",
      "Set-Cookie": `${OWNER_SESSION_COOKIE}=; HttpOnly; Secure; SameSite=Strict; Path=/; Max-Age=0`,
      "Cache-Control": "no-store",
    },
  })
}
