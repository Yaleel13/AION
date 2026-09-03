"use client"

import { useCallback, useEffect, useState } from "react"
import { Activity, AlertTriangle, CheckCircle2, Loader2, Lock, RefreshCw, Unlock } from "lucide-react"
import { defer } from "@/lib/defer"
import { AION_REQUEST_HEADER } from "@/lib/aion/owner-session"

type GoLiveItem = {
  id: string
  ok: boolean
  label: string
  action: string
}

type GateStatus = {
  ok: boolean
  current_mode: string
  kill_switch_engaged: boolean
  moltbook_mode: string | null
  moltbook_api_key_set: boolean
  moltbook_outbound_enabled: boolean
  moltbook_execute_enabled: boolean
  moltbook_error?: string | null
  stripe_checkout_ready: boolean
  ready_for_revenue: boolean
  go_live_checklist: GoLiveItem[]
  blockers: string[]
  owner_actions: string[]
  ready_for_live_outbound: boolean
  note?: string
  error?: string
}

export function OwnerOutboundGates() {
  const [data, setData] = useState<GateStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [toggling, setToggling] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/owner/outbound-gates", { cache: "no-store" })
      const body = (await response.json()) as GateStatus
      if (!response.ok || !body.ok) throw new Error(body.error || `Gate status failed (${response.status})`)
      setData(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Outbound gate status unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  const toggle = useCallback(async (outbound: boolean, execute: boolean) => {
    setToggling(true)
    setNotice(null)
    try {
      const response = await fetch("/api/owner/outbound-gates", {
        method: "POST",
        headers: { "Content-Type": "application/json", ...AION_REQUEST_HEADER },
        body: JSON.stringify({ outbound_enabled: outbound, execute_enabled: execute }),
        cache: "no-store",
      })
      const body = (await response.json()) as GateStatus
      if (!response.ok || !body.ok) throw new Error(body.error || `Gate toggle failed (${response.status})`)
      setData(body)
      setNotice(body.note ?? (outbound ? "Outbound enabled for this invocation." : "Gates closed."))
      setError(null)
      window.dispatchEvent(new CustomEvent("aion:boardroom-refresh", { detail: { source: "outbound-gates" } }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Gate toggle failed")
    } finally {
      setToggling(false)
    }
  }, [])

  useEffect(() => {
    defer(() => { void load() })
    const refresh = () => void load()
    window.addEventListener("aion:boardroom-refresh", refresh)
    return () => window.removeEventListener("aion:boardroom-refresh", refresh)
  }, [load])

  const isReady = data?.ready_for_live_outbound
  const isOutboundOn = data?.moltbook_outbound_enabled
  const isExecuteOn = data?.moltbook_execute_enabled

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">Outbound activation</p>
          <p className="mt-1 text-xs text-muted-foreground">
            Controls whether AION can send public Moltbook replies to qualified buyers.
            Process-level toggles below are for testing; set Vercel env vars for durable activation.
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
      {data?.moltbook_error ? (
        <p className="rounded-lg border border-caution/30 bg-caution/5 p-3 text-xs text-caution">{data.moltbook_error}</p>
      ) : null}

      {data ? (
        <>
          {/* Status summary */}
          <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {[
              { label: "Mode", value: data.current_mode.replace(/_/g, " "), ok: isReady },
              { label: "Moltbook", value: data.moltbook_mode ?? "not set", ok: data.moltbook_mode === "live" },
              { label: "API key", value: data.moltbook_api_key_set ? "set" : "missing", ok: data.moltbook_api_key_set },
              { label: "Outbound gate", value: isOutboundOn ? "open" : "closed", ok: !!isOutboundOn },
              { label: "Execute gate", value: isExecuteOn ? "open" : "closed", ok: !!isExecuteOn },
              { label: "Stripe", value: data.stripe_checkout_ready ? "ready" : "not configured", ok: data.stripe_checkout_ready },
            ].map(({ label, value, ok }) => (
              <div key={label} className="rounded-lg border border-border/70 bg-background/40 p-3">
                <p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">{label}</p>
                <div className="mt-1 flex items-center gap-1.5">
                  {ok ? (
                    <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-positive" />
                  ) : (
                    <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-400" />
                  )}
                  <p className="text-xs font-medium text-foreground">{value}</p>
                </div>
              </div>
            ))}
          </div>

          {/* Go-live checklist */}
          {data.go_live_checklist?.length ? (
            <div className="rounded-xl border border-border/70 bg-background/35 p-4">
              <p className="mb-2 text-[0.65rem] uppercase tracking-wider text-muted-foreground">
                Revenue go-live checklist
              </p>
              <p className="mb-3 text-[0.65rem] text-muted-foreground">
                Checkout can run once kill switch, Postgres, owner token, cron secret, and Stripe are green.
                Moltbook outbound is separate and stays fail-closed until you set those env vars in Vercel.
              </p>
              <ul className="space-y-2">
                {data.go_live_checklist.map((item) => (
                  <li key={item.id} className="flex items-start gap-2">
                    {item.ok ? (
                      <CheckCircle2 className="mt-0.5 h-3.5 w-3.5 shrink-0 text-positive" />
                    ) : (
                      <AlertTriangle className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
                    )}
                    <div>
                      <p className="text-xs font-medium text-foreground">{item.label}</p>
                      {item.ok ? null : (
                        <p className="text-[0.65rem] leading-relaxed text-muted-foreground">{item.action}</p>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs text-muted-foreground">
                Revenue rails: {data.ready_for_revenue ? "ready" : "blocked"}. Durable activation is Vercel env, not the test toggle below.
              </p>
            </div>
          ) : null}

          {/* Blockers */}
          {data.blockers.length > 0 ? (
            <div className="rounded-xl border border-amber-400/20 bg-amber-400/5 p-4">
              <div className="mb-2 flex items-center gap-1.5">
                <Lock className="h-3.5 w-3.5 text-amber-400" />
                <p className="text-xs font-medium text-amber-300">Blockers ({data.blockers.length})</p>
              </div>
              <ul className="space-y-1">
                {data.blockers.map((b) => (
                  <li key={b} className="text-xs text-muted-foreground">• {b}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {/* Owner actions */}
          {data.owner_actions.length > 0 ? (
            <div className="rounded-xl border border-border/70 bg-background/35 p-4">
              <p className="mb-2 text-[0.65rem] uppercase tracking-wider text-muted-foreground">Required owner actions</p>
              <ul className="space-y-1.5">
                {data.owner_actions.map((a) => (
                  <li key={a} className="text-xs leading-relaxed text-foreground/85">→ {a}</li>
                ))}
              </ul>
            </div>
          ) : null}

          {/* Process-level toggle */}
          <div className="rounded-xl border border-border/70 bg-background/35 p-4">
            <p className="mb-1 text-xs font-medium text-foreground">Process-level test activation</p>
            <p className="mb-3 text-[0.65rem] text-muted-foreground">
              Applies only to this running Vercel function invocation — not persisted. Requires MOLTBOOK_MODE=live and API key to be set in env.
            </p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={toggling || data.kill_switch_engaged}
                onClick={() => void toggle(true, true)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-positive/40 bg-positive/10 px-3 py-1.5 text-xs font-medium text-positive hover:bg-positive/20 disabled:opacity-50"
              >
                {toggling ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Unlock className="h-3.5 w-3.5" />}
                Enable outbound + execute
              </button>
              <button
                type="button"
                disabled={toggling}
                onClick={() => void toggle(false, false)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-1.5 text-xs hover:bg-muted disabled:opacity-50"
              >
                {toggling ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Activity className="h-3.5 w-3.5" />}
                Close gates
              </button>
            </div>
          </div>
        </>
      ) : loading ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading gate status…
        </div>
      ) : null}
    </div>
  )
}
