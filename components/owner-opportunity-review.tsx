"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { ExternalLink, FileCheck2, Loader2, RefreshCw, Send, ShieldCheck, XCircle } from "lucide-react"
import { cn } from "@/lib/utils"

type PreparedItem = {
  lead_id: string
  source_url: string
  requester_identity: string
  problem: string
  service: string
  fit_score: number
  confidence_score: number
  response_draft: string
  risks: string
}

type PreparationResponse = {
  prepared_count: number
  source_lead_count: number
  summary: string
  items: PreparedItem[]
  error?: string
}

type Approval = {
  request_id: string
  action: string
  summary: string
  destination: string
  decision: string
  content_hash: string
  expires_at: string
}

type QualityGate = {
  reviewed_count: number
  positive_count: number
  precision: number | null
  minimum_reviews: number
  minimum_precision: number
  ready: boolean
}

type ApprovalResponse = {
  ok: boolean
  pending_count: number
  prepared_count: number
  approvals: Approval[]
  outbound_enabled: boolean
  execute_enabled: boolean
  controlled_outbound_ready?: boolean
  quality_gate?: QualityGate
  quota_reached?: boolean
  quota_message?: string | null
  approval_token?: string
  approved?: Approval
  execution?: { ok: boolean; request_id: string; status_code: number }
  error?: string
}

type Disposition = "strong_lead" | "possible_lead" | "informational" | "wrong_service" | "noise"
type ReviewRecord = { lead_id: string; disposition: Disposition; reviewed_at: string }
type ReviewResponse = {
  ok: boolean
  reviewed_count: number
  positive_count: number
  precision: number | null
  target_precision: number
  reviews: ReviewRecord[]
  error?: string
}

type QueueStatus = "prepared" | "pending" | "approved" | "executed" | "rejected" | "expired" | "invalidated"

const DISPOSITIONS: Array<{ value: Disposition; label: string }> = [
  { value: "strong_lead", label: "Strong lead" },
  { value: "possible_lead", label: "Possible lead" },
  { value: "informational", label: "Informational" },
  { value: "wrong_service", label: "Wrong service" },
  { value: "noise", label: "Noise" },
]
const POSITIVE = new Set<Disposition>(["strong_lead", "possible_lead"])

function leadIdFromApproval(item: Approval) {
  return item.summary.match(/lead ([0-9a-f-]{8,})/i)?.[1] ?? null
}

function statusClass(status: QueueStatus) {
  if (status === "pending" || status === "approved") return "border-gold/40 bg-gold/10 text-gold"
  if (status === "executed") return "border-positive/30 bg-positive/10 text-positive"
  if (status === "rejected" || status === "expired" || status === "invalidated") return "border-border bg-muted/40 text-muted-foreground"
  return "border-positive/30 bg-positive/10 text-positive"
}

export function OwnerOpportunityReview() {
  const [preparation, setPreparation] = useState<PreparationResponse | null>(null)
  const [approvals, setApprovals] = useState<ApprovalResponse | null>(null)
  const [reviews, setReviews] = useState<ReviewResponse | null>(null)
  const [approvalTokens, setApprovalTokens] = useState<Record<string, string>>({})
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [prepResponse, approvalResponse, reviewResponse] = await Promise.all([
        fetch("/api/owner/moltbook-preparation", { cache: "no-store" }),
        fetch("/api/owner/moltbook-approvals", { cache: "no-store" }),
        fetch("/api/owner/moltbook-reviews", { cache: "no-store" }),
      ])
      const [prepBody, approvalBody, reviewBody] = await Promise.all([
        prepResponse.json() as Promise<PreparationResponse>,
        approvalResponse.json() as Promise<ApprovalResponse>,
        reviewResponse.json() as Promise<ReviewResponse>,
      ])
      if (!prepResponse.ok) throw new Error(prepBody.error || `Preparation load failed (${prepResponse.status})`)
      if (!approvalResponse.ok || !approvalBody.ok) throw new Error(approvalBody.error || `Approval load failed (${approvalResponse.status})`)
      if (!reviewResponse.ok || !reviewBody.ok) throw new Error(reviewBody.error || `Review metrics failed (${reviewResponse.status})`)
      setPreparation(prepBody)
      setApprovals(approvalBody)
      setReviews(reviewBody)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Opportunity review queue unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  const post = useCallback(async (payload: Record<string, unknown>, key: string) => {
    setWorking(key)
    setNotice(null)
    try {
      const response = await fetch("/api/owner/moltbook-approvals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
      })
      const body = (await response.json()) as ApprovalResponse
      if (!response.ok || !body.ok) throw new Error(body.error || `Approval operation failed (${response.status})`)
      setApprovals(body)
      if (body.approved?.request_id && body.approval_token) {
        setApprovalTokens((current) => ({ ...current, [body.approved!.request_id]: body.approval_token! }))
        setNotice("Exact draft approved. The single-use token is held only in this browser session; execution is a separate action.")
      }
      if (body.execution?.ok) {
        setApprovalTokens((current) => {
          const next = { ...current }
          delete next[body.execution!.request_id]
          return next
        })
        setNotice(`Controlled comment executed successfully (HTTP ${body.execution.status_code}).`)
      }
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Approval operation unavailable")
    } finally {
      setWorking(null)
    }
  }, [])

  const prepare = useCallback(async () => {
    setWorking("prepare")
    try {
      const response = await fetch("/api/owner/moltbook-preparation", { method: "POST", cache: "no-store" })
      const body = (await response.json()) as PreparationResponse
      if (!response.ok) throw new Error(body.error || `Preparation failed (${response.status})`)
      setPreparation(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Preparation unavailable")
    } finally {
      setWorking(null)
    }
  }, [])

  const setDisposition = useCallback(async (leadId: string, disposition: Disposition) => {
    setWorking(`review:${leadId}`)
    try {
      const response = await fetch("/api/owner/moltbook-reviews", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lead_id: leadId, disposition }),
        cache: "no-store",
      })
      const body = (await response.json()) as ReviewResponse
      if (!response.ok || !body.ok) throw new Error(body.error || `Review update failed (${response.status})`)
      setReviews(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Review feedback unavailable")
    } finally {
      setWorking(null)
    }
  }, [])

  useEffect(() => { void load() }, [load])

  const approvalsByLead = useMemo(() => {
    const map = new Map<string, Approval>()
    for (const approval of approvals?.approvals ?? []) {
      const leadId = leadIdFromApproval(approval)
      if (leadId && !map.has(leadId)) map.set(leadId, approval)
    }
    return map
  }, [approvals])
  const reviewsByLead = useMemo(() => new Map((reviews?.reviews ?? []).map((item) => [item.lead_id, item])), [reviews])
  const queue = useMemo(() => (preparation?.items ?? []).map((item) => {
    const approval = approvalsByLead.get(item.lead_id)
    const status = (approval?.decision || "prepared") as QueueStatus
    return { item, approval, status, review: reviewsByLead.get(item.lead_id) }
  }), [approvalsByLead, preparation, reviewsByLead])

  if (loading && !preparation && !approvals) {
    return <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Loading opportunity review queue…</div>
  }

  const precisionPct = reviews?.precision == null ? "—" : `${Math.round(reviews.precision * 100)}%`
  const quality = approvals?.quality_gate

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-2xl">
          <p className="text-sm font-medium text-foreground">Owner Opportunity Review</p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">Research, quality feedback, proposal review, and—only when separately activated—two-step owner-approved comment execution. No direct messages or autonomous outreach.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => void load()} disabled={Boolean(working)} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs hover:bg-muted disabled:opacity-60"><RefreshCw className="h-3.5 w-3.5" />Refresh</button>
          <button type="button" onClick={() => void prepare()} disabled={Boolean(working)} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs hover:bg-muted disabled:opacity-60">{working === "prepare" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileCheck2 className="h-3.5 w-3.5" />}Prepare Review</button>
          <button type="button" onClick={() => void post({ operation: "propose_prepared" }, "propose")} disabled={Boolean(working)} className="inline-flex items-center gap-2 rounded-lg border border-gold/40 bg-gold/10 px-3 py-2 text-xs font-medium text-gold disabled:opacity-60">{working === "propose" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}Create Proposals</button>
        </div>
      </div>

      {error ? <p className="rounded-lg border border-critical/30 bg-critical/5 p-3 text-xs text-critical">{error}</p> : null}
      {notice ? <p className="rounded-lg border border-positive/30 bg-positive/5 p-3 text-xs text-positive">{notice}</p> : null}
      {approvals?.quota_reached ? <p className="rounded-lg border border-caution/30 bg-caution/5 p-3 text-xs text-caution">{approvals.quota_message || "The 8-item proposal quota has been reached."}</p> : null}

      <div className="grid gap-2 sm:grid-cols-6">
        <Metric label="Qualified pool" value={String(preparation?.source_lead_count ?? 0)} />
        <Metric label="Prepared" value={`${preparation?.prepared_count ?? 0} / 8`} />
        <Metric label="Reviewed" value={String(reviews?.reviewed_count ?? 0)} />
        <Metric label="Precision" value={precisionPct} detail="Target ≥ 70%" />
        <Metric label="Approval gate" value={approvals?.outbound_enabled ? "Active" : "Locked"} />
        <Metric label="Execute gate" value={approvals?.execute_enabled ? "Active" : "Locked"} />
      </div>

      {quality ? <p className={cn("rounded-lg border p-3 text-xs", quality.ready ? "border-positive/30 bg-positive/5 text-positive" : "border-border bg-background/35 text-muted-foreground")}>Quality gate · {quality.ready ? "ready" : "not ready"} · {quality.reviewed_count}/{quality.minimum_reviews} minimum reviews · {quality.precision == null ? "—" : Math.round(quality.precision * 100) + "%"}/{Math.round(quality.minimum_precision * 100)}% minimum precision.</p> : null}

      {queue.length ? <div className="space-y-3">{queue.map(({ item, approval, status, review }, index) => {
        const positiveReview = review ? POSITIVE.has(review.disposition) : false
        const token = approval ? approvalTokens[approval.request_id] : undefined
        const canApprove = Boolean(approval?.decision === "pending" && approvals?.outbound_enabled && quality?.ready && positiveReview)
        const canExecute = Boolean(approval?.decision === "approved" && approvals?.execute_enabled && token)
        return <article key={item.lead_id} className="rounded-xl border border-border/70 bg-background/35 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 max-w-3xl">
              <div className="flex flex-wrap items-center gap-2"><span className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Opportunity {index + 1}</span><span className={cn("rounded-full border px-2 py-0.5 text-[0.65rem] font-medium capitalize", statusClass(status))}>{status}</span>{review ? <span className="rounded-full border border-border bg-muted/40 px-2 py-0.5 text-[0.65rem] text-muted-foreground">{DISPOSITIONS.find((d) => d.value === review.disposition)?.label}</span> : null}</div>
              <p className="mt-2 text-xs text-muted-foreground">Requester · {item.requester_identity}</p>
              <p className="mt-1 text-sm font-medium text-foreground">{item.problem}</p>
              <p className="mt-1 text-xs text-muted-foreground">Service fit · {item.service}</p>
            </div>
            <div className="rounded-lg border border-border/70 bg-background/40 px-3 py-2 text-right text-xs text-muted-foreground"><p>Fit <span className="font-medium text-foreground">{Math.round(item.fit_score * 100)}%</span></p><p>Confidence <span className="font-medium text-foreground">{Math.round(item.confidence_score * 100)}%</span></p></div>
          </div>
          <div className="mt-4 grid gap-3 lg:grid-cols-2"><div className="rounded-lg border border-border/60 bg-background/30 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">AION assessment</p><p className="mt-2 text-xs leading-relaxed text-foreground/85">Passed Stage 3. Owner disposition is required before approval. Risks · {item.risks}</p></div><div className="rounded-lg border border-gold/20 bg-gold/5 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-gold">Exact proposed response</p><p className="mt-2 text-xs leading-relaxed text-foreground/90">{item.response_draft}</p></div></div>
          <div className="mt-3 flex flex-wrap gap-1.5">{DISPOSITIONS.map((option) => <button key={option.value} type="button" disabled={Boolean(working)} onClick={() => void setDisposition(item.lead_id, option.value)} className={cn("rounded-lg border px-2.5 py-1.5 text-xs disabled:opacity-60", review?.disposition === option.value ? "border-gold/40 bg-gold/10 text-gold" : "border-border text-muted-foreground hover:bg-muted")}>{option.label}</button>)}</div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-border/60 pt-3">
            <div className="flex flex-wrap items-center gap-3 text-[0.7rem] text-muted-foreground"><a href={item.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-gold hover:underline">Open source <ExternalLink className="h-3 w-3" /></a>{approval ? <span>Proposal · {approval.decision}</span> : <span>No durable proposal yet</span>}</div>
            <div className="flex flex-wrap gap-2">
              {approval?.decision === "pending" ? <button type="button" disabled={Boolean(working)} onClick={() => void post({ operation: "reject", request_id: approval.request_id, expected_content_hash: approval.content_hash }, `reject:${approval.request_id}`)} className="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted disabled:opacity-60"><XCircle className="h-3.5 w-3.5" />Reject</button> : null}
              {canApprove ? <button type="button" disabled={Boolean(working)} onClick={() => void post({ operation: "approve", request_id: approval!.request_id, expected_content_hash: approval!.content_hash }, `approve:${approval!.request_id}`)} className="inline-flex items-center gap-1 rounded-lg border border-gold/40 bg-gold/10 px-2.5 py-1.5 text-xs font-medium text-gold disabled:opacity-60"><ShieldCheck className="h-3.5 w-3.5" />Approve exact draft</button> : null}
              {canExecute ? <button type="button" disabled={Boolean(working)} onClick={() => void post({ operation: "execute", request_id: approval!.request_id, approval_token: token }, `execute:${approval!.request_id}`)} className="inline-flex items-center gap-1 rounded-lg border border-positive/40 bg-positive/10 px-2.5 py-1.5 text-xs font-medium text-positive disabled:opacity-60"><Send className="h-3.5 w-3.5" />Execute once</button> : null}
            </div>
          </div>
        </article>
      })}</div> : <p className="rounded-xl border border-border/70 bg-background/35 p-4 text-sm text-muted-foreground">No Stage 3 opportunities are prepared.</p>}

      <p className="text-[0.7rem] leading-relaxed text-muted-foreground">Execution policy: comments only; separate approve and execute actions; exact content hash binding; single-use token; max 3 successful comments per 24h; no DMs; no automatic retries; kill switch remains authoritative.</p>
    </div>
  )
}

function Metric({ label, value, detail }: { label: string; value: string; detail?: string }) {
  return <div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">{label}</p><p className="mt-1 text-sm font-medium text-foreground">{value}</p>{detail ? <p className="mt-1 text-[0.65rem] text-muted-foreground">{detail}</p> : null}</div>
}
