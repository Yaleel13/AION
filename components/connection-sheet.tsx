"use client"

import { useEffect } from "react"
import { Github, TerminalSquare, HardDrive, Cloud, Server, Upload, X } from "lucide-react"

const options = [
  { icon: Github, title: "GitHub Repository", desc: "Read, review and open pull requests" },
  { icon: TerminalSquare, title: "Terminal Session", desc: "Run commands with your approval" },
  { icon: HardDrive, title: "Local Project", desc: "Work against a project on this machine" },
  { icon: Server, title: "Remote Workspace", desc: "Attach to a live remote environment" },
  { icon: Cloud, title: "Cloud Deployment", desc: "Inspect Vercel or other hosting" },
  { icon: Upload, title: "Upload Files", desc: "Add documents, data or media" },
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
            <h2 className="text-lg font-medium text-foreground">Connect AION</h2>
            <p className="mt-0.5 text-sm text-muted-foreground">
              Choose what AION should work with. Access is scoped and revocable.
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
              onClick={() => onConnect(o.title)}
              className="group flex items-start gap-3 rounded-xl border border-border bg-surface/50 p-3 text-left transition-colors hover:border-border-strong hover:bg-surface"
            >
              <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-muted text-muted-foreground transition-colors group-hover:bg-gold/12 group-hover:text-gold">
                <o.icon className="h-4.5 w-4.5" />
              </span>
              <span className="min-w-0">
                <span className="block text-sm font-medium text-foreground">{o.title}</span>
                <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">{o.desc}</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
