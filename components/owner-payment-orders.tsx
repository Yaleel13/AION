"use client"

import { useCallback, useEffect, useState } from "react"
import { Loader2, RefreshCw } from "lucide-react"
import { defer } from "@/lib/defer"

type PaymentOrder = {
  order_id: string
  opportunity_id: string
  amount_cents: number
  currency: string
  status: "pending_owner_approval" | "paid" | "fulfilled"
  created_at: string
  updated_at: string
  stripe_session_id: string
  customer_email: string
}

type PaymentOrdersData = {
  all: PaymentOrder[]
  pending_approval: PaymentOrder[]
  paid_awaiting_fulfillment: PaymentOrder[]
  fulfilled: PaymentOrder[]
  total_paid_amount_cents: number
  total_fulfilled_amount_cents: number
}

type DashboardResponse = {
  payment_orders?: PaymentOrdersData
  error?: string
  [key: string]: unknown
}

type FulfillResponse = {
  status: string
  orders_processed: number
  results: Array<{ order_id: string; status: string }>
  note: string
  error?: string
}

export function OwnerPaymentOrders() {
  const [paymentData, setPaymentData] = useState<PaymentOrdersData | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetch("/api/owner/dashboard", { cache: "no-store" })
      const body = (await response.json()) as DashboardResponse
      if (!response.ok) throw new Error(body.error || `Dashboard load failed (${response.status})`)
      setPaymentData(body.payment_orders || null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Failed to load payment data")
    } finally {
      setLoading(false)
    }
  }, [])

  const fulfill = useCallback(async () => {
    setBusy(true)
    setMessage(null)
    setError(null)
    try {
      const response = await fetch("/api/owner/fulfill/paid-orders", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
      const body = (await response.json()) as FulfillResponse
      if (!response.ok) throw new Error(body.error || `Fulfillment failed (${response.status})`)
      setMessage(`${body.orders_processed} order(s) fulfilled successfully`)
      await load()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Fulfillment request failed")
    } finally {
      setBusy(false)
    }
  }, [load])

  useEffect(() => {
    defer(() => { void load() })
    const refresh = () => void load()
    window.addEventListener("aion:boardroom-refresh", refresh)
    return () => window.removeEventListener("aion:boardroom-refresh", refresh)
  }, [load])

  if (loading && !paymentData) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading payment data…
      </div>
    )
  }

  if (!paymentData) {
    return <div className="text-xs text-muted-foreground">No payment data available</div>
  }

  const formatCents = (cents: number) => `$${(cents / 100).toFixed(2)}`

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">Payment orders</p>
          <p className="mt-1 text-xs text-muted-foreground">Track payment processing and fulfillment</p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs hover:bg-muted disabled:opacity-60"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          Refresh
        </button>
      </div>

      {error && <p className="rounded-lg border border-critical/30 bg-critical/5 p-3 text-xs text-critical">{error}</p>}
      {message && (
        <p className="rounded-lg border border-positive/30 bg-positive/5 p-3 text-xs text-positive">{message}</p>
      )}

      <div className="grid gap-2 sm:grid-cols-3">
        <div className="rounded-lg border border-border/70 bg-background/40 p-3">
          <p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Pending approval</p>
          <p className="mt-1 text-sm font-medium text-foreground">{paymentData.pending_approval.length}</p>
        </div>
        <div className="rounded-lg border border-border/70 bg-background/40 p-3">
          <p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Paid (awaiting fulfillment)</p>
          <p className="mt-1 text-sm font-medium text-foreground">{paymentData.paid_awaiting_fulfillment.length}</p>
          <p className="mt-1 text-[0.65rem] text-muted-foreground">{formatCents(paymentData.total_paid_amount_cents)}</p>
        </div>
        <div className="rounded-lg border border-border/70 bg-background/40 p-3">
          <p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Fulfilled</p>
          <p className="mt-1 text-sm font-medium text-foreground">{paymentData.fulfilled.length}</p>
          <p className="mt-1 text-[0.65rem] text-muted-foreground">{formatCents(paymentData.total_fulfilled_amount_cents)}</p>
        </div>
      </div>

      {paymentData.paid_awaiting_fulfillment.length > 0 && (
        <div className="rounded-lg border border-gold/40 bg-gold/5 p-4">
          <p className="text-xs font-medium text-gold">
            {paymentData.paid_awaiting_fulfillment.length} order(s) ready for fulfillment
          </p>
          <button
            type="button"
            disabled={busy}
            onClick={() => void fulfill()}
            className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-gold/10 px-3 py-1.5 text-xs font-medium text-gold hover:bg-gold/20 disabled:opacity-60"
          >
            {busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <span>→</span>}
            Fulfill paid orders
          </button>
        </div>
      )}

      {paymentData.all.length > 0 && (
        <div className="rounded-lg border border-border/70 bg-background/35 p-4">
          <p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground mb-3">Recent orders</p>
          <div className="max-h-64 space-y-2 overflow-auto">
            {paymentData.all.slice(0, 10).map((order) => (
              <div key={order.order_id} className="border-b border-border/40 pb-2">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <p className="text-xs font-mono text-foreground/80 truncate">{order.order_id}</p>
                    <p className="text-[0.65rem] text-muted-foreground">
                      {order.customer_email} · {new Date(order.created_at).toLocaleDateString()}
                    </p>
                  </div>
                  <span
                    className={`text-xs font-medium px-2 py-1 rounded whitespace-nowrap ${
                      order.status === "fulfilled"
                        ? "bg-positive/20 text-positive"
                        : order.status === "paid"
                          ? "bg-caution/20 text-caution"
                          : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {order.status === "pending_owner_approval" ? "Pending" : order.status}
                  </span>
                </div>
                <p className="text-xs text-foreground/70 mt-1">{formatCents(order.amount_cents)}</p>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
