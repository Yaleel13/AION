"use client"

import { useEffect } from "react"
import { Github, TerminalSquare, HardDrive, Cloud, Server, Upload, X } from "lucide-react"

const options = [
  { icon: TerminalSquare, title: "Terminal Session", desc: "Owner-gated AION repository diagnostics in Vercel Sandbox", available: true },
  { icon: Github, title: "GitHub Repository", desc: "Not connected inside the deployed AION runtime yet", available: false },
  { icon: HardDrive, title: "Local Project", desc: "Unavailable from the hosted web runtime", available: false },
  { icon: Server, title: "Remote Workspace", desc: "No remote workspace connector is configured", available: false },
  { icon: Cloud, title: "Cloud Deployment", desc: "Runtime status is visible; deployment-control access is not connected", available: false },
  { icon: Upload, title: "Upload Files", desc: "File ingestion is not wired into AION yet", available: false },
]

export function ConnectionSheet({
  open,
  onClose,
  onConnect,
}: {
  open: boolean
  onClose: () => void
  onConnect: (title: string) => void
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose()
    if (open) window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, onClose])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center sm:items-center">
      <div className="absolute inset-0 animate-fade bg-background/70 backdrop-blur-sm" onClick={onClose} aria-hidden />
      <div
        role="dialog"
        aria-modal="true"
        aria-label="Connect AION"
        className="relative m-0 w-full max-w-lg animate-rise rounded-t-2xl border border-border bg-popover p-5 shadow-2xl sm:m-4 sm:rounded-2xl"
      >
        <div className="mb-4 flex items-start justify-between">
          <div>
            <h2 className="text-lg font-medium text-foreground">AION Connections</h2>
            <p className="mt-0.5 text-sm text-muted-foreground">
              Only capabilities actually connected to this deployed AION runtime are actionable here.
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
                  <span className="text-[0.62rem] uppercase tracking-wider text-muted-foreground">
                    {o.available ? "Available" : "Not connected"}
                  </span>
                </span>
                <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">{o.desc}</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
