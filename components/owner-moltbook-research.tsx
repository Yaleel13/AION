"use client"

import { useCallback, useEffect, useState } from "react"
import { ExternalLink, Loader2, Radar, RefreshCw } from "lucide-react"
import { defer } from "@/lib/defer"
import { AION_REQUEST_HEADER } from "@/lib/aion/owner-session"

type Lead = {
  lead_id: string
  source_url: string
  requester_identity: string
  stated_problem: string
  relevant_service: string
  fit_score: number
  confidence_score: number
  suggested_response: string
  risks: string
  approval_status: string
  conversion_outcome: string
  created_at: string
  untrusted_external_content: boolean
}

type ResearchResponse = {
  ok: boolean
  stage: number
  mode: string
  count?: number
  stored_count?: number
  qualified_this_scan?: number
  leads: Lead[]
  contacted: boolean
  outbound_enabled: boolean
  error?: string
}

export function OwnerMoltbookResearch() {
  const [data, setData] = useState<ResearchResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/owner/moltbook-research", { cache: "no-store" })
      const body = (await response.json()) as ResearchResponse
      if (!response.ok || !body.ok) throw new Error(body.error || `Research load failed (${response.status})`)
      setData(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Moltbook research unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  const scan = useCallback(async () => {
    setScanning(true)
    setNotice(null)
    try {
      const response = await fetch("/api/owner/moltbook-research", { method: "POST", headers: AION_REQUEST_HEADER, cache: "no-store" })
      const body = (await response.json()) as ResearchResponse
      if (!response.ok || !body.ok) throw new Error(body.error || `Research scan failed (${response.status})`)
      setData(body)
      setError(null)
      setNotice(`Scan complete. ${body.qualified_this_scan ?? 0} qualified this scan; ${body.stored_count ?? body.count ?? body.leads.length} stored.`)
      window.dispatchEvent(new CustomEvent("aion:boardroom-refresh", { detail: { source: "moltbook-scan" } }))
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Moltbook research scan unavailable")
    } finally {
      setScanning(false)
    }
  }, [])

  useEffect(() => {
    defer(() => { void load() })
    const refresh = (event: Event) => {
      const source = (event as CustomEvent<{ source?: string }>).detail?.source
      if (source !== "moltbook-scan") void load()
    }
    window.addEventListener("aion:boardroom-refresh", refresh)
    return () => window.removeEventListener("aion:boardroom-refresh", refresh)
  }, [load])

  if (loading && !data) {
    return <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Loading research queue…</div>
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">Live read-only opportunity research</p>
          <p className="mt-1 text-xs text-muted-foreground">Moltbook content is untrusted external data. AION may classify and store qualified opportunities, but it does not contact anyone.</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => void load()} disabled={loading || scanning} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs text-foreground hover:bg-muted disabled:opacity-60">{loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}Refresh</button>
          <button type="button" onClick={() => void scan()} disabled={scanning || loading} className="inline-flex items-center gap-2 rounded-lg border border-gold/40 bg-gold/10 px-3 py-2 text-xs font-medium text-gold hover:bg-gold/15 disabled:opacity-60">{scanning ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Radar className="h-3.5 w-3.5" />}{scanning ? "Scanning…" : "Scan Moltbook"}</button>
        </div>
      </div>

      {error ? <p className="rounded-lg border border-critical/30 bg-critical/5 p-3 text-xs text-critical">{error}</p> : null}
      {notice ? <p role="status" aria-live="polite" className="rounded-lg border border-positive/30 bg-positive/5 p-3 text-xs text-positive">{notice}</p> : null}

      {data ? <div className="grid gap-2 sm:grid-cols-4">
        <div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Mode</p><p className="mt-1 text-sm font-medium text-foreground">{data.mode}</p></div>
        <div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Stored</p><p className="mt-1 text-sm font-medium text-foreground">{data.stored_count ?? data.count ?? data.leads.length}</p></div>
        <div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">This scan</p><p className="mt-1 text-sm font-medium text-foreground">{data.qualified_this_scan ?? "—"}</p></div>
        <div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Outbound</p><p className="mt-1 text-sm font-medium text-foreground">{data.outbound_enabled ? "Enabled" : "Locked"}</p></div>
      </div> : null}

      {data?.leads?.length ? <div className="space-y-2">{data.leads.slice(0, 12).map((lead) => <article key={lead.lead_id} className="rounded-xl border border-border/70 bg-background/35 p-4">
        <div className="flex flex-wrap items-start justify-between gap-3"><div className="min-w-0"><p className="text-xs text-muted-foreground">{lead.requester_identity}</p><p className="mt-1 text-sm font-medium text-foreground">{lead.stated_problem}</p><p className="mt-1 text-xs text-muted-foreground">Service match · {lead.relevant_service}</p></div><div className="text-right text-xs text-muted-foreground"><p>Fit {Math.round(Number(lead.fit_score || 0) * 100)}%</p><p>Confidence {Math.round(Number(lead.confidence_score || 0) * 100)}%</p></div></div>
        <p className="mt-3 text-xs leading-relaxed text-foreground/85">{lead.suggested_response}</p>
        <p className="mt-2 text-[0.7rem] leading-relaxed text-muted-foreground">Risks · {lead.risks}</p>
        <div className="mt-3 flex items-center justify-between gap-3"><span className="text-[0.7rem] text-muted-foreground">{lead.approval_status} · {lead.conversion_outcome}</span><a href={lead.source_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-gold hover:underline">Source <ExternalLink className="h-3 w-3" /></a></div>
      </article>)}</div> : <p className="rounded-xl border border-border/70 bg-background/35 p-4 text-sm text-muted-foreground">No qualified opportunities are stored yet. A scan may legitimately return zero results; AION will not fabricate demand.</p>}
    </div>
  )
}
