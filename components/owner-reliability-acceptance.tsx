"use client"

import { useCallback, useEffect, useState } from "react"
import { CheckCircle2, Loader2, RefreshCw, TriangleAlert } from "lucide-react"
import { defer } from "@/lib/defer"

type Acceptance = {
  ok: boolean
  direct_openai: { accepted: boolean; conversations: number; gateway_conversations: number }
  durable_conversations: { total: number; with_user_messages: number; cross_conversation_ready: boolean }
  memory_provenance: { active: number; linked: number; coverage: number; new_writes_link_exact_source: boolean }
  paper_market: { live_snapshots_24h: number; fallback_snapshots_24h: number; live_trading: boolean; price_cache_seconds: number }
  runtime: {
    storage_configured: boolean
    cron_secret_configured: boolean
    terminal_executor_connected: boolean
    arbitrary_terminal_commands_enabled: boolean
    moltbook_outbound_enabled: boolean
    moltbook_execute_enabled: boolean
  }
  error?: string
}

function Check({ label, ok, detail }: { label: string; ok: boolean; detail: string }) {
  const Icon = ok ? CheckCircle2 : TriangleAlert
  return <div className="rounded-lg border border-border/70 bg-background/40 p-3"><div className="flex items-start gap-2"><Icon className={`mt-0.5 h-4 w-4 shrink-0 ${ok ? "text-positive" : "text-caution"}`} /><div><p className="text-xs font-medium text-foreground">{label}</p><p className="mt-1 text-[0.7rem] leading-relaxed text-muted-foreground">{detail}</p></div></div></div>
}

export function OwnerReliabilityAcceptance() {
  const [data, setData] = useState<Acceptance | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/owner/acceptance", { cache: "no-store" })
      const body = (await response.json()) as Acceptance
      if (!response.ok || !body.ok) throw new Error(body.error || `Acceptance check failed (${response.status})`)
      setData(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Acceptance evidence unavailable")
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

  if (loading && !data) return <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Reading acceptance evidence…</div>

  return <div className="space-y-3">
    <div className="flex items-center justify-between gap-3"><div><p className="text-sm font-medium text-foreground">Production acceptance evidence</p><p className="mt-1 text-xs text-muted-foreground">Grounded in durable AION state and current runtime gates.</p></div><button type="button" onClick={() => void load()} disabled={loading} className="inline-flex items-center gap-1.5 rounded-lg border border-border px-2.5 py-1.5 text-xs hover:bg-muted disabled:opacity-60">{loading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}Refresh</button></div>
    {error ? <p className="rounded-lg border border-critical/30 bg-critical/5 p-3 text-xs text-critical">{error}</p> : null}
    {data ? <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
      <Check label="Direct OpenAI" ok={data.direct_openai.accepted} detail={`${data.direct_openai.conversations} durable OpenAI Responses conversation(s); ${data.direct_openai.gateway_conversations} Gateway conversation(s).`} />
      <Check label="Cross-conversation durability" ok={data.durable_conversations.cross_conversation_ready} detail={`${data.durable_conversations.with_user_messages} conversation(s) contain durable user messages.`} />
      <Check label="Memory provenance" ok={data.memory_provenance.new_writes_link_exact_source} detail={`${data.memory_provenance.linked}/${data.memory_provenance.active} active memories currently linked; new explicit writes bind the exact source message.`} />
      <Check label="Paper-market isolation" ok={!data.paper_market.live_trading} detail={`${data.paper_market.live_snapshots_24h} live-public and ${data.paper_market.fallback_snapshots_24h} fallback snapshot(s) in 24h; ${data.paper_market.price_cache_seconds}s request cache; no live trading.`} />
      <Check label="Durable storage" ok={data.runtime.storage_configured} detail="Dedicated AION Postgres runtime is required for acceptance." />
      <Check label="Cron protection" ok={data.runtime.cron_secret_configured} detail="Scheduled operations remain protected by CRON_SECRET." />
      <Check label="Safe executor" ok={data.runtime.terminal_executor_connected && !data.runtime.arbitrary_terminal_commands_enabled} detail="Vercel Sandbox executor connected; arbitrary terminal commands remain disabled." />
      <Check label="External writes" ok={!data.runtime.moltbook_outbound_enabled && !data.runtime.moltbook_execute_enabled} detail="Moltbook approval and execute gates are currently locked unless separately activated." />
    </div> : null}
  </div>
}
