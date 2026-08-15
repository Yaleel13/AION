"use client"

import {
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Loader2,
  ShieldAlert,
  Github,
  CreditCard,
  Cloud,
  Mail,
  BookOpen,
  Brain,
  Clock,
  ChevronLeft,
} from "lucide-react"
import type { PresenceState } from "@/lib/aion/types"
import {
  brief,
  ventures,
  decisions,
  actions,
  signals,
  workingContext,
  timeline,
  type Health,
  type Venture,
} from "@/lib/aion/boardroom"
import { AionPresence } from "@/components/aion-presence"
import { CommandComposer } from "@/components/command-composer"
import { StatusDot } from "@/components/ui/status-dot"
import { cn } from "@/lib/utils"

const healthMeta: Record<Health, { tone: "positive" | "caution" | "critical" | "neutral"; label: string }> = {
  strong: { tone: "positive", label: "Strong" },
  steady: { tone: "neutral", label: "Steady" },
  watch: { tone: "caution", label: "Watch" },
  risk: { tone: "critical", label: "At risk" },
}

const signalIcon: Record<string, typeof Github> = {
  GitHub: Github,
  Stripe: CreditCard,
  Vercel: Cloud,
  Email: Mail,
  Research: BookOpen,
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
        {subtitle && <span className="text-[0.7rem] text-muted-foreground/70">{subtitle}</span>}
      </div>
      {children}
    </section>
  )
}

function VentureCard({ v, focused }: { v: Venture; focused: boolean }) {
  const meta = healthMeta[v.health]
  return (
    <div
      className={cn(
        "rounded-xl border p-3 transition-all",
        focused
          ? "border-gold/50 bg-gold/8 shadow-[0_0_0_1px_var(--gold)]"
          : "border-border/70 bg-background/40 hover:border-border-strong",
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-foreground">{v.name}</span>
        <span className="inline-flex items-center gap-1.5 text-[0.7rem] text-muted-foreground">
          <StatusDot tone={meta.tone} pulse={v.health === "watch" || v.health === "risk"} />
          {meta.label}
        </span>
      </div>
      <p className="mt-1 text-xs text-muted-foreground">{v.objective}</p>
      <div className="mt-3 flex items-end justify-between">
        <div>
          <p className="text-[0.6rem] uppercase tracking-wider text-muted-foreground">{v.kpi.label}</p>
          <p className="text-base font-medium tabular-nums text-foreground">{v.kpi.value}</p>
        </div>
        <p className="text-right text-[0.7rem] text-muted-foreground">{v.milestone}</p>
      </div>
      {v.alert && (
        <p className="mt-2 flex items-center gap-1.5 rounded-md bg-caution/10 px-2 py-1 text-[0.7rem] text-caution">
          <ShieldAlert className="h-3 w-3" />
          {v.alert}
        </p>
      )}
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
  return (
    <div className="flex min-h-dvh flex-col animate-fade">
      {/* Boardroom header */}
      <div className="relative flex flex-col items-center px-4 pb-6 pt-8 text-center">
        <button
          onClick={onExit}
          className="absolute left-4 top-6 inline-flex items-center gap-1 rounded-lg px-2 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-muted hover:text-foreground sm:left-8"
        >
          <ChevronLeft className="h-3.5 w-3.5" />
          Conversation
        </button>

        <AionPresence state={presence} size={96} />
        <h1 className="mt-4 font-serif text-3xl font-light tracking-[0.12em] text-foreground">
          BOARDROOM
        </h1>
        <p className="mt-1 text-xs uppercase tracking-[0.24em] text-muted-foreground">
          Strategic Command
        </p>
      </div>

      {/* Modular grid */}
      <div className="mx-auto grid w-full max-w-6xl flex-1 grid-cols-1 gap-3 px-4 pb-40 lg:grid-cols-3">
        {/* AION Brief — spans full width on top */}
        <Panel title="AION Brief" className="lg:col-span-3">
          <div className="flex items-start gap-3">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-gold/12 text-gold">
              <Sparkles className="h-4 w-4" />
            </span>
            <div>
              <p className="font-serif text-lg font-light text-foreground">{brief.headline}</p>
              <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-muted-foreground">
                {brief.synthesis}
              </p>
            </div>
          </div>

          {focus && (
            <div className="mt-4 animate-rise rounded-xl border border-gold/40 bg-gold/8 p-4">
              <p className="flex items-center gap-2 text-sm font-medium text-gold">
                <Brain className="h-4 w-4" />
                Focus on {focus.venture}
              </p>
              <p className="mt-1.5 text-sm leading-relaxed text-foreground/90">{focus.reasoning}</p>
            </div>
          )}
        </Panel>

        {/* Active Ventures */}
        <Panel title="Active Ventures" subtitle={`${ventures.length} connected`} className="lg:col-span-2">
          <div className="grid gap-2.5 sm:grid-cols-2">
            {ventures.map((v) => (
              <VentureCard key={v.name} v={v} focused={focus?.venture === v.name} />
            ))}
          </div>
        </Panel>

        {/* Signals */}
        <Panel title="Signals" subtitle="Live">
          <ul className="space-y-2.5">
            {signals.map((s, i) => {
              const Icon = signalIcon[s.source] ?? BookOpen
              return (
                <li key={i} className="flex items-start gap-2.5">
                  <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                    <Icon className="h-3.5 w-3.5" />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm leading-snug text-foreground/90">{s.message}</p>
                    <p className="mt-0.5 flex items-center gap-1.5 text-[0.7rem] text-muted-foreground">
                      <StatusDot tone={s.tone} />
                      {s.source} · {s.when} ago
                    </p>
                  </div>
                </li>
              )
            })}
          </ul>
        </Panel>

        {/* Decisions */}
        <Panel title="Decisions" subtitle={`${decisions.length} waiting`} className="lg:col-span-2">
          <div className="grid gap-2.5 sm:grid-cols-2">
            {decisions.map((d, i) => (
              <div key={i} className="rounded-xl border border-border/70 bg-background/40 p-3">
                <p className="text-sm font-medium text-foreground">{d.title}</p>
                <div className="mt-2 flex items-center gap-3 text-xs">
                  <span className="inline-flex items-center gap-1.5 text-gold">
                    <Sparkles className="h-3 w-3" />
                    {d.recommendation}
                  </span>
                  <span className="text-muted-foreground">Confidence · {d.confidence}</span>
                </div>
                <ul className="mt-2.5 space-y-1">
                  {d.reasons.map((r, j) => (
                    <li key={j} className="flex gap-2 text-xs leading-snug text-muted-foreground">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-muted-foreground/60" />
                      {r}
                    </li>
                  ))}
                </ul>
                <button className="mt-3 inline-flex items-center gap-1 rounded-md bg-gold px-3 py-1.5 text-xs font-medium text-gold-foreground transition-colors hover:bg-gold/90">
                  Review
                  <ArrowRight className="h-3 w-3" />
                </button>
              </div>
            ))}
          </div>
        </Panel>

        {/* Actions */}
        <Panel title="Actions">
          <ul className="space-y-2">
            {actions.map((a, i) => (
              <li key={i} className="flex items-center gap-2.5 text-sm">
                {a.status === "complete" && <CheckCircle2 className="h-4 w-4 shrink-0 text-positive" />}
                {a.status === "running" && <Loader2 className="h-4 w-4 shrink-0 animate-spin text-gold" />}
                {a.status === "approval" && <ShieldAlert className="h-4 w-4 shrink-0 text-caution" />}
                <span className="flex-1 text-foreground/90">{a.label}</span>
                <span className="text-[0.7rem] capitalize text-muted-foreground">
                  {a.status === "approval" ? "Needs approval" : a.status}
                </span>
              </li>
            ))}
          </ul>
        </Panel>

        {/* Working Context */}
        <Panel title="Working Context" className="lg:col-span-2">
          <dl className="grid gap-3 sm:grid-cols-2">
            {workingContext.map((c) => (
              <div key={c.label}>
                <dt className="text-[0.7rem] uppercase tracking-wider text-muted-foreground">{c.label}</dt>
                <dd className="mt-0.5 text-sm leading-snug text-foreground/85">{c.value}</dd>
              </div>
            ))}
          </dl>
        </Panel>

        {/* Timeline */}
        <Panel title="Timeline" className="lg:col-span-3">
          <ol className="relative ml-1 space-y-4 border-l border-border pl-5">
            {timeline.map((t, i) => (
              <li key={i} className="relative">
                <span className="absolute -left-[1.42rem] top-1 flex h-2.5 w-2.5 items-center justify-center">
                  <Clock className="h-2.5 w-2.5 text-muted-foreground" />
                </span>
                <p className="text-sm text-foreground/90">{t.event}</p>
                <p className="mt-0.5 text-[0.7rem] text-muted-foreground">{t.when}</p>
              </li>
            ))}
          </ol>
        </Panel>
      </div>

      {/* Boardroom command bar */}
      <div className="fixed inset-x-0 bottom-0 z-30 border-t border-border/60 bg-background/80 px-4 py-4 backdrop-blur-xl">
        <div className="mx-auto max-w-3xl">
          <CommandComposer
            onSubmit={onSubmit}
            onVoiceToggle={onVoiceToggle}
            listening={listening}
            placeholder="Ask AION about anything in the Boardroom…"
            disabled={working !== "idle" && working !== "complete"}
          />
        </div>
      </div>
    </div>
  )
}
