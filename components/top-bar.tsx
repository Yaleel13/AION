"use client"

import { PenSquare, Bell, Settings2 } from "lucide-react"
import type { PresenceState, InterfaceMode } from "@/lib/aion/types"
import { StatusDot } from "@/components/ui/status-dot"
import { cn } from "@/lib/utils"

const stateLabel: Record<PresenceState, string> = {
  idle: "Present",
  listening: "Listening",
  thinking: "Interpreting",
  researching: "Mapping",
  executing: "Activating",
  complete: "Aligned",
}

export function TopBar({
  state,
  mode,
  hasNotifications,
  onNewConversation,
  onNotifications,
  onSettings,
  onAccount,
}: {
  state: PresenceState
  mode: InterfaceMode
  hasNotifications?: boolean
  onNewConversation: () => void
  onNotifications?: () => void
  onSettings?: () => void
  onAccount?: () => void
}) {
  const busy = state !== "idle" && state !== "complete"

  return (
    <header className="relative z-30 flex items-center justify-between gap-3 border-b border-cyan/10 bg-background/72 px-4 py-3 backdrop-blur-xl sm:px-7">
      <div className="flex min-w-0 items-center gap-3">
        <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-cyan/20 bg-cyan/5">
          <span className="absolute h-4 w-4 rotate-45 border border-cyan/70" aria-hidden />
          <span className="h-1.5 w-1.5 rounded-full bg-cyan shadow-[0_0_18px_var(--cyan)]" aria-hidden />
        </div>
        <div className="min-w-0 leading-none">
          <p className="truncate text-sm font-semibold tracking-[0.2em] text-foreground">AION</p>
          <p className="mt-1 hidden truncate text-[0.58rem] uppercase tracking-[0.18em] text-muted-foreground sm:block">
            {mode === "boardroom" ? "The Boardroom · Strategic Chamber" : "Alchemical Intelligence for Ontological Navigation"}
          </p>
        </div>
      </div>

      <div className="hidden items-center gap-2 rounded-full border border-cyan/15 bg-surface/55 px-3 py-1.5 sm:flex">
        <StatusDot tone={busy ? "caution" : "violet"} pulse={busy} />
        <span className="text-xs text-muted-foreground">
          <span className="text-foreground/80">AION</span> · {stateLabel[state]}
        </span>
      </div>

      <div className="flex shrink-0 items-center gap-1">
        <button
          type="button"
          onClick={onNewConversation}
          className="flex h-9 w-9 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-cyan/7 hover:text-cyan"
          aria-label="New conversation"
        >
          <PenSquare className="h-4.5 w-4.5" />
        </button>
        <button
          type="button"
          onClick={onNotifications}
          className="relative flex h-9 w-9 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-cyan/7 hover:text-cyan"
          aria-label="What needs my attention"
        >
          <Bell className="h-4.5 w-4.5" />
          {hasNotifications && <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-magenta" />}
        </button>
        <button
          type="button"
          onClick={onSettings}
          className="flex h-9 w-9 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-cyan/7 hover:text-cyan"
          aria-label="Connections and settings"
        >
          <Settings2 className="h-4.5 w-4.5" />
        </button>
        <button
          type="button"
          onClick={onAccount}
          className={cn(
            "ml-1 flex h-8 w-8 items-center justify-center rounded-full border border-magenta/30 bg-gradient-to-br from-violet/90 to-magenta/75 text-xs font-medium text-white shadow-[0_0_24px_color-mix(in_oklch,var(--magenta)_24%,transparent)]",
          )}
          aria-label="Owner access"
        >
          Y
        </button>
      </div>
    </header>
  )
}
