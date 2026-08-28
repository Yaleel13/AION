"use client"

import { useCallback, useEffect, useState } from "react"
import { Loader2, RefreshCw, ShieldCheck, XCircle } from "lucide-react"

type Approval = {
  request_id: string
  action: string
  summary: string
  destination: string
  decision: string
  content_hash: string
  created_at: string
  expires_at: string
}

type ApprovalResponse = {
  ok: boolean
  stage: number
  mode: string
  pending_count: number
  prepared_count: number
  approvals: Approval[]
  outbound_enabled: boolean
  execute_enabled: boolean
  published: boolean
  note: string
  error?: string
}

export function OwnerMoltbookApprovals() {
  const [data, setData] = useState<ApprovalResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/owner/moltbook-approvals", { cache: "no-store" })
      const body = (await response.json()) as ApprovalResponse
      if (!response.ok || !body.ok) throw new Error(body.error || `Approval load failed (${response.status})`)
      setData(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Approval preflight unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  const mutate = useCallback(async (payload: Record<string, unknown>) => {
    setWorking(true)
    try {
      const response = await fetch("/api/owner/moltbook-approvals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
      })
      const body = (await response.json()) as ApprovalResponse
      if (!response.ok || !body.ok) throw new Error(body.error || `Approval mutation failed (${response.status})`)
      setData(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Approval preflight unavailable")
    } finally {
      setWorking(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  if (loading && !data) {
    return <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Loading approval preflight…</div>
  }

  const pending = data?.approvals?.filter((item) => item.decision === "pending") ?? []

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">Approval preflight</p>
          <p className="mt-1 text-xs text-muted-foreground">Creates durable owner-review proposals from prepared opportunities. Approve-and-publish is intentionally unavailable.</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => void load()} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs text-foreground hover:bg-muted"><RefreshCw className="h-3.5 w-3.5" />Refresh</button>
          <button type="button" onClick={() => void mutate({ operation: "propose_prepared" })} disabled={working} className="inline-flex items-center gap-2 rounded-lg border border-gold/40 bg-gold/10 px-3 py-2 text-xs font-medium text-gold hover:bg-gold/15 disabled:opacity-60">{working ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}Propose Prepared</button>
        </div>
      </div>

      {error ? <p className="rounded-lg border border-critical/30 bg-critical/5 p-3 text-xs text-critical">{error}</p> : null}
      {data ? <p className="rounded-xl border border-border/70 bg-background/35 p-4 text-sm text-foreground/90">Pending {data.pending_count} · Prepared {data.prepared_count} · Outbound {data.outbound_enabled ? "enabled" : "locked"} · Execution {data.execute_enabled ? "enabled" : "locked"}</p> : null}

      {pending.length ? pending.map((item) => (
        <article key={item.request_id} className="rounded-xl border border-border/70 bg-background/35 p-4">
          <p className="text-xs uppercase tracking-wider text-muted-foreground">{item.action}</p>
          <p className="mt-1 text-sm font-medium text-foreground">{item.summary}</p>
          <p className="mt-1 text-xs text-muted-foreground">{item.destination}</p>
          <div className="mt-3 flex items-center justify-between gap-3">
            <span className="text-[0.7rem] text-gold">Pending owner review · no publish capability</span>
            <button type="button" disabled={working} onClick={() => void mutate({ operation: "reject", request_id: item.request_id, expected_content_hash: item.content_hash })} className="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-60"><XCircle className="h-3.5 w-3.5" />Reject</button>
          </div>
        </article>
      )) : (
        <p className="rounded-xl border border-border/70 bg-background/35 p-4 text-sm text-muted-foreground">No pending outbound proposals. If Stage 3 has no qualified opportunities, Stage 4 will create nothing.</p>
      )}
    </div>
  )
}
