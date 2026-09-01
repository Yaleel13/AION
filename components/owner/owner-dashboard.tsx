"use client"

import { useCallback, useState, startTransition } from "react"
import { OwnerPaymentOrders } from "@/components/owner-payment-orders"

type Dashboard = {
  phase?: string
  kill_switch?: { engaged?: boolean; reason?: string }
  drafts_awaiting_approval?: Array<Record<string, unknown>>
  approvals_pending?: Array<Record<string, unknown>>
  approvals_approved?: Array<Record<string, unknown>>
  approvals_rejected?: Array<Record<string, unknown>>
  qualified_leads?: Array<Record<string, unknown>>
  attributed_revenue_total?: number
  paper_trading?: Record<string, unknown>
  search_categories?: string[]
  audit_history?: Array<Record<string, unknown>>
  risk_status?: Record<string, unknown>
  controlled_autonomy?: Record<string, unknown>
  storage?: Record<string, unknown>
  error?: string
}

function Panel({
  title,
  children,
}: {
  title: string
  children: React.ReactNode
}) {
  return (
    <section className="border border-border/70 bg-surface/80 p-4 backdrop-blur">
      <h2 className="mb-3 font-serif text-xl tracking-tight text-gold">{title}</h2>
      <div className="text-sm text-muted-foreground">{children}</div>
    </section>
  )
}

export function OwnerDashboard() {
  const [data, setData] = useState<Dashboard | null>(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string>(
    "Click Refresh to load the Phase 2 control snapshot from the local API."
  )
  const [loadedOnce, setLoadedOnce] = useState(false)

  const refresh = useCallback(async () => {
    setBusy(true)
    try {
      const res = await fetch("/api/owner/dashboard", { cache: "no-store" })
      const json = (await res.json()) as Dashboard
      startTransition(() => {
        setData(json)
        setLoadedOnce(true)
        if (!res.ok) setMessage(json.error || "Failed to load dashboard")
        else setMessage("")
      })
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Network error")
    } finally {
      setBusy(false)
    }
  }, [])

  async function postAction(path: string) {
    setBusy(true)
    setMessage("")
    try {
      const res = await fetch(path, { method: "POST" })
      const json = await res.json()
      if (!res.ok) setMessage(json.error || json.detail || "Action failed")
      else setMessage(json.message || "OK")
      await refresh()
    } catch (err) {
      setMessage(err instanceof Error ? err.message : "Network error")
    } finally {
      setBusy(false)
    }
  }

  const kill = data?.kill_switch?.engaged

  return (
    <main className="min-h-screen bg-[radial-gradient(ellipse_at_top,_#1a1630_0%,_#0b0b10_55%)] px-4 py-10 text-foreground md:px-8">
      <div className="mx-auto max-w-6xl">
        <header className="mb-8">
          <p className="text-xs uppercase tracking-[0.25em] text-violet">AION · Phase 2</p>
          <h1 className="mt-2 font-serif text-4xl text-gold md:text-5xl">Owner control room</h1>
          <p className="mt-3 max-w-2xl text-sm text-muted-foreground">
            Drafts, approvals, YaliTek lead review, and paper trading. Nothing publishes or
            trades live from this screen without separate explicit execution enablement.
          </p>
          <div className="mt-4 flex flex-wrap gap-2">
            <button
              type="button"
              disabled={busy}
              onClick={() => void refresh()}
              className="border border-border px-3 py-1.5 text-xs uppercase tracking-wide hover:border-gold"
            >
              Refresh
            </button>
            <button
              type="button"
              disabled={busy || !loadedOnce}
              onClick={() => void postAction("/api/owner/campaign/seed")}
              className="border border-border px-3 py-1.5 text-xs uppercase tracking-wide hover:border-gold disabled:opacity-40"
            >
              Seed 14-day drafts
            </button>
            <button
              type="button"
              disabled={busy || !loadedOnce}
              onClick={() => void postAction("/api/owner/leads/scan")}
              className="border border-border px-3 py-1.5 text-xs uppercase tracking-wide hover:border-gold disabled:opacity-40"
            >
              Scan leads
            </button>
            <button
              type="button"
              disabled={busy || !loadedOnce}
              onClick={() => void postAction("/api/owner/paper/tick")}
              className="border border-border px-3 py-1.5 text-xs uppercase tracking-wide hover:border-gold disabled:opacity-40"
            >
              Paper tick
            </button>
            <button
              type="button"
              disabled={busy || !loadedOnce}
              onClick={() => void postAction("/api/owner/autonomy/daily-report")}
              className="border border-border px-3 py-1.5 text-xs uppercase tracking-wide hover:border-gold disabled:opacity-40"
            >
              Autonomy daily report
            </button>
            <button
              type="button"
              disabled={busy || !loadedOnce}
              onClick={() =>
                void postAction(
                  kill ? "/api/owner/kill-switch?engage=0" : "/api/owner/kill-switch?engage=1"
                )
              }
              className="border border-critical/60 px-3 py-1.5 text-xs uppercase tracking-wide text-critical hover:border-critical disabled:opacity-40"
            >
              {kill ? "Release kill switch" : "Engage kill switch"}
            </button>
          </div>
          {message ? <p className="mt-3 text-xs text-caution">{message}
        {data?.storage ? (
          <p className="mt-2 text-xs text-muted-foreground">
            Storage: {String(data.storage.backend)} — {String(data.storage.detail || "")}
          </p>
        ) : null}</p> : null}
        </header>

        <div className="grid gap-4 md:grid-cols-2">
          <Panel title="Risk status">
            <p>Phase: {data?.phase || "—"}</p>
            <p>Kill switch: {kill ? `ENGAGED (${data?.kill_switch?.reason || ""})` : "off"}</p>
            <pre className="mt-2 overflow-auto whitespace-pre-wrap text-[11px] text-foreground/80">
              {JSON.stringify(data?.risk_status || {}, null, 2)}
            </pre>
          </Panel>

          <Panel title="Paper trading">
            <pre className="overflow-auto whitespace-pre-wrap text-[11px] text-foreground/80">
              {JSON.stringify(data?.paper_trading || {}, null, 2)}
            </pre>
          </Panel>

          <Panel title="Drafts awaiting approval">
            <p className="mb-2">{data?.drafts_awaiting_approval?.length || 0} drafts</p>
            <ul className="max-h-64 space-y-2 overflow-auto">
              {(data?.drafts_awaiting_approval || []).map((d) => (
                <li key={String(d.draft_id)} className="border-b border-border/40 pb-2">
                  <div className="text-foreground">
                    Day {String(d.day_index)} — {String(d.title)}
                  </div>
                  <div className="text-[11px]">
                    {String(d.theme)} · {String(d.submolt)}
                  </div>
                </li>
              ))}
            </ul>
          </Panel>

          <Panel title="Approval queue">
            <p>Pending: {data?.approvals_pending?.length || 0}</p>
            <p>Approved/executed: {data?.approvals_approved?.length || 0}</p>
            <p>Rejected: {data?.approvals_rejected?.length || 0}</p>
            <pre className="mt-2 max-h-64 overflow-auto whitespace-pre-wrap text-[11px]">
              {JSON.stringify(data?.approvals_pending || [], null, 2)}
            </pre>
          </Panel>

          <Panel title="Controlled autonomy">
            <p className="mb-2 text-[11px]">
              Quotas are ceilings, not targets. Live writes require activation + open
              experiment window. Platform rate limits always override owner caps.
            </p>
            {data?.controlled_autonomy?.quota_availability ? (
              <div className="mb-3 space-y-1 text-foreground">
                <p>
                  Posts:{" "}
                  {String(
                    (data.controlled_autonomy.quota_availability as Record<string, Record<string, unknown>>)
                      ?.create_post?.count ?? "—"
                  )}
                  /
                  {String(
                    (data.controlled_autonomy.quota_availability as Record<string, Record<string, unknown>>)
                      ?.create_post?.limit ?? "—"
                  )}{" "}
                  (24h)
                </p>
                <p>
                  Comments:{" "}
                  {String(
                    (data.controlled_autonomy.quota_availability as Record<string, Record<string, unknown>>)
                      ?.comment?.count ?? "—"
                  )}
                  /
                  {String(
                    (data.controlled_autonomy.quota_availability as Record<string, Record<string, unknown>>)
                      ?.comment?.limit ?? "—"
                  )}{" "}
                  (24h)
                </p>
                <p>
                  Follows:{" "}
                  {String(
                    (data.controlled_autonomy.quota_availability as Record<string, Record<string, unknown>>)
                      ?.follow?.count ?? "—"
                  )}
                  /
                  {String(
                    (data.controlled_autonomy.quota_availability as Record<string, Record<string, unknown>>)
                      ?.follow?.limit ?? "—"
                  )}{" "}
                  (7d)
                </p>
                <p>
                  Auto-reduced:{" "}
                  {String(
                    (data.controlled_autonomy.automatic_quota_reduction as Record<string, unknown>)
                      ?.active
                      ? "yes"
                      : "no"
                  )}
                </p>
              </div>
            ) : null}
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-[11px] text-foreground/80">
              {JSON.stringify(data?.controlled_autonomy || {}, null, 2)}
            </pre>
          </Panel>

          <Panel title="Qualified leads">
            <p className="mb-1">
              Count: {data?.qualified_leads?.length || 0} · Attributed revenue: $
              {Number(data?.attributed_revenue_total || 0).toFixed(2)}
            </p>
            <p className="mb-2 text-[11px]">
              Categories: {(data?.search_categories || []).join(" · ")}
            </p>
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap text-[11px]">
              {JSON.stringify(data?.qualified_leads || [], null, 2)}
            </pre>
          </Panel>

          <Panel title="Payment orders">
            <OwnerPaymentOrders />
          </Panel>

          <Panel title="Audit history">
            <pre className="max-h-80 overflow-auto whitespace-pre-wrap text-[11px]">
              {JSON.stringify(data?.audit_history || [], null, 2)}
            </pre>
          </Panel>
        </div>
      </div>
    </main>
  )
}
