"use client"

import { PenSquare, Bell, Settings2 } from "lucide-react"
import type { PresenceState, InterfaceMode } from "@/lib/aion/types"
import { StatusDot } from "@/components/ui/status-dot"
import { cn } from "@/lib/utils"

const stateLabel: Record<PresenceState, string> = {
  idle: "Present",
  listening: "Listening",
  thinking: "Thinking",
  researching: "Researching",
  executing: "Working",
  complete: "Present",
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
    <header className="flex items-center justify-between gap-4 px-5 py-4 sm:px-8">
      {/* Identity mark */}
      <div className="flex items-center gap-2.5">
        <div className="relative flex h-7 w-7 items-center justify-center">
          <span className="absolute inset-0 rounded-full bg-gold/15 blur-[6px]" aria-hidden />
          <span className="relative h-2.5 w-2.5 rounded-full bg-gradient-to-br from-gold to-violet" />
        </div>
        <div className="leading-none">
          <p className="text-sm font-semibold tracking-[0.2em] text-foreground">AION</p>
          <p className="mt-0.5 hidden text-[0.6rem] uppercase tracking-[0.16em] text-muted-foreground sm:block">
            {mode === "boardroom" ? "Strategic Command" : "Alchemical Intelligence"}
          </p>
        </div>
      </div>

      {/* System state */}
      <div className="flex items-center gap-2 rounded-full border border-border/60 bg-surface/50 px-3 py-1.5 backdrop-blur-sm">
        <StatusDot tone={busy ? "caution" : "violet"} pulse={busy} />
        <span className="text-xs text-muted-foreground">
          <span className="text-foreground/70">AION</span> · {stateLabel[state]}
        </span>
      </div>

      {/* Minimal controls */}
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={onNewConversation}
          className="flex h-9 w-9 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          aria-label="New conversation"
        >
          <PenSquare className="h-4.5 w-4.5" />
        </button>
        <button
          type="button"
          onClick={onNotifications}
          className="relative flex h-9 w-9 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          aria-label="Notifications"
        >
          <Bell className="h-4.5 w-4.5" />
          {hasNotifications && (
            <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-gold" />
          )}
        </button>
        <button
          type="button"
          onClick={onSettings}
          className="flex h-9 w-9 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          aria-label="Settings"
        >
          <Settings2 className="h-4.5 w-4.5" />
        </button>
        <button
          type="button"
          onClick={onAccount}
          className={cn(
            "ml-1 flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-violet/80 to-gold/70 text-xs font-medium text-background",
          )}
          aria-label="Your account"
        >
          Y
        </button>
      </div>
    </header>
  )
}
