"use client"

import { useCallback, useEffect, useState } from "react"
import { Loader2, RefreshCw } from "lucide-react"

type Capability = { id: string; label: string; read: boolean; propose: boolean; approve: boolean; execute: boolean; scope: string }
type Briefing = { ok: boolean; counts: { qualified_leads: number; pending_approvals: number; recent_audit_events: number }; capabilities: Capability[]; actions_needed: string[]; principle: string; error?: string }
function State({ value }: { value: boolean }) { return <span className={value ? "text-positive" : "text-muted-foreground"}>{value ? "Yes" : "No"}</span> }

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
      setData(body); setError(null)
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Operator briefing unavailable") }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])
  if (loading && !data) return <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Building owner briefing…</div>
  return <div className="space-y-4">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-sm font-medium text-foreground">Capability-specific operator model</p><p className="mt-1 max-w-3xl text-xs leading-relaxed text-muted-foreground">{data?.principle}</p></div><button type="button" onClick={() => void load()} className="inline-flex items-center gap-2 rounded-lg border border-border px-3 py-2 text-xs text-foreground hover:bg-muted"><RefreshCw className="h-3.5 w-3.5" />Refresh</button></div>
    {error ? <p className="rounded-lg border border-critical/30 bg-critical/5 p-3 text-xs text-critical">{error}</p> : null}
    {data ? <><div className="grid gap-2 sm:grid-cols-3"><div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Qualified leads</p><p className="mt-1 text-sm font-medium text-foreground">{data.counts.qualified_leads}</p></div><div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Pending approvals</p><p className="mt-1 text-sm font-medium text-foreground">{data.counts.pending_approvals}</p></div><div className="rounded-lg border border-border/70 bg-background/40 p-3"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Recent audit events</p><p className="mt-1 text-sm font-medium text-foreground">{data.counts.recent_audit_events}</p></div></div>
    <div className="overflow-x-auto rounded-xl border border-border/70"><table className="w-full min-w-[720px] text-left text-xs"><thead className="bg-muted/30 text-muted-foreground"><tr><th className="p-3">Capability</th><th className="p-3">Read</th><th className="p-3">Propose</th><th className="p-3">Approve</th><th className="p-3">Execute</th><th className="p-3">Scope</th></tr></thead><tbody>{data.capabilities.map((cap) => <tr key={cap.id} className="border-t border-border/60"><td className="p-3 font-medium text-foreground">{cap.label}</td><td className="p-3"><State value={cap.read} /></td><td className="p-3"><State value={cap.propose} /></td><td className="p-3"><State value={cap.approve} /></td><td className="p-3"><State value={cap.execute} /></td><td className="p-3 leading-relaxed text-muted-foreground">{cap.scope}</td></tr>)}</tbody></table></div>
    <div className="rounded-xl border border-border/70 bg-background/35 p-4"><p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Actions needed</p>{data.actions_needed.length ? <ul className="mt-2 space-y-1.5 text-xs leading-relaxed text-foreground/85">{data.actions_needed.map((item) => <li key={item}>• {item}</li>)}</ul> : <p className="mt-2 text-xs text-positive">No current operator blockers reported.</p>}</div></> : null}
  </div>
}
