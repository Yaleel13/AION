"use client"

import { useCallback, useEffect, useState } from "react"
import { Check, Loader2, Minus, RefreshCw } from "lucide-react"

type Capability = {
  configured: boolean
  read: boolean
  propose: boolean
  approve: boolean
  execute: boolean
  scope: string
  note: string
}
type Registry = {
  ok: boolean
  policy: string
  global_autonomy_switch: boolean
  capabilities: Record<string, Capability>
  error?: string
}

function Mark({ value }: { value: boolean }) {
  return value ? <Check className="mx-auto h-4 w-4 text-positive" /> : <Minus className="mx-auto h-4 w-4 text-muted-foreground/50" />
}

export function OwnerCapabilityRegistry() {
  const [data, setData] = useState<Registry | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/owner/capabilities", { cache: "no-store" })
      const body = (await response.json()) as Registry
      if (!response.ok || !body.ok) throw new Error(body.error || `Capability load failed (${response.status})`)
      setData(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Capability registry unavailable")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void load() }, [load])
  if (loading && !data) return <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Reading capability permissions…</div>

  return <div className="space-y-3">
    <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-sm font-medium text-foreground">Least-privilege capability matrix</p><p className="mt-1 text-xs text-muted-foreground">Permissions are independent per capability. There is no single global switch that grants AION unrestricted execution.</p></div><button type="button" onClick={() => void load()} className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs hover:bg-muted"><RefreshCw className="h-3.5 w-3.5" />Refresh</button></div>
    {error ? <p className="rounded-lg border border-critical/30 bg-critical/5 p-3 text-xs text-critical">{error}</p> : null}
    {data ? <div className="overflow-x-auto rounded-xl border border-border/70"><table className="w-full min-w-[700px] text-left text-xs"><thead className="bg-background/50 text-[0.65rem] uppercase tracking-wider text-muted-foreground"><tr><th className="px-3 py-2.5">Capability</th><th className="px-3 py-2.5 text-center">Configured</th><th className="px-3 py-2.5 text-center">Read</th><th className="px-3 py-2.5 text-center">Propose</th><th className="px-3 py-2.5 text-center">Approve</th><th className="px-3 py-2.5 text-center">Execute</th><th className="px-3 py-2.5">Scope</th></tr></thead><tbody className="divide-y divide-border/60">{Object.entries(data.capabilities).map(([name, cap]) => <tr key={name} className="align-top"><td className="px-3 py-3 font-medium capitalize text-foreground">{name.replaceAll("_", " ")}</td><td className="px-3 py-3"><Mark value={cap.configured} /></td><td className="px-3 py-3"><Mark value={cap.read} /></td><td className="px-3 py-3"><Mark value={cap.propose} /></td><td className="px-3 py-3"><Mark value={cap.approve} /></td><td className="px-3 py-3"><Mark value={cap.execute} /></td><td className="max-w-sm px-3 py-3 text-muted-foreground"><p>{cap.scope}</p><p className="mt-1 text-[0.68rem] text-muted-foreground/75">{cap.note}</p></td></tr>)}</tbody></table></div> : null}
    {data ? <p className="text-[0.7rem] text-muted-foreground">Policy · {data.policy} · Global unrestricted autonomy · {data.global_autonomy_switch ? "enabled" : "not available"}</p> : null}
  </div>
}
