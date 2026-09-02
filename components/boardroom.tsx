"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import {
  Brain,
  ChevronLeft,
  CircleAlert,
  Database,
  FlaskConical,
  Loader2,
  Network,
  ShieldCheck,
  ShieldOff,
  Sparkles,
} from "lucide-react"
import type { PresenceState } from "@/lib/aion/types"
import type { RuntimeStatus } from "@/lib/aion/runtime-status"
import { signals as demoSignals } from "@/lib/aion/boardroom"
import { FactProvenanceBadge } from "@/components/fact-provenance-badge"
import { ConvergenceRail } from "@/components/convergence-rail"
import { CommandComposer } from "@/components/command-composer"
import { OwnerCapabilityRegistry } from "@/components/owner-capability-registry"
import { OwnerCommercialExecution } from "@/components/owner-commercial-execution"
import { OwnerMemoryInspector } from "@/components/owner-memory-inspector"
import { OwnerMoltbookResearch } from "@/components/owner-moltbook-research"
import { OwnerOpportunityReview } from "@/components/owner-opportunity-review"
import { OwnerOperatorBriefing } from "@/components/owner-operator-briefing"
import { OwnerPaymentRail } from "@/components/owner-payment-rail"
import { OwnerReliabilityAcceptance } from "@/components/owner-reliability-acceptance"
import { defer } from "@/lib/defer"
import { cn } from "@/lib/utils"
import { AION_CANON_PORTRAIT } from "@/lib/aion/canon-portrait"

type RuntimeStatusView = RuntimeStatus

function Chamber({ title, subtitle, children, className }: { title: string; subtitle?: string; children: React.ReactNode; className?: string }) {
  return (
    <section className={cn("relative overflow-hidden border border-cyan/15 bg-surface/35 p-4 backdrop-blur-md sm:p-5", className)}>
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-cyan/55 to-transparent" aria-hidden />
      <div className="mb-4 flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-[0.68rem] font-medium uppercase tracking-[0.22em] text-cyan/80">{title}</h2>
        {subtitle ? <span className="text-[0.66rem] uppercase tracking-[0.14em] text-muted-foreground/70">{subtitle}</span> : null}
      </div>
      {children}
    </section>
  )
}

function Gate({ icon: Icon, label, value, detail, healthy }: { icon: typeof Database; label: string; value: string; detail: string; healthy: boolean }) {
  return (
    <div className="relative border-l border-cyan/20 bg-background/25 px-3 py-3.5">
      <div className="flex items-start gap-3">
        <span className={cn("flex h-8 w-8 shrink-0 items-center justify-center rounded-full border", healthy ? "border-positive/30 bg-positive/8 text-positive" : "border-caution/30 bg-caution/8 text-caution")}>
          <Icon className="h-4 w-4" />
        </span>
        <div className="min-w-0">
          <p className="text-[0.62rem] uppercase tracking-[0.18em] text-muted-foreground">{label}</p>
          <p className="mt-1 text-sm font-medium text-foreground">{value}</p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{detail}</p>
        </div>
      </div>
    </div>
  )
}

export function Boardroom({ presence, working, focus, onSubmit, onVoiceToggle, listening, onExit, onOpenConnections }: { presence: PresenceState; working: PresenceState; focus: { venture: string; reasoning: string } | null; onSubmit: (text: string) => void; onVoiceToggle: () => void; listening: boolean; onExit: () => void; onOpenConnections?: () => void }) {
  const [status, setStatus] = useState<RuntimeStatusView | null>(null)
  const [error, setError] = useState<string | null>(null)

  const refreshStatus = useCallback(async () => {
    try {
      const response = await fetch("/api/runtime/status", { cache: "no-store" })
      const body = (await response.json()) as RuntimeStatusView & { error?: string }
      if (!response.ok || !body.ok) throw new Error(body.error || `Runtime status failed (${response.status})`)
      setStatus(body)
      setError(null)
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Runtime status unavailable")
    }
  }, [])

  useEffect(() => {
    defer(() => { void refreshStatus() })
    const interval = window.setInterval(() => void refreshStatus(), 30_000)
    const refresh = () => void refreshStatus()
    window.addEventListener("aion:boardroom-refresh", refresh)
    return () => {
      window.clearInterval(interval)
      window.removeEventListener("aion:boardroom-refresh", refresh)
    }
  }, [refreshStatus])

  const synthesis = useMemo(() => {
    if (!status) return null
    if (!status.storage.configured) return "AION is online, but durable production storage is not configured. Scheduled operations and cross-session operational state must remain gated until Postgres is connected."
    if (status.kill_switch.engaged) return "AION's kill switch is engaged. Read-only visibility remains available while autonomous execution is blocked."
    if (status.autonomy.live_writes_enabled) return "AION has durable storage and live autonomy writes are enabled under the current policy gates."
    return "AION's runtime is online with durable storage. Permissions are capability-specific; unrestricted global autonomy is not available."
  }, [status])

  return (
    <div className="relative flex min-h-dvh flex-col animate-fade overflow-hidden bg-background">
      <div className="pointer-events-none fixed inset-0 aion-grid opacity-25" aria-hidden />
      <div className="pointer-events-none fixed inset-x-0 top-0 h-64 bg-gradient-to-b from-violet/12 via-cyan/5 to-transparent" aria-hidden />
      <div className="pointer-events-none fixed left-1/2 top-20 h-64 w-64 -translate-x-1/2 rounded-full bg-cyan/5 blur-3xl sm:top-24 sm:h-72 sm:w-72" aria-hidden />

      <header className="relative z-10 border-b border-cyan/10 px-4 pb-4 pt-5 sm:px-8 sm:pb-5 sm:pt-8">
        <button type="button" onClick={onExit} className="absolute left-3 top-3 inline-flex min-h-10 items-center gap-1.5 rounded-lg border border-transparent px-2.5 py-2 text-xs text-muted-foreground transition-colors hover:border-cyan/20 hover:bg-cyan/5 hover:text-foreground sm:left-8 sm:top-7" aria-label="Return to conversation">
          <ChevronLeft className="h-3.5 w-3.5" />Conversation
        </button>

        <div className="mx-auto flex max-w-4xl flex-col items-center text-center pt-8 sm:pt-0">
          <div className="relative h-24 w-24 overflow-hidden rounded-full border border-cyan/25 bg-cyan/5 shadow-[0_0_42px_rgba(0,190,255,.14)] sm:h-28 sm:w-28">
            <img src={AION_CANON_PORTRAIT} alt="Aion" className="h-full w-full object-cover object-top" />
            <div className="pointer-events-none absolute inset-0 rounded-full ring-1 ring-inset ring-white/5" aria-hidden />
          </div>
          <h1 className="mt-3 font-serif text-3xl font-light tracking-[0.12em] text-foreground sm:text-4xl sm:tracking-[0.14em]">BOARDROOM</h1>
          <p className="mt-1.5 text-[0.62rem] uppercase tracking-[0.22em] text-cyan/70 sm:mt-2 sm:text-[0.68rem] sm:tracking-[0.28em]">The deeper operational chamber</p>
          <p className="mt-2 max-w-2xl text-[0.72rem] leading-relaxed text-muted-foreground sm:mt-3 sm:text-sm">
            Owner-only command space for live runtime evidence, memory, research, capability permissions, opportunity review, and controlled execution.
          </p>
        </div>
        <div className="mt-4 sm:mt-5">
          <ConvergenceRail state={presence} />
        </div>
      </header>

      <main className="relative z-10 mx-auto grid w-full max-w-6xl flex-1 grid-cols-1 gap-3 px-3 pb-6 pt-4 sm:px-4 sm:pt-5 lg:grid-cols-12">
        <Chamber title="AION Brief" subtitle={status ? "live convergence" : "connecting"} className="lg:col-span-12">
          {error ? (
            <div className="flex items-start gap-3 border border-critical/25 bg-critical/5 p-4">
              <CircleAlert className="mt-0.5 h-5 w-5 shrink-0 text-critical" />
              <div>
                <p className="text-sm font-medium text-foreground">Live runtime status is unavailable.</p>
                <p className="mt-1 text-xs text-muted-foreground">{error}</p>
                <button type="button" onClick={() => void refreshStatus()} className="mt-3 min-h-10 border border-cyan/20 px-3 py-2 text-xs text-foreground transition-colors hover:bg-cyan/5">Retry status</button>
              </div>
            </div>
          ) : synthesis ? (
            <div className="flex items-start gap-3">
              <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-cyan/25 bg-cyan/8 text-cyan"><Sparkles className="h-4 w-4" /></span>
              <div>
                <p className="max-w-4xl text-sm leading-relaxed text-foreground/90">{synthesis}</p>
                <p className="mt-2 text-[0.65rem] uppercase tracking-[0.18em] text-muted-foreground/60">Runtime refreshed after actions and every 30 seconds</p>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground"><Loader2 className="h-4 w-4 animate-spin" />Reading AION runtime…</div>
          )}
          {focus ? (
            <div className="mt-4 border-l border-violet/50 bg-violet/5 px-4 py-3">
              <p className="flex items-center gap-2 text-sm font-medium text-violet"><Brain className="h-4 w-4" />Focus on {focus.venture}</p>
              <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">{focus.reasoning}</p>
              <p className="mt-1 text-xs text-muted-foreground">Authenticated venture telemetry is not inferred from this focus request.</p>
            </div>
          ) : null}
        </Chamber>

        {status ? <>
          <Chamber title="Runtime Gates" subtitle="verified systems" className="lg:col-span-8">
            <div className="grid gap-2 sm:grid-cols-2">
              <Gate icon={Database} label="Storage" value={status.storage.configured ? status.storage.backend : "Not durable"} detail={status.storage.detail || "No storage detail reported."} healthy={status.storage.configured && status.storage.backend === "postgres"} />
              <Gate icon={Network} label="Moltbook" value={status.moltbook.mode || "Unconfigured"} detail={`API key ${status.moltbook.api_key_present ? "present" : "absent"}; outbound ${status.moltbook.outbound_enabled ? "enabled" : "disabled"}; execution ${status.moltbook.execute_enabled ? "enabled" : "disabled"}.`} healthy={status.moltbook.api_key_present && status.moltbook.mode === "live"} />
              <Gate icon={status.kill_switch.engaged ? ShieldOff : ShieldCheck} label="Kill switch" value={status.kill_switch.engaged ? "Engaged" : "Clear"} detail={status.kill_switch.engaged ? status.kill_switch.reason || "Execution is blocked." : "No emergency stop is engaged."} healthy={!status.kill_switch.engaged} />
              <Gate icon={Brain} label="Direct providers" value={status.providers.openai_configured || status.providers.gemini_configured ? "Configured" : "No direct key"} detail={`OpenAI ${status.providers.openai_configured ? "configured" : "not configured"}; Gemini ${status.providers.gemini_configured ? "configured" : "not configured"}.`} healthy={status.providers.openai_configured || status.providers.gemini_configured} />
            </div>
          </Chamber>

          <Chamber title="Autonomy" subtitle="current policy" className="lg:col-span-4">
            <dl className="divide-y divide-cyan/10 text-sm">
              <div className="flex items-center justify-between gap-3 py-2.5 first:pt-0"><dt className="text-muted-foreground">Mode</dt><dd className="font-medium capitalize text-foreground">{status.autonomy.mode}</dd></div>
              <div className="flex items-center justify-between gap-3 py-2.5"><dt className="text-muted-foreground">Dry run</dt><dd className="font-medium text-foreground">{status.autonomy.dry_run ? "Yes" : "No"}</dd></div>
              <div className="flex items-center justify-between gap-3 py-2.5"><dt className="text-muted-foreground">Live writes</dt><dd className="font-medium text-foreground">{status.autonomy.live_writes_enabled ? "Enabled" : "Disabled"}</dd></div>
              <div className="flex items-center justify-between gap-3 py-2.5 pb-0"><dt className="text-muted-foreground">Experiment</dt><dd className="font-medium text-foreground">{status.autonomy.experiment_active ? "Active" : "Inactive"}</dd></div>
            </dl>
          </Chamber>

          <Chamber title="Fixture Signals" subtitle="demo only · not live integrations" className="lg:col-span-12">
            <p className="mb-3 text-xs leading-relaxed text-muted-foreground">
              Illustrative integration examples for design review. These are excluded from runtime metrics, alerts, and recommendations.
            </p>
            <ul className="divide-y divide-cyan/10">
              {demoSignals.map((signal) => (
                <li key={signal.source_object_id} className="flex flex-wrap items-start justify-between gap-3 py-3 first:pt-0">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-foreground">{signal.value.source}</p>
                    <p className="mt-1 text-sm text-foreground/85">{signal.value.message}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{signal.value.when} ago · tone {signal.value.tone}</p>
                  </div>
                  <FactProvenanceBadge envelope={signal} compact />
                </li>
              ))}
            </ul>
          </Chamber>

          <Chamber title="Reliability Acceptance" subtitle="Phase 8 · production evidence" className="lg:col-span-12"><OwnerReliabilityAcceptance /></Chamber>
          <Chamber title="Capability Permissions" subtitle="Phase 9 · least privilege" className="lg:col-span-12"><OwnerCapabilityRegistry /></Chamber>
          <Chamber title="Operator Briefing" subtitle="Phase 9 · owner priorities" className="lg:col-span-12"><OwnerOperatorBriefing /></Chamber>
          <Chamber title="Moltbook Research" subtitle="Stage 2 · read-only" className="lg:col-span-12"><OwnerMoltbookResearch /></Chamber>
          <Chamber title="Opportunity Review" subtitle="Phases 5–7 · owner controlled" className="lg:col-span-12"><OwnerOpportunityReview /></Chamber>
          <Chamber title="Commercial Pursuit Execution" subtitle="owner gated · exact-content controls" className="lg:col-span-12"><OwnerCommercialExecution /></Chamber>
          <Chamber title="Payment Rail" subtitle="owner only · live verification" className="lg:col-span-12"><OwnerPaymentRail /></Chamber>
          <Chamber title="Long-term Memory" subtitle="owner only · read-only" className="lg:col-span-12"><OwnerMemoryInspector /></Chamber>

          <Chamber title="Paper Market" subtitle="simulation only" className="lg:col-span-7">
            <div className="flex items-start gap-3">
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-cyan/20 bg-cyan/5 text-cyan"><FlaskConical className="h-4 w-4" /></span>
              <div><p className="text-sm font-medium text-foreground">Price mode · {status.paper_market_data.price_mode}</p><p className="mt-1 text-xs leading-relaxed text-muted-foreground">{status.paper_market_data.note}</p><p className="mt-2 text-xs font-medium text-foreground">Live trading · {status.paper_market_data.live_trading ? "Enabled" : "No"}</p></div>
            </div>
          </Chamber>

          <Chamber title="Next Operational Gate" subtitle="path forward" className="lg:col-span-5">
            <p className="text-sm leading-relaxed text-foreground/90">{!status.storage.configured ? "Connect the dedicated AION Postgres database to unlock durable scheduled operations." : !status.moltbook.api_key_present ? "Connect the approved Moltbook credential before enabling live Moltbook research." : !status.moltbook.outbound_enabled ? "Research, review, pursuit packets, and preparation are active. Controlled commercial approval remains locked until the outbound gate is enabled." : !status.moltbook.execute_enabled ? "Exact commercial content can be owner-approved, but publishing remains separately locked until the execute gate is enabled." : "Eligible commercial comments can proceed only through Prepare → Approve exact content → Execute with a single-use token, quotas, and the kill switch."}</p>
          </Chamber>
        </> : null}
      </main>

      <div className="sticky inset-x-0 bottom-0 z-30 mt-auto border-t border-cyan/15 bg-background/92 px-3 py-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] backdrop-blur-xl sm:px-4 sm:py-4">
        <div className="mx-auto max-w-3xl">
          <CommandComposer onSubmit={onSubmit} onVoiceToggle={onVoiceToggle} listening={listening} placeholder="Ask AION about the live runtime, a venture, or a decision…" disabled={working !== "idle" && working !== "complete"} onOpenConnections={onOpenConnections} />
        </div>
      </div>
    </div>
  )
}
