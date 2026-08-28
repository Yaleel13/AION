"use client"

import { useCallback, useEffect, useState } from "react"
import { Loader2, RefreshCw, Send, ShieldAlert } from "lucide-react"

type Approval = {
  request_id: string
  action: string
  summary: string
  destination: string
  decision: string
  content_hash: string
  expires_at: string
}

type ControlledStatus = {
  outbound_enabled: boolean
  execute_enabled: boolean
  ready: boolean
  allowed_action: string
  send_quota_per_24h: number
  sent_last_24h: number
  remaining_last_24h: number
}

type ApprovalResponse = {
  ok: boolean
  approvals: Approval[]
  pending_count: number
  outbound_enabled: boolean
  execute_enabled: boolean
  controlled_outbound?: ControlledStatus
  published?: boolean
  note?: string
  error?: string
}

export function OwnerControlledOutbound() {
  const [data, setData] = useState<ApprovalResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [sendingId, setSendingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/owner/moltbook-approvals", { cache: "no-store" })
      const body = (await response.json()) as ApprovalResponse
      if (!response.ok || !body.ok) throw new Error(body.error || `Controlled outbound load failed (${response.status})`)
      setData(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Controlled outbound unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  const approveAndSend = useCallback(async (approval: Approval) => {
    setSendingId(approval.request_id)
    setSuccess(null)
    try {
      const response = await fetch("/api/owner/moltbook-approvals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          operation: "approve_and_execute",
          request_id: approval.request_id,
          expected_content_hash: approval.content_hash,
        }),
        cache: "no-store",
      })
      const body = (await response.json()) as ApprovalResponse
      if (!response.ok || !body.ok) throw new Error(body.error || `Send failed (${response.status})`)
      setData(body)
      setSuccess(body.published ? "Moltbook confirmed the owner-approved comment." : "No publish confirmation was returned.")
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Controlled send unavailable")
    } finally {
      setSendingId(null)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  if (loading && !data) {
    return <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Loading controlled outbound gates…</div>
  }

  const status = data?.controlled_outbound
  const pending = (data?.approvals ?? []).filter((item) => item.decision === "pending" && item.action === "comment")

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-2xl">
          <p className="text-sm font-medium text-foreground">Owner-approved comments only</p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">A send requires this owner action, the exact stored content hash, a pending proposal, a clear kill switch, and both deployment gates. No DMs, posts, follows, or autonomous writes are supported.</p>
        </div>
        <button type="button" onClick={() => void load()} disabled={Boolean(sendingId)} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs text-foreground hover:bg-muted disabled:opacity-60"><RefreshCw className="h-3.5 w-3.5" />Refresh</button>
      </div>

      {error ? <p className="rounded-lg border border-critical/30 bg-critical/5 p-3 text-xs text-critical">{error}</p> : null}
      {success ? <p className="rounded-lg border border-positive/30 bg-positive/5 p-3 text-xs text-positive">{success}</p> : null}

      <div className="grid gap-2 sm:grid-cols-4">
        <div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Outbound gate</p><p className="mt-1 text-sm font-medium text-foreground">{status?.outbound_enabled ? "Enabled" : "Locked"}</p></div>
        <div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Execution gate</p><p className="mt-1 text-sm font-medium text-foreground">{status?.execute_enabled ? "Enabled" : "Locked"}</p></div>
        <div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Sent / 24h</p><p className="mt-1 text-sm font-medium text-foreground">{status?.sent_last_24h ?? 0} / {status?.send_quota_per_24h ?? 3}</p></div>
        <div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Capability</p><p className="mt-1 text-sm font-medium text-foreground">{status?.ready ? "Owner-approved comment" : "Inactive"}</p></div>
      </div>

      {!status?.ready ? <div className="flex items-start gap-3 rounded-xl border border-caution/30 bg-caution/5 p-4"><ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-caution" /><p className="text-xs leading-relaxed text-muted-foreground">Controlled outbound infrastructure is installed but inactive. It remains fail-closed until both production deployment gates are explicitly enabled.</p></div> : null}

      {pending.length ? <div className="space-y-2">
        {pending.map((approval) => (
          <article key={approval.request_id} className="rounded-xl border border-border/70 bg-background/35 p-4">
            <p className="text-sm font-medium text-foreground">{approval.summary}</p>
            <p className="mt-1 text-xs text-muted-foreground">{approval.destination} · expires {new Date(approval.expires_at).toLocaleString()}</p>
            <div className="mt-3 flex justify-end">
              <button type="button" disabled={!status?.ready || Boolean(sendingId)} onClick={() => void approveAndSend(approval)} className="inline-flex items-center gap-2 rounded-lg border border-gold/40 bg-gold/10 px-3 py-2 text-xs font-medium text-gold hover:bg-gold/15 disabled:cursor-not-allowed disabled:opacity-40">{sendingId === approval.request_id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}Approve &amp; Send</button>
            </div>
          </article>
        ))}
      </div> : <p className="rounded-xl border border-border/70 bg-background/35 p-4 text-sm text-muted-foreground">No pending comment proposals are available for controlled sending.</p>}
    </div>
  )
}
