"use client"

import { useCallback, useEffect, useState } from "react"
import { Copy, ExternalLink, Loader2, RefreshCw, ShoppingCart } from "lucide-react"
import { defer } from "@/lib/defer"
import { AION_REQUEST_HEADER } from "@/lib/aion/owner-session"

type SalesItem = {
  lead_id: string
  confidence: number
  service: string
  problem: string
  requester: string
  source_url: string
  conversion_channel: string
  conversion_outcome: string
  suggested_response: string
  matched_venture: string
  matched_product: string
  matched_product_key: string
  sale_status: string
  shared_checkout_url: string | null
  next_action: string
}

type SalesResponse = {
  ok: boolean
  count: number
  sales_queue: SalesItem[]
  error?: string
}

type ConversionChannel = "moltbook_comment" | "owner_direct_alert" | ""

function asConversionChannel(value: string): ConversionChannel {
  if (value === "moltbook_comment" || value === "owner_direct_alert") return value
  return ""
}

function channelLabel(channel: ConversionChannel): string {
  switch (channel) {
    case "moltbook_comment":
      return "Moltbook comment"
    case "owner_direct_alert":
      return "Owner reply on source"
    case "":
      return "Review"
    default: {
      const _exhaustive: never = channel
      return _exhaustive
    }
  }
}

export function OwnerSalesQueue() {
  const [data, setData] = useState<SalesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [acting, setActing] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/owner/sales-alerts", { cache: "no-store" })
      const body = (await response.json()) as SalesResponse
      if (!response.ok || !body.ok) throw new Error(body.error || `Sales queue failed (${response.status})`)
      setData(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Sales queue unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  const prepareCheckout = useCallback(async (leadId: string) => {
    setActing(leadId)
    setNotice(null)
    try {
      const response = await fetch("/api/owner/sales-alerts", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...AION_REQUEST_HEADER },
        body: JSON.stringify({ operation: "prepare_checkout", lead_id: leadId }),
        cache: "no-store",
      })
      const body = (await response.json()) as { ok?: boolean; error?: string; checkout?: { checkout_url?: string }; note?: string }
      if (!response.ok || !body.ok) throw new Error(body.error || `Checkout prepare failed (${response.status})`)
      const url = body.checkout?.checkout_url
      setNotice(url ? `Checkout ready: ${url}` : body.note || "Checkout prepared.")
      window.dispatchEvent(new CustomEvent("aion:boardroom-refresh", { detail: { source: "sales-queue" } }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Checkout prepare failed")
    } finally {
      setActing(null)
    }
  }, [])

  const copyText = useCallback(async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setNotice("Reply draft copied.")
    } catch {
      setNotice("Could not copy. Select the draft text manually.")
    }
  }, [])

  useEffect(() => {
    defer(() => { void load() })
    const refresh = () => void load()
    window.addEventListener("aion:boardroom-refresh", refresh)
    return () => window.removeEventListener("aion:boardroom-refresh", refresh)
  }, [load])

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">Qualified buyer queue</p>
          <p className="mt-1 text-xs text-muted-foreground">
            High-confidence leads from Moltbook, Reddit, GitHub, and Hacker News.
            AION never auto-comments on Reddit, GitHub, or HN — copy the draft and reply yourself.
          </p>
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

      {error ? (
        <p className="rounded-lg border border-critical/30 bg-critical/5 p-3 text-xs text-critical">{error}</p>
      ) : null}
      {notice ? (
        <p className="rounded-lg border border-positive/30 bg-positive/5 p-3 text-xs text-positive">{notice}</p>
      ) : null}

      {data?.sales_queue?.length ? (
        <ul className="space-y-3">
          {data.sales_queue.map((item) => (
            <li key={item.lead_id} className="rounded-xl border border-border/70 bg-background/35 p-4">
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-sm font-medium text-foreground">{item.matched_product}</p>
                  <p className="mt-1 text-[0.65rem] uppercase tracking-wider text-muted-foreground">
                    {item.matched_venture} · {channelLabel(asConversionChannel(item.conversion_channel))} · {Math.round(item.confidence * 100)}%
                  </p>
                </div>
                <a
                  href={item.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-gold hover:underline"
                >
                  Open source <ExternalLink className="h-3 w-3" />
                </a>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-foreground/85">{item.problem}</p>
              {item.suggested_response ? (
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{item.suggested_response}</p>
              ) : null}
              <div className="mt-3 flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void copyText(item.suggested_response)}
                  disabled={!item.suggested_response}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs hover:bg-muted disabled:opacity-50"
                >
                  <Copy className="h-3.5 w-3.5" />
                  Copy reply
                </button>
                <button
                  type="button"
                  onClick={() => void prepareCheckout(item.lead_id)}
                  disabled={acting === item.lead_id || !item.shared_checkout_url}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-positive/40 bg-positive/10 px-2.5 py-1.5 text-xs font-medium text-positive hover:bg-positive/20 disabled:opacity-50"
                >
                  {acting === item.lead_id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShoppingCart className="h-3.5 w-3.5" />}
                  Prepare checkout
                </button>
                {item.shared_checkout_url ? (
                  <a
                    href={item.shared_checkout_url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs hover:bg-muted"
                  >
                    Shared Stripe link <ExternalLink className="h-3 w-3" />
                  </a>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      ) : loading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading sales queue…
        </div>
      ) : (
        <p className="text-xs text-muted-foreground">No qualified buyers in the queue yet. Cron discovery will fill this when public buyer-intent posts appear.</p>
      )}
    </div>
  )
}
