import { hasValidOwnerSession, requireCsrfHeader } from "@/lib/aion/owner-session"

type CheckoutResponse = {
  checkout?: {
    session_id?: string
    checkout_url?: string
  }
  detail?: string
}

export async function POST(req: Request) {
  if (!hasValidOwnerSession(req.headers.get("cookie"))) {
    return Response.json({ error: "Owner authentication required." }, { status: 401 })
  }
  const csrfError = requireCsrfHeader(req)
  if (csrfError) return csrfError
  if (!process.env.AION_OWNER_TOKEN) {
    return Response.json({ error: "AION owner authentication is not configured." }, { status: 503 })
  }

  const verificationId = crypto.randomUUID()
  const origin = new URL(req.url).origin

  try {
    const response = await fetch(new URL("/api/owner/checkout/prepare", req.url), {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.AION_OWNER_TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        order_id: `verify-${verificationId}`,
        opportunity_id: `stripe-live-verification-${verificationId}`,
        amount_cents: 100,
        currency: "usd",
        success_url: `${origin}/?checkout=verified`,
      }),
      cache: "no-store",
    })
    const data = (await response.json()) as CheckoutResponse
    if (!response.ok) {
      return Response.json(
        { error: data.detail || "Stripe Checkout verification failed." },
        { status: response.status },
      )
    }

    const sessionId = data.checkout?.session_id ?? ""
    const checkoutUrl = data.checkout?.checkout_url ?? ""
    if (!sessionId.startsWith("cs_live_") || !checkoutUrl.startsWith("https://checkout.stripe.com/")) {
      return Response.json({ error: "Stripe did not return a live Checkout session." }, { status: 502 })
    }

    return Response.json(
      {
        verified: true,
        live: true,
        session_id: sessionId,
        checkout_url: checkoutUrl,
        amount_cents: 100,
        charged: false,
      },
      { headers: { "Cache-Control": "no-store" } },
    )
  } catch (error) {
    console.error("[AION] Payment rail verification error:", error instanceof Error ? error.message : String(error))
    return Response.json({ error: "Payment rail verification is temporarily unavailable." }, { status: 500 })
  }
}
