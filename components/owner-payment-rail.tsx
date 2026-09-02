"use client"

import { useState } from "react"
import { CreditCard, Loader2 } from "lucide-react"

type VerificationResult = {
  verified?: boolean
  live?: boolean
  session_id?: string
  checkout_url?: string
  amount_cents?: number
  charged?: boolean
  error?: string
}

export function OwnerPaymentRail() {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<VerificationResult | null>(null)

  async function verify() {
    setBusy(true)
    setResult(null)
    try {
      const response = await fetch("/api/owner/payment-rail", { method: "POST" })
      const body = (await response.json()) as VerificationResult
      if (!response.ok) throw new Error(body.error || `Payment verification failed (${response.status})`)
      setResult(body)
    } catch (reason) {
      setResult({ error: reason instanceof Error ? reason.message : "Payment verification failed" })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-3">
      <p className="text-sm leading-relaxed text-foreground/90">
        Create an unpaid $1 live Checkout session to verify Stripe credentials, Checkout access, and the payment ledger.
      </p>
      <button
        type="button"
        onClick={() => void verify()}
        disabled={busy}
        className="inline-flex min-h-10 items-center gap-2 border border-cyan/25 bg-cyan/5 px-3 py-2 text-xs font-medium text-foreground transition-colors hover:bg-cyan/10 disabled:opacity-60"
      >
        {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <CreditCard className="h-4 w-4" />}
        Verify live Checkout
      </button>
      {result?.error ? (
        <p className="border border-critical/25 bg-critical/5 p-3 text-xs text-critical">{result.error}</p>
      ) : null}
      {result?.verified ? (
        <div className="border border-positive/25 bg-positive/5 p-3 text-xs text-foreground/90">
          <p className="font-medium text-positive">Live Checkout verified</p>
          <p className="mt-1 font-mono">{result.session_id}</p>
          <p className="mt-1 text-muted-foreground">No charge was completed.</p>
          {result.checkout_url ? (
            <a className="mt-2 inline-block text-cyan underline-offset-4 hover:underline" href={result.checkout_url} target="_blank" rel="noreferrer">
              Inspect unpaid Checkout
            </a>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}
