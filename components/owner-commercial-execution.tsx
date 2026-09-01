"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { CheckCircle2, Loader2, Play, RefreshCw, Send, ShieldCheck, XCircle } from "lucide-react"
import { defer } from "@/lib/defer"

type ExecutionPlan = {
  opportunity_id: string
  executable: boolean
  channel: string
  reason: string
  destination: string
  payload: { post_id?: string; content?: string; parent_id?: string | null }
  authorization_required: string
  recommendation: string
  idempotency_key: string
}

type Approval = {
  request_id: string
  summary: string
  destination: string
  content_hash: string
  decision: string
}

type CommercialExecutionResponse = {
  ok: boolean
  mode: string
  plans: ExecutionPlan[]
  executable_count: number
  preparation_only_count: number
  outbound_enabled: boolean
  execute_enabled: boolean
  grant_submission_enabled: boolean
  federal_bid_submission_enabled: boolean
  generic_external_send_enabled: boolean
  note: string
  prepared?: { created: boolean; plan: ExecutionPlan; approval: Approval | null }
  approved?: Approval
  rejected?: Approval
  execution?: { published?: boolean; [key: string]: unknown }
  approval_token?: string
  token_note?: string
  error?: string
}

type PendingApproval = Approval & { opportunity_id: string }

export function OwnerCommercialExecution() {
  const [data, setData] = useState<CommercialExecutionResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [workingId, setWorkingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [pending, setPending] = useState<Record<string, PendingApproval>>({})
  const [tokens, setTokens] = useState<Record<string, string>>({})

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/owner/commercial-execution", { cache: "no-store" })
      const body = (await response.json()) as CommercialExecutionResponse
      if (!response.ok || !body.ok) throw new Error(body.error || `Commercial execution load failed (${response.status})`)
      setData(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Commercial execution controls unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  const mutate = useCallback(async (opportunityId: string, payload: Record<string, unknown>) => {
    setWorkingId(opportunityId)
    setNotice(null)
    try {
      const response = await fetch("/api/owner/commercial-execution", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
      })
      const body = (await response.json()) as CommercialExecutionResponse
      if (!response.ok || !body.ok) throw new Error(body.error || `Commercial execution action failed (${response.status})`)
      setData(body)
      setError(null)

      if (body.prepared?.approval) {
        setPending((current) => ({
          ...current,
          [opportunityId]: { ...body.prepared!.approval!, opportunity_id: opportunityId },
        }))
        setNotice(body.prepared.created ? "Prepared exact outbound content for owner review." : "Existing prepared approval loaded for review.")
      }
      if (body.approved && body.approval_token) {
        setPending((current) => ({
          ...current,
          [opportunityId]: { ...body.approved!, opportunity_id: opportunityId },
        }))
        setTokens((current) => ({ ...current, [opportunityId]: body.approval_token! }))
        setNotice("Approved. The single-use token is held only in this Boardroom session until you execute or leave.")
      }
      if (body.rejected) {
        setPending((current) => {
          const next = { ...current }
          delete next[opportunityId]
          return next
        })
        setTokens((current) => {
          const next = { ...current }
          delete next[opportunityId]
          return next
        })
        setNotice("Commercial outreach rejected. Nothing was sent.")
      }
      if (body.execution?.published) {
        setPending((current) => {
          const next = { ...current }
          delete next[opportunityId]
          return next
        })
        setTokens((current) => {
          const next = { ...current }
          delete next[opportunityId]
          return next
        })
        setNotice("Owner-approved commercial reply was published through the controlled executor.")
        window.dispatchEvent(new Event("aion:boardroom-refresh"))
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Commercial execution action failed")
    } finally {
      setWorkingId(null)
    }
  }, [])

  useEffect(() => { defer(() => { void load() }) }, [load])

  const executable = useMemo(() => data?.plans?.filter((plan) => plan.executable) ?? [], [data])
  const preparationOnly = useMemo(() => data?.plans?.filter((plan) => !plan.executable) ?? [], [data])

  if (loading && !data) {
    return <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Loading commercial execution controls…</div>
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">Controlled commercial execution</p>
          <p className="mt-1 max-w-3xl text-xs leading-relaxed text-muted-foreground">Only qualified public Moltbook replies can execute today. Prepare, approve, and execute remain separate owner actions; grant, federal bid, email, SMS, and generic social sending stay disabled.</p>
        </div>
        <button type="button" onClick={() => void load()} disabled={loading} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs text-foreground hover:bg-muted disabled:opacity-60"><RefreshCw className="h-3.5 w-3.5" />Refresh</button>
      </div>

      {error ? <p className="rounded-lg border border-critical/30 bg-critical/5 p-3 text-xs text-critical">{error}</p> : null}
      {notice ? <p className="rounded-lg border border-positive/30 bg-positive/5 p-3 text-xs text-positive">{notice}</p> : null}

      {data ? <div className="grid gap-2 sm:grid-cols-4">
        <div className="rounded-xl border border-border/70 bg-background/35 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Executable</p><p className="mt-1 text-lg font-medium text-foreground">{data.executable_count}</p></div>
        <div className="rounded-xl border border-border/70 bg-background/35 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Preparation only</p><p className="mt-1 text-lg font-medium text-foreground">{data.preparation_only_count}</p></div>
        <div className="rounded-xl border border-border/70 bg-background/35 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Outbound gate</p><p className="mt-1 text-sm font-medium text-foreground">{data.outbound_enabled ? "Enabled" : "Locked"}</p></div>
        <div className="rounded-xl border border-border/70 bg-background/35 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Execute gate</p><p className="mt-1 text-sm font-medium text-foreground">{data.execute_enabled ? "Enabled" : "Locked"}</p></div>
      </div> : null}

      {executable.length ? <div className="space-y-3">
        {executable.map((plan) => {
          const approval = pending[plan.opportunity_id]
          const token = tokens[plan.opportunity_id]
          const busy = workingId === plan.opportunity_id
          const approved = approval?.decision === "approved" && Boolean(token)
          return <article key={plan.opportunity_id} className="rounded-xl border border-gold/30 bg-gold/5 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <p className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-gold"><ShieldCheck className="h-3.5 w-3.5" />Execution eligible</p>
                <p className="mt-1 text-sm font-medium text-foreground">{plan.channel}</p>
                <p className="mt-1 break-all text-xs text-muted-foreground">{plan.destination}</p>
                <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{plan.reason}</p>
              </div>
              <span className="rounded-full border border-border px-2.5 py-1 text-[0.65rem] text-muted-foreground">{plan.recommendation.replaceAll("_", " ")}</span>
            </div>
            {plan.payload.content ? <div className="mt-3 rounded-lg border border-border/70 bg-background/50 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Exact proposed content</p><p className="mt-1 text-xs leading-relaxed text-foreground/90">{plan.payload.content}</p></div> : null}
            {approval ? <p className="mt-3 text-[0.7rem] text-muted-foreground">Approval {approval.decision} · hash {approval.content_hash.slice(0, 18)}…</p> : null}
            <div className="mt-3 flex flex-wrap gap-2">
              {!approval || approval.decision === "pending" ? <button type="button" disabled={busy} onClick={() => void mutate(plan.opportunity_id, { operation: "prepare", opportunity_id: plan.opportunity_id })} className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs text-foreground hover:bg-muted disabled:opacity-60">{busy ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}Prepare</button> : null}
              {approval?.decision === "pending" ? <>
                <button type="button" disabled={busy || !data?.outbound_enabled} onClick={() => void mutate(plan.opportunity_id, { operation: "approve", request_id: approval.request_id, expected_content_hash: approval.content_hash })} className="inline-flex items-center gap-1.5 rounded-lg border border-positive/40 bg-positive/10 px-3 py-2 text-xs font-medium text-positive hover:bg-positive/15 disabled:opacity-50"><CheckCircle2 className="h-3.5 w-3.5" />Approve exact content</button>
                <button type="button" disabled={busy} onClick={() => void mutate(plan.opportunity_id, { operation: "reject", request_id: approval.request_id, expected_content_hash: approval.content_hash })} className="inline-flex items-center gap-1.5 rounded-lg border border-border px-3 py-2 text-xs text-muted-foreground hover:bg-muted disabled:opacity-60"><XCircle className="h-3.5 w-3.5" />Reject</button>
              </> : null}
              {approved ? <button type="button" disabled={busy || !data?.execute_enabled} onClick={() => void mutate(plan.opportunity_id, { operation: "execute", request_id: approval.request_id, approval_token: token })} className="inline-flex items-center gap-1.5 rounded-lg border border-gold/50 bg-gold/12 px-3 py-2 text-xs font-medium text-gold hover:bg-gold/20 disabled:opacity-50"><Play className="h-3.5 w-3.5" />Execute approved reply</button> : null}
            </div>
            {!data?.outbound_enabled ? <p className="mt-2 text-[0.7rem] text-caution">Approval is locked until the outbound gate is enabled.</p> : approved && !data?.execute_enabled ? <p className="mt-2 text-[0.7rem] text-caution">Execution is separately locked until the execute gate is enabled.</p> : null}
          </article>
        })}
      </div> : <p className="rounded-xl border border-border/70 bg-background/35 p-4 text-sm text-muted-foreground">No pursuit-ranked opportunity currently qualifies for controlled execution.</p>}

      {preparationOnly.length ? <details className="rounded-xl border border-border/70 bg-background/30 p-4"><summary className="cursor-pointer text-xs font-medium text-muted-foreground">Preparation-only opportunities ({preparationOnly.length})</summary><div className="mt-3 space-y-2">{preparationOnly.slice(0, 8).map((plan) => <div key={plan.opportunity_id} className="rounded-lg border border-border/60 p-3"><p className="text-xs font-medium text-foreground">{plan.channel}</p><p className="mt-1 text-xs leading-relaxed text-muted-foreground">{plan.reason}</p></div>)}</div></details> : null}
    </div>
  )
}
