"use client"

import { useEffect, useMemo, useState } from "react"
import { Github, TerminalSquare, HardDrive, Cloud, Server, Upload, X, Database, CreditCard, BrainCircuit, BarChart3, Globe2 } from "lucide-react"

type ExternalConnection = {
  connected?: boolean
  actionable?: boolean
  mode?: string | null
  note?: string
  approval_gate?: string
  execute_gate?: string
}

type RuntimeStatus = {
  external_connections?: Record<string, ExternalConnection>
}

type ConnectionOption = {
  key: string
  icon: typeof TerminalSquare
  title: string
  desc: string
  fallbackAvailable?: boolean
}

const baseOptions: ConnectionOption[] = [
  { key: "terminal", icon: TerminalSquare, title: "Terminal Session", desc: "Owner-gated repository diagnostics in Vercel Sandbox" },
  { key: "github", icon: Github, title: "GitHub Repository", desc: "Server-side repository access for source, code changes, and fulfillment assets" },
  { key: "vercel", icon: Cloud, title: "Cloud Deployment", desc: "Production runtime plus deployment-control readiness" },
  { key: "supabase_postgres", icon: Database, title: "Supabase / Postgres", desc: "Durable operational storage and ledgers" },
  { key: "stripe", icon: CreditCard, title: "Stripe", desc: "Checkout and payment collection readiness" },
  { key: "openai", icon: BrainCircuit, title: "OpenAI", desc: "Primary reasoning and generation provider" },
  { key: "posthog", icon: BarChart3, title: "PostHog", desc: "Product analytics runtime configuration" },
  { key: "google", icon: Globe2, title: "Google", desc: "Runtime Google credentials for Drive/Cloud workflows" },
  { key: "moltbook", icon: Server, title: "Moltbook", desc: "Public research and controlled outbound gates" },
  { key: "local", icon: HardDrive, title: "Local Project", desc: "Unavailable from the hosted web runtime", fallbackAvailable: false },
  { key: "upload", icon: Upload, title: "Upload Files", desc: "File ingestion is not wired into AION yet", fallbackAvailable: false },
]

function statusLabel(connection: ExternalConnection | undefined, fallbackAvailable = false) {
  if (!connection) return fallbackAvailable ? "Available" : "Not connected"
  if (connection.actionable) return "Actionable"
  if (connection.connected) return "Connected"
  return "Not connected"
}

export function ConnectionSheet({
  open,
  onClose,
  onConnect,
}: {
  open: boolean
  onClose: () => void
  onConnect: (title: string) => void
}) {
  const [runtime, setRuntime] = useState<RuntimeStatus | null>(null)

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose()
    if (open) window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, onClose])

  useEffect(() => {
    if (!open) return
    let cancelled = false
    void fetch("/api/runtime/status", { cache: "no-store" })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error(`status ${res.status}`))))
      .then((data) => {
        if (!cancelled) setRuntime(data as RuntimeStatus)
      })
      .catch(() => {
        if (!cancelled) setRuntime(null)
      })
    return () => {
      cancelled = true
    }
  }, [open])

  const options = useMemo(
    () =>
      baseOptions.map((option) => {
        const connection = runtime?.external_connections?.[option.key]
        const available = Boolean(connection?.actionable || option.fallbackAvailable)
        const desc = connection?.note ? `${option.desc}. ${connection.note}` : option.desc
        return {
          ...option,
          connection,
          available,
          desc,
          label: statusLabel(connection, option.fallbackAvailable),
        }
      }),
    [runtime],
  )

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      <div className="absolute inset-0 animate-fade bg-background/70 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Connect AION"
        className="relative m-0 w-full max-w-2xl animate-rise rounded-t-2xl border border-border bg-popover p-5 shadow-2xl sm:m-4 sm:rounded-2xl"
      >
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-medium text-foreground">AION Connections</h2>
            <p className="mt-0.5 text-sm text-muted-foreground">
              This panel reflects credentials and capabilities available inside the deployed AION runtime, not connections available only to ChatGPT or the owner externally.
            </p>
          </div>
          <button
            onClick={onClose}
            className="rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="grid gap-2 sm:grid-cols-2">
          {options.map((o) => (
            <button
              key={o.title}
              type="button"
              onClick={() => o.available && onConnect(o.title)}
              disabled={!o.available}
              className="group flex items-start gap-3 rounded-xl border border-border bg-surface/50 p-3 text-left transition-colors enabled:hover:border-border-strong enabled:hover:bg-surface disabled:cursor-not-allowed disabled:opacity-55"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground transition-colors group-enabled:group-hover:bg-gold/12 group-enabled:group-hover:text-gold">
                <o.icon className="h-4.5 w-4.5" />
              </span>
              <span className="min-w-0">
                <span className="flex items-center gap-2 text-sm font-medium text-foreground">
                  {o.title}
                  <span className="text-[0.62rem] uppercase tracking-wider text-muted-foreground">{o.label}</span>
                </span>
                <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">{o.desc}</span>
                {o.key === "moltbook" && o.connection ? (
                  <span className="mt-1 block text-[0.68rem] text-muted-foreground">
                    Approval: {o.connection.approval_gate ?? "locked"} · Execute: {o.connection.execute_gate ?? "locked"}
                  </span>
                ) : null}
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
