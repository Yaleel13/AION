"use client"

import { Bell, Link2, LockKeyhole, MessageCircleMore, Settings2 } from "lucide-react"
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
  onHome,
  onNewConversation,
  onNotifications,
  onSettings,
  onAccount,
}: {
  state: PresenceState
  mode: InterfaceMode
  hasNotifications?: boolean
  onHome?: () => void
  onNewConversation: () => void
  onNotifications?: () => void
  onSettings?: () => void
  onAccount?: () => void
}) {
  const busy = state !== "idle" && state !== "complete"

  const jump = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" })
  }

  const goHome = () => {
    if (mode === "boardroom") onHome?.()
    else jump("conversation")
  }

  return (
    <header className="relative z-30 flex min-h-16 items-center justify-between gap-3 border-b border-cyan/12 bg-[#040b16]/92 px-4 py-2.5 backdrop-blur-xl sm:px-6 lg:px-8">
      <button type="button" onClick={goHome} className="group flex min-w-0 items-center gap-3" aria-label="AION home">
        <span className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-cyan/30 bg-cyan/5 shadow-[0_0_26px_rgba(0,190,255,.08)]">
          <span className="absolute h-5 w-5 rotate-45 border border-cyan/75" aria-hidden />
          <span className="absolute h-5 w-5 -rotate-45 border border-violet/55" aria-hidden />
          <span className="h-1.5 w-1.5 rounded-full bg-cyan shadow-[0_0_15px_var(--cyan)]" aria-hidden />
        </span>
        <span className="font-serif text-xl font-light tracking-[0.28em] text-foreground sm:text-2xl">AION</span>
      </button>

      {mode === "conversation" ? (
        <nav className="hidden items-center gap-1 lg:flex" aria-label="Primary">
          <button type="button" onClick={() => jump("conversation")} className="rounded-lg px-3 py-2 text-xs text-cyan transition-colors hover:bg-cyan/6">Home</button>
          <button type="button" onClick={() => jump("about-aion")} className="rounded-lg px-3 py-2 text-xs text-muted-foreground transition-colors hover:bg-cyan/6 hover:text-foreground">About Aion</button>
          <button type="button" onClick={() => jump("how-it-works")} className="rounded-lg px-3 py-2 text-xs text-muted-foreground transition-colors hover:bg-cyan/6 hover:text-foreground">How It Works</button>
          <button type="button" onClick={() => jump("connect")} className="rounded-lg px-3 py-2 text-xs text-muted-foreground transition-colors hover:bg-cyan/6 hover:text-foreground">Connect</button>
        </nav>
      ) : (
        <div className="hidden items-center gap-2 rounded-full border border-cyan/15 bg-surface/40 px-3 py-1.5 sm:flex">
          <StatusDot tone={busy ? "caution" : "violet"} pulse={busy} />
          <span className="text-xs text-muted-foreground">Boardroom · {stateLabel[state]}</span>
        </div>
      )}

      <div className="flex shrink-0 items-center gap-1.5">
        <button type="button" onClick={onNotifications} className="relative hidden h-9 w-9 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-cyan/7 hover:text-cyan sm:flex" aria-label="What needs my attention">
          <Bell className="h-4 w-4" />
          {hasNotifications && <span className="absolute right-2 top-2 h-1.5 w-1.5 rounded-full bg-magenta" />}
        </button>
        <button type="button" onClick={onSettings} className="hidden h-9 w-9 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-cyan/7 hover:text-cyan sm:flex" aria-label="Connections and settings"><Settings2 className="h-4 w-4" /></button>
        <button
          type="button"
          onClick={onAccount}
          disabled={mode === "boardroom"}
          className={cn(
            "inline-flex h-9 items-center justify-center gap-2 rounded-xl border border-cyan/25 bg-background/30 px-3 text-xs text-foreground transition-colors",
            mode === "boardroom" ? "cursor-default border-cyan/35 bg-cyan/8 text-cyan" : "hover:bg-cyan/7",
          )}
          aria-label={mode === "boardroom" ? "Boardroom unlocked" : "Owner access"}
          aria-current={mode === "boardroom" ? "page" : undefined}
        >
          <LockKeyhole className="h-3.5 w-3.5 text-cyan/75" />
          <span className="hidden sm:inline">{mode === "boardroom" ? "Boardroom" : "Owner"}</span>
        </button>
        <button type="button" onClick={onNewConversation} className="inline-flex h-9 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-500 px-3 text-xs font-medium text-white shadow-[0_0_22px_rgba(0,170,255,.15)] transition-transform hover:-translate-y-px"><MessageCircleMore className="h-3.5 w-3.5" /><span className="hidden sm:inline">Begin Conversation</span><span className="sm:hidden">Chat</span></button>
        <button type="button" onClick={onSettings} className="flex h-9 w-9 items-center justify-center rounded-xl text-muted-foreground transition-colors hover:bg-cyan/7 hover:text-cyan lg:hidden" aria-label="Connect"><Link2 className="h-4 w-4" /></button>
      </div>
    </header>
  )
}
