"use client"

import { useCallback, useEffect, useState } from "react"
import { FileCheck2, Loader2, RefreshCw } from "lucide-react"
import { defer } from "@/lib/defer"

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

type Preparation = {
  stage: number
  mode: string
  prepared_at: string
  source_lead_count: number
  prepared_count: number
  items: PreparedItem[]
  summary: string
  contacted: boolean
  published: boolean
  outbound_enabled: boolean
  error?: string
}

export function OwnerMoltbookPreparation() {
  const [data, setData] = useState<Preparation | null>(null)
  const [loading, setLoading] = useState(true)
  const [preparing, setPreparing] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/owner/moltbook-preparation", { cache: "no-store" })
      const body = (await response.json()) as Preparation
      if (!response.ok) throw new Error(body.error || `Preparation load failed (${response.status})`)
      setData(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Preparation unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  const prepare = useCallback(async () => {
    setPreparing(true)
    try {
      const response = await fetch("/api/owner/moltbook-preparation", { method: "POST", cache: "no-store" })
      const body = (await response.json()) as Preparation
      if (!response.ok) throw new Error(body.error || `Preparation failed (${response.status})`)
      setData(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Preparation unavailable")
    } finally {
      setPreparing(false)
    }
  }, [])

  useEffect(() => { defer(() => { void load() }) }, [load])

  if (loading && !data) {
    return <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Loading preparation queue…</div>
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-foreground">Owner-review preparation</p>
          <p className="mt-1 text-xs text-muted-foreground">Builds ranked briefs and response drafts from already-qualified Stage 2 leads. Nothing is contacted or published.</p>
        </div>
        <div className="flex gap-2">
          <button type="button" onClick={() => void load()} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs text-foreground hover:bg-muted"><RefreshCw className="h-3.5 w-3.5" />Refresh</button>
          <button type="button" onClick={() => void prepare()} disabled={preparing} className="inline-flex items-center gap-2 rounded-lg border border-gold/40 bg-gold/10 px-3 py-2 text-xs font-medium text-gold hover:bg-gold/15 disabled:opacity-60">{preparing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <FileCheck2 className="h-3.5 w-3.5" />}Prepare Review</button>
        </div>
      </div>

      {error ? <p className="rounded-lg border border-critical/30 bg-critical/5 p-3 text-xs text-critical">{error}</p> : null}
      {data ? <p className="rounded-xl border border-border/70 bg-background/35 p-4 text-sm text-foreground/90">{data.summary}</p> : null}

      {data?.items?.length ? data.items.map((item) => (
        <article key={item.lead_id} className="rounded-xl border border-border/70 bg-background/35 p-4">
          <div className="flex flex-wrap justify-between gap-3"><div><p className="text-xs text-muted-foreground">{item.requester_identity}</p><p className="mt-1 text-sm font-medium text-foreground">{item.problem}</p><p className="mt-1 text-xs text-muted-foreground">{item.service}</p></div><div className="text-right text-xs text-muted-foreground"><p>Fit {Math.round(Number(item.fit_score || 0) * 100)}%</p><p>Confidence {Math.round(Number(item.confidence_score || 0) * 100)}%</p></div></div>
          <p className="mt-3 text-xs leading-relaxed text-foreground/85">{item.response_draft}</p>
          <p className="mt-2 text-[0.7rem] text-muted-foreground">Risks · {item.risks}</p>
          <p className="mt-2 text-[0.7rem] font-medium text-gold">Owner review only · no outbound action</p>
        </article>
      )) : null}
    </div>
  )
}
