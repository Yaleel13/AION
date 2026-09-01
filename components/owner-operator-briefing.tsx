"use client"

import { useCallback, useEffect, useState } from "react"
import { Loader2, RefreshCw } from "lucide-react"
import { defer } from "@/lib/defer"

type Briefing = {
  ok: boolean
  quality: { reviewed: number; positive: number; precision: number | null; target_precision: number; minimum_reviews: number; ready: boolean }
  counts: { qualified_leads: number; pending_approvals: number; recent_audit_events: number }
  actions_needed: string[]
  principle: string
  error?: string
}

export function OwnerOperatorBriefing() {
  const [data, setData] = useState<Briefing | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/owner/operator-briefing", { cache: "no-store" })
      const body = (await response.json()) as Briefing
      if (!response.ok || !body.ok) throw new Error(body.error || `Operator briefing failed (${response.status})`)
      setData(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Operator briefing unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    defer(() => { void load() })
    const refresh = () => void load()
    window.addEventListener("aion:boardroom-refresh", refresh)
    return () => window.removeEventListener("aion:boardroom-refresh", refresh)
  }, [load])

  if (loading && !data) return <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Building owner briefing…</div>

  const precision = data?.quality.precision == null ? "—" : `${Math.round(data.quality.precision * 100)}%`
  return <div className="space-y-3">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-medium text-foreground">Owner priorities</p><p className="mt-1 max-w-3xl text-xs leading-relaxed text-muted-foreground">{data?.principle}</p></div><button type="button" onClick={() => void load()} disabled={loading} className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs hover:bg-muted disabled:opacity-60">{loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}Refresh</button></div>
    {error ? <p className="rounded-lg border border-critical/30 bg-critical/5 p-3 text-xs text-critical">{error}</p> : null}
    {data ? <>
      <div className="grid gap-2 sm:grid-cols-4"><div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Qualified leads</p><p className="mt-1 text-sm font-medium text-foreground">{data.counts.qualified_leads}</p></div><div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Pending approvals</p><p className="mt-1 text-sm font-medium text-foreground">{data.counts.pending_approvals}</p></div><div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Quality precision</p><p className="mt-1 text-sm font-medium text-foreground">{precision}</p><p className="mt-1 text-[0.65rem] text-muted-foreground">{data.quality.reviewed} reviewed · target 70%</p></div><div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Recent audit</p><p className="mt-1 text-sm font-medium text-foreground">{data.counts.recent_audit_events}</p></div></div>
      <div className="rounded-xl border border-border/70 bg-background/35 p-4"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Actions needed</p>{data.actions_needed.length ? <ul className="mt-2 space-y-1.5 text-xs leading-relaxed text-foreground/85">{data.actions_needed.map((item) => <li key={item}>• {item}</li>)}</ul> : <p className="mt-2 text-xs text-positive">No current operator blockers reported.</p>}</div>
    </> : null}
  </div>
}
