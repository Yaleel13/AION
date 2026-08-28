"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { ExternalLink, FileCheck2, Loader2, RefreshCw, ShieldCheck, XCircle } from "lucide-react"
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
  status: string
}

type PreparationResponse = {
  stage: number
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
  created_at: string
  expires_at: string
}

type ApprovalResponse = {
  ok: boolean
  pending_count: number
  prepared_count: number
  approvals: Approval[]
  outbound_enabled: boolean
  execute_enabled: boolean
  quota_reached?: boolean
  quota_message?: string | null
  error?: string
}

type QueueStatus = "qualified" | "prepared" | "pending" | "rejected" | "expired"

function leadIdFromApproval(item: Approval) {
  return item.summary.match(/lead ([0-9a-f-]{8,})/i)?.[1] ?? null
}

function statusLabel(status: QueueStatus) {
  if (status === "qualified") return "Qualified opportunity"
  if (status === "prepared") return "Prepared"
  if (status === "pending") return "Pending approval"
  if (status === "rejected") return "Rejected"
  return "Expired"
}

function statusClass(status: QueueStatus) {
  if (status === "pending") return "border-gold/40 bg-gold/10 text-gold"
  if (status === "rejected" || status === "expired") return "border-border bg-muted/40 text-muted-foreground"
  return "border-positive/30 bg-positive/10 text-positive"
}

export function OwnerOpportunityReview() {
  const [preparation, setPreparation] = useState<PreparationResponse | null>(null)
  const [approvals, setApprovals] = useState<ApprovalResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [working, setWorking] = useState<"prepare" | "propose" | "reject" | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const [prepResponse, approvalResponse] = await Promise.all([
        fetch("/api/owner/moltbook-preparation", { cache: "no-store" }),
        fetch("/api/owner/moltbook-approvals", { cache: "no-store" }),
      ])
      const [prepBody, approvalBody] = await Promise.all([
        prepResponse.json() as Promise<PreparationResponse>,
        approvalResponse.json() as Promise<ApprovalResponse>,
      ])
      if (!prepResponse.ok) throw new Error(prepBody.error || `Preparation load failed (${prepResponse.status})`)
      if (!approvalResponse.ok || !approvalBody.ok) throw new Error(approvalBody.error || `Approval load failed (${approvalResponse.status})`)
      setPreparation(prepBody)
      setApprovals(approvalBody)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Opportunity review queue unavailable")
    } finally {
      setLoading(false)
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

  const mutateApprovals = useCallback(async (payload: Record<string, unknown>, mode: "propose" | "reject") => {
    setWorking(mode)
    try {
      const response = await fetch("/api/owner/moltbook-approvals", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
        cache: "no-store",
      })
      const body = (await response.json()) as ApprovalResponse
      if (!response.ok || !body.ok) throw new Error(body.error || `Approval mutation failed (${response.status})`)
      setApprovals(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Approval preflight unavailable")
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

  const queue = useMemo(() => (preparation?.items ?? []).map((item) => {
    const approval = approvalsByLead.get(item.lead_id)
    let status: QueueStatus = "prepared"
    if (approval?.decision === "pending") status = "pending"
    else if (approval?.decision === "rejected") status = "rejected"
    else if (approval?.decision === "expired") status = "expired"
    return { item, approval, status }
  }), [approvalsByLead, preparation])

  if (loading && !preparation && !approvals) {
    return <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Loading opportunity review queue…</div>
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="max-w-2xl">
          <p className="text-sm font-medium text-foreground">Owner Opportunity Review</p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">One decision surface for qualified Moltbook opportunities. Review the source, service fit, confidence, risk, and exact draft before rejecting or advancing to a durable proposal. Publishing remains unavailable.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => void load()} disabled={Boolean(working)} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs text-foreground hover:bg-muted disabled:opacity-60"><RefreshCw className="h-3.5 w-3.5" />Refresh</button>
          <button type="button" onClick={() => void prepare()} disabled={Boolean(working)} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs text-foreground hover:bg-muted disabled:opacity-60">{working === "prepare" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileCheck2 className="h-3.5 w-3.5" />}Prepare Review</button>
          <button type="button" onClick={() => void mutateApprovals({ operation: "propose_prepared" }, "propose")} disabled={Boolean(working)} className="inline-flex items-center gap-2 rounded-lg border border-gold/40 bg-gold/10 px-3 py-2 text-xs font-medium text-gold hover:bg-gold/15 disabled:opacity-60">{working === "propose" ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <ShieldCheck className="h-3.5 w-3.5" />}Create Proposals</button>
        </div>
      </div>

      {error ? <p className="rounded-lg border border-critical/30 bg-critical/5 p-3 text-xs text-critical">{error}</p> : null}
      {approvals?.quota_reached ? <p className="rounded-lg border border-caution/30 bg-caution/5 p-3 text-xs text-caution">{approvals.quota_message || "The 8-item review proposal quota has been reached for this 24-hour window."}</p> : null}

      <div className="grid gap-2 sm:grid-cols-4">
        <div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Qualified source pool</p><p className="mt-1 text-sm font-medium text-foreground">{preparation?.source_lead_count ?? 0}</p></div>
        <div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Prepared</p><p className="mt-1 text-sm font-medium text-foreground">{preparation?.prepared_count ?? 0} / 8</p></div>
        <div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Pending review</p><p className="mt-1 text-sm font-medium text-foreground">{approvals?.pending_count ?? 0}</p></div>
        <div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">External execution</p><p className="mt-1 text-sm font-medium text-foreground">{approvals?.execute_enabled ? "Enabled" : "Locked"}</p></div>
      </div>

      {queue.length ? <div className="space-y-3">
        {queue.map(({ item, approval, status }, index) => (
          <article key={item.lead_id} className="rounded-xl border border-border/70 bg-background/35 p-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 max-w-3xl">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[0.65rem] font-medium uppercase tracking-wider text-muted-foreground">Opportunity {index + 1}</span>
                  <span className={cn("rounded-full border px-2 py-0.5 text-[0.65rem] font-medium", statusClass(status))}>{statusLabel(status)}</span>
                </div>
                <p className="mt-2 text-xs text-muted-foreground">Requester · {item.requester_identity}</p>
                <p className="mt-1 text-sm font-medium text-foreground">{item.problem}</p>
                <p className="mt-1 text-xs text-muted-foreground">Service fit · {item.service}</p>
              </div>
              <div className="rounded-lg border border-border/70 bg-background/40 px-3 py-2 text-right text-xs text-muted-foreground">
                <p>Fit <span className="font-medium text-foreground">{Math.round(Number(item.fit_score || 0) * 100)}%</span></p>
                <p>Confidence <span className="font-medium text-foreground">{Math.round(Number(item.confidence_score || 0) * 100)}%</span></p>
              </div>
            </div>

            <div className="mt-4 grid gap-3 lg:grid-cols-2">
              <div className="rounded-lg border border-border/60 bg-background/30 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">AION assessment</p><p className="mt-2 text-xs leading-relaxed text-foreground/85">Strong enough for owner review because it passed the current Stage 3 explicit-need and confidence gates. Verify buyer intent from the source before treating it as a sales opportunity.</p><p className="mt-2 text-[0.7rem] leading-relaxed text-muted-foreground">Risks · {item.risks}</p></div>
              <div className="rounded-lg border border-gold/20 bg-gold/5 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-gold">Proposed response</p><p className="mt-2 text-xs leading-relaxed text-foreground/90">{item.response_draft}</p></div>
            </div>

            <div className="mt-3 flex flex-wrap items-center justify-between gap-3 border-t border-border/60 pt-3">
              <div className="flex flex-wrap items-center gap-3 text-[0.7rem] text-muted-foreground">
                <a href={item.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-gold hover:underline">Open source <ExternalLink className="h-3 w-3" /></a>
                {approval ? <span>Proposal · {approval.decision}</span> : <span>No durable proposal yet</span>}
                {approval?.expires_at ? <span>Expires · {new Date(approval.expires_at).toLocaleString()}</span> : null}
              </div>
              {approval?.decision === "pending" ? <button type="button" disabled={Boolean(working)} onClick={() => void mutateApprovals({ operation: "reject", request_id: approval.request_id, expected_content_hash: approval.content_hash }, "reject")} className="inline-flex items-center gap-1 rounded-lg border border-border px-2.5 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-60"><XCircle className="h-3.5 w-3.5" />Reject proposal</button> : null}
            </div>
          </article>
        ))}
      </div> : <p className="rounded-xl border border-border/70 bg-background/35 p-4 text-sm text-muted-foreground">No Stage 3 opportunities are prepared. Run a read-only Moltbook scan, then prepare review. AION will not fabricate opportunities.</p>}

      <p className="text-[0.7rem] leading-relaxed text-muted-foreground">Pipeline: Research candidate → qualified opportunity → prepared → pending owner approval → rejected/expired. There is intentionally no approve-or-publish control in this phase.</p>
    </div>
  )
}
