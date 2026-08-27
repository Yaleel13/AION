"use client"

import { useEffect, useMemo, useState } from "react"
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
import { AionPresence } from "@/components/aion-presence"
import { CommandComposer } from "@/components/command-composer"
import { cn } from "@/lib/utils"

type RuntimeStatus = {
  ok: boolean
  source: string
  fixture: boolean
  storage: {
    backend: string
    configured: boolean
    schema: string | null
    detail: string | null
  }
  moltbook: {
    configured: boolean
    mode: string | null
    api_key_present: boolean
    outbound_enabled: boolean
    execute_enabled: boolean
    phase: string
  }
  autonomy: {
    mode: string
    dry_run: boolean
    live_writes_enabled: boolean
    experiment_active: boolean
  }
  kill_switch: {
    engaged: boolean
    reason?: string
  }
  paper_market_data: {
    price_mode: string
    live_trading: boolean
    note: string
  }
  providers: {
    openai_configured: boolean
    gemini_configured: boolean
  }
}

function Panel({
  title,
  subtitle,
  children,
  className,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <section
      className={cn(
        "flex flex-col rounded-2xl border border-border bg-surface/50 p-4 backdrop-blur-sm",
        className,
      )}
    >
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <h2 className="text-[0.7rem] font-medium uppercase tracking-[0.16em] text-muted-foreground">
          {title}
        </h2>
        {subtitle ? <span className="text-[0.7rem] text-muted-foreground/70">{subtitle}</span> : null}
      </div>
      {children}
    </section>
  )
}

function Gate({
  icon: Icon,
  label,
  value,
  detail,
  healthy,
}: {
  icon: typeof Database
  label: string
  value: string
  detail: string
  healthy: boolean
}) {
  return (
    <div className="rounded-xl border border-border/70 bg-background/40 p-3">
      <div className="flex items-start gap-3">
        <span
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg",
            healthy ? "bg-positive/10 text-positive" : "bg-caution/10 text-caution",
          )}
        >
          <Icon className="h-4 w-4" />
        </span>
        <div className="min-w-0">
          <p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">{label}</p>
          <p className="mt-0.5 text-sm font-medium text-foreground">{value}</p>
          <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{detail}</p>
        </div>
      </div>
    </div>
  )
}

export function Boardroom({
  presence,
  working,
  focus,
  onSubmit,
  onVoiceToggle,
  listening,
  onExit,
}: {
  presence: PresenceState
  working: PresenceState
  focus: { venture: string; reasoning: string } | null
  onSubmit: (text: string) => void
  onVoiceToggle: () => void
  listening: boolean
  onExit: () => void
}) {
  const [status, setStatus] = useState<RuntimeStatus | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true

    async function refresh() {
      try {
        const response = await fetch("/api/runtime/status", { cache: "no-store" })
        const body = (await response.json()) as RuntimeStatus & { error?: string }
        if (!response.ok || !body.ok) throw new Error(body.error || `Runtime status failed (${response.status})`)
        if (active) {
          setStatus(body)
          setError(null)
        }
      } catch (reason) {
        if (active) setError(reason instanceof Error ? reason.message : "Runtime status unavailable")
      }
    }

    void refresh()
    const interval = window.setInterval(refresh, 30_000)
    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [])

  const synthesis = useMemo(() => {
    if (!status) return null
    if (!status.storage.configured) {
      return "AION is online, but durable production storage is not configured. Scheduled operations and cross-session operational state must remain gated until Postgres is connected."
    }
    if (status.kill_switch.engaged) {
      return "AION's kill switch is engaged. Read-only visibility remains available while autonomous execution is blocked."
    }
    if (status.autonomy.live_writes_enabled) {
      return "AION has durable storage and live autonomy writes are enabled under the current policy gates."
    }
    return "AION's runtime is online with durable storage. Autonomous writes remain disabled or dry-run unless the owner explicitly activates them."
  }, [status])

  return (
    <div className="flex min-h-dvh flex-col animate-fade">
      <div className="relative flex flex-col items-center px-4 pb-6 pt-8 text-center">
        <button
          onClick={onExit}
          className="absolute left-4 top-6 inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground sm:left-8"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Conversation
        </button>

        <AionPresence state={presence} size={96} />
        <h1 className="mt-4 font-serif text-3xl font-light tracking-[0.12em] text-foreground">BOARDROOM</h1>
        <p className="mt-1 text-xs uppercase tracking-[0.24em] text-muted-foreground">
          Strategic Command · Live Runtime
        </p>
        <p className="mt-2 max-w-xl text-[0.7rem] text-muted-foreground/80">
          This view reports AION runtime gates only. Venture KPIs are not shown until their authenticated data sources are connected.
        </p>
      </div>

      <div className="mx-auto grid w-full max-w-6xl flex-1 grid-cols-1 gap-3 px-4 pb-40 lg:grid-cols-3">
        <Panel title="AION Brief" subtitle={status ? "Live · refreshes every 30s" : "Connecting"} className="lg:col-span-3">
          {error ? (
            <div className="flex items-start gap-3 rounded-xl border border-critical/30 bg-critical/5 p-4">
              <CircleAlert className="mt-0.5 h-5 w-5 shrink-0 text-critical" />
              <div>
                <p className="text-sm font-medium text-foreground">Live runtime status is unavailable.</p>
                <p className="mt-1 text-xs text-muted-foreground">{error}</p>
              </div>
            </div>
          ) : synthesis ? (
            <div className="flex items-start gap-3">
              <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gold/12 text-gold">
                <Sparkles className="h-4 w-4" />
              </span>
              <p className="max-w-4xl text-sm leading-relaxed text-foreground/90">{synthesis}</p>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              Reading AION runtime…
            </div>
          )}

          {focus ? (
            <div className="mt-4 rounded-xl border border-gold/40 bg-gold/8 p-4">
              <p className="flex items-center gap-2 text-sm font-medium text-gold">
                <Brain className="h-4 w-4" />
                Focus on {focus.venture}
              </p>
              <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">{focus.reasoning}</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Authenticated venture telemetry is not inferred from this focus request.
              </p>
            </div>
          ) : null}
        </Panel>

        {status ? (
          <>
            <Panel title="Runtime Gates" subtitle="Verified" className="lg:col-span-2">
              <div className="grid gap-2.5 sm:grid-cols-2">
                <Gate
                  icon={Database}
                  label="Storage"
                  value={status.storage.configured ? status.storage.backend : "Not durable"}
                  detail={status.storage.detail || "No storage detail reported."}
                  healthy={status.storage.configured && status.storage.backend === "postgres"}
                />
                <Gate
                  icon={Network}
                  label="Moltbook"
                  value={status.moltbook.mode || "Unconfigured"}
                  detail={`API key ${status.moltbook.api_key_present ? "present" : "absent"}; outbound ${status.moltbook.outbound_enabled ? "enabled" : "disabled"}.`}
                  healthy={status.moltbook.api_key_present && status.moltbook.mode === "live"}
                />
                <Gate
                  icon={status.kill_switch.engaged ? ShieldOff : ShieldCheck}
                  label="Kill switch"
                  value={status.kill_switch.engaged ? "Engaged" : "Clear"}
                  detail={status.kill_switch.engaged ? status.kill_switch.reason || "Execution is blocked." : "No emergency stop is engaged."}
                  healthy={!status.kill_switch.engaged}
                />
                <Gate
                  icon={Brain}
                  label="Direct providers"
                  value={status.providers.openai_configured || status.providers.gemini_configured ? "Configured" : "No direct key"}
                  detail={`OpenAI ${status.providers.openai_configured ? "configured" : "not configured"}; Gemini ${status.providers.gemini_configured ? "configured" : "not configured"}. Chat can use its separate Vercel Gateway fallback when available.`}
                  healthy={status.providers.openai_configured || status.providers.gemini_configured}
                />
              </div>
            </Panel>

            <Panel title="Autonomy">
              <dl className="space-y-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">Mode</dt>
                  <dd className="font-medium capitalize text-foreground">{status.autonomy.mode}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">Dry run</dt>
                  <dd className="font-medium text-foreground">{status.autonomy.dry_run ? "Yes" : "No"}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">Live writes</dt>
                  <dd className="font-medium text-foreground">{status.autonomy.live_writes_enabled ? "Enabled" : "Disabled"}</dd>
                </div>
                <div className="flex items-center justify-between gap-3">
                  <dt className="text-muted-foreground">Experiment</dt>
                  <dd className="font-medium text-foreground">{status.autonomy.experiment_active ? "Active" : "Inactive"}</dd>
                </div>
              </dl>
            </Panel>

            <Panel title="Paper Market" className="lg:col-span-2">
              <div className="flex items-start gap-3">
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground">
                  <FlaskConical className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-sm font-medium text-foreground">Price mode · {status.paper_market_data.price_mode}</p>
                  <p className="mt-1 text-xs leading-relaxed text-muted-foreground">{status.paper_market_data.note}</p>
                  <p className="mt-2 text-xs font-medium text-foreground">
                    Live trading · {status.paper_market_data.live_trading ? "Enabled" : "No"}
                  </p>
                </div>
              </div>
            </Panel>

            <Panel title="Next Operational Gate">
              <p className="text-sm leading-relaxed text-foreground/90">
                {!status.storage.configured
                  ? "Connect the dedicated AION Postgres database to unlock durable scheduled operations."
                  : !status.moltbook.api_key_present
                    ? "Connect the approved Moltbook credential before enabling live Moltbook execution."
                    : status.autonomy.dry_run
                      ? "Review policy and owner approvals before leaving dry-run mode."
                      : "Runtime gates are available; consequential actions still require their configured approval policy."}
              </p>
            </Panel>
          </>
        ) : null}
      </div>

      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border/60 bg-background/80 px-4 py-4 backdrop-blur-xl">
        <div className="mx-auto max-w-3xl">
          <CommandComposer
            onSubmit={onSubmit}
            onVoiceToggle={onVoiceToggle}
            listening={listening}
            placeholder="Ask AION about the live runtime or a decision…"
            disabled={working !== "idle" && working !== "complete"}
          />
        </div>
      </div>
    </div>
  )
}
