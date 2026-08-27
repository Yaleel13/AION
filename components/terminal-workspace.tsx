"use client"

import { X, Terminal, ShieldAlert } from "lucide-react"

export function TerminalWorkspace({ onClose }: { onClose: () => void }) {
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-border bg-[oklch(0.12_0.008_285)]">
      <div className="flex items-center justify-between gap-3 border-b border-border bg-surface/40 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-gold" />
          <span className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            AION Terminal · Executor not connected
          </span>
        </div>
        <button
          onClick={onClose}
          className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="Close terminal"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="flex flex-1 items-center justify-center p-6">
        <div className="max-w-md rounded-xl border border-caution/30 bg-caution/5 p-5 text-center">
          <ShieldAlert className="mx-auto h-7 w-7 text-caution" />
          <p className="mt-3 text-sm font-medium text-foreground">No live shell session is attached.</p>
          <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
            AION will not display simulated command output as if it were execution. A secure executor must be connected before terminal commands, repository writes, or remote shell actions can run here.
          </p>
          <p className="mt-3 text-[0.7rem] text-muted-foreground">
            Consequential commands will remain subject to owner approval even after an executor is connected.
          </p>
        </div>
      </div>
    </div>
  )
}
