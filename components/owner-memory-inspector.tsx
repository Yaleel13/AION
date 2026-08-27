"use client"

import { useEffect, useState } from "react"
import { Brain, Loader2, LockKeyhole, RefreshCw } from "lucide-react"

type MemoryFact = {
  id: number
  content: string
  category: string | null
  status: "active" | "forgotten" | "superseded"
  superseded_by: number | null
  created_at: string
  updated_at: string
}

type MemoryResponse = {
  facts?: MemoryFact[]
  error?: string
}

export function OwnerMemoryInspector() {
  const [facts, setFacts] = useState<MemoryFact[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  async function refresh() {
    setLoading(true)
    try {
      const response = await fetch("/api/owner/memory?includeInactive=true", { cache: "no-store" })
      const body = (await response.json()) as MemoryResponse
      if (!response.ok) {
        setFacts([])
        setError(response.status === 401 ? "Unlock the owner session in Terminal to inspect memory." : body.error || `Memory inspector failed (${response.status})`)
        return
      }
      setFacts(body.facts ?? [])
      setError(null)
    } catch (reason) {
      setFacts([])
      setError(reason instanceof Error ? reason.message : "Memory inspector unavailable")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  const active = facts.filter((fact) => fact.status === "active")
  const inactive = facts.filter((fact) => fact.status !== "active")

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 text-sm text-foreground">
          <Brain className="h-4 w-4 text-gold" />
          <span>{active.length} active · {inactive.length} historical</span>
        </div>
        <button
          onClick={() => void refresh()}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground disabled:opacity-50"
        >
          {loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          Refresh
        </button>
      </div>

      {error ? (
        <div className="flex items-start gap-2 rounded-xl border border-border bg-background/40 p-3 text-xs text-muted-foreground">
          <LockKeyhole className="mt-0.5 h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      ) : loading ? (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Loader2 className="h-4 w-4 animate-spin" />
          Reading protected memory…
        </div>
      ) : facts.length === 0 ? (
        <p className="text-xs text-muted-foreground">No explicit long-term memories are stored.</p>
      ) : (
        <div className="max-h-80 space-y-2 overflow-y-auto pr-1">
          {facts.map((fact) => (
            <article key={fact.id} className="rounded-xl border border-border/70 bg-background/40 p-3">
              <div className="flex flex-wrap items-center gap-2 text-[0.65rem] uppercase tracking-wider text-muted-foreground">
                <span>{fact.category || "general"}</span>
                <span>·</span>
                <span>{fact.status}</span>
                <span>·</span>
                <span>#{fact.id}</span>
                {fact.superseded_by ? <span>→ #{fact.superseded_by}</span> : null}
              </div>
              <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">{fact.content}</p>
            </article>
          ))}
        </div>
      )}

      <p className="text-[0.7rem] leading-relaxed text-muted-foreground/80">
        Read-only inspector. Permanent memory changes occur only through explicit remember, forget, or exact replacement requests.
      </p>
    </div>
  )
}
