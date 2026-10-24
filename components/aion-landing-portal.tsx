"use client"

import {
  ArrowRight,
  BrainCircuit,
  Database,
  Link2,
  LockKeyhole,
  Mic,
  Radio,
  Settings2,
  Sparkles,
  TerminalSquare,
} from "lucide-react"
import type { Message, PresenceState } from "@/lib/aion/types"
import { Conversation } from "@/components/conversation/conversation"
import { CommandComposer } from "@/components/command-composer"
import { cn } from "@/lib/utils"

const features = [
  { icon: Radio, title: "Local-first", text: "Runs on your machine" },
  { icon: BrainCircuit, title: "Memory", text: "Durable context" },
  { icon: Sparkles, title: "Execution", text: "Controlled tools" },
]

export function AionLandingPortal({
  messages,
  working,
  presence,
  listening,
  voiceAvailable,
  disabled,
  compact = false,
  ownerAuthenticated,
  onSubmit,
  onVoiceToggle,
  onOpenConnections,
  onOpenBoardroom,
  onOpenTerminal,
}: {
  messages: Message[]
  working: PresenceState
  presence: PresenceState
  listening: boolean
  voiceAvailable: boolean
  disabled: boolean
  compact?: boolean
  ownerAuthenticated: boolean
  onSubmit: (text: string) => void
  onVoiceToggle: () => void
  onOpenConnections: () => void
  onOpenBoardroom: () => void
  onOpenTerminal?: () => void
}) {
  const focusComposer = () => document.getElementById("aion-message")?.focus()
  const openTerminal = () => {
    if (onOpenTerminal) {
      onOpenTerminal()
      return
    }
    onSubmit("Open it in the terminal.")
  }

  return (
    <main className="relative min-h-0 flex-1 overflow-y-auto overscroll-contain px-3 pb-5 sm:px-5 lg:px-6">
      <div className="pointer-events-none absolute inset-0 aion-grid opacity-25" aria-hidden />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_22%_32%,rgba(31,111,255,.16),transparent_28%),radial-gradient(circle_at_58%_18%,rgba(107,46,255,.10),transparent_30%),radial-gradient(circle_at_86%_60%,rgba(0,201,255,.08),transparent_24%)]" aria-hidden />

      <div
        className={cn(
          "relative z-10 mx-auto grid min-h-full max-w-[1540px] grid-cols-1 gap-3 py-3 lg:py-4",
          compact ? "lg:grid-cols-1" : "lg:grid-cols-[0.78fr_1.5fr_0.82fr]",
        )}
      >
        <section
          id="aion-presence"
          className={cn(
            "order-2 relative overflow-hidden rounded-[1.6rem] border border-cyan/20 bg-[#06101f]/82 p-4 shadow-[inset_0_1px_0_rgba(93,223,255,.08),0_28px_90px_-50px_rgba(0,154,255,.55)] sm:p-5 lg:order-1 lg:min-h-[calc(100dvh-8.4rem)]",
            compact && "lg:hidden",
          )}
        >
          <div className="pointer-events-none absolute left-1/2 top-[34%] h-[64%] w-[115%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan/12" aria-hidden />
          <div className="pointer-events-none absolute left-1/2 top-[34%] h-[52%] w-[94%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-violet/15" aria-hidden />

          <div className="relative flex items-center justify-between gap-3">
            <div>
              <p className="text-[0.62rem] uppercase tracking-[0.22em] text-muted-foreground">AION OS</p>
              <h2 className="mt-1 font-serif text-2xl font-light text-foreground">Presence</h2>
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="h-2 w-2 rounded-full bg-positive shadow-[0_0_10px_var(--positive)]" />
              {presence === "idle" || presence === "complete" ? "Ready" : "Active"}
            </div>
          </div>

          <div className="relative mx-auto mt-3 flex w-full max-w-[330px] items-start justify-center">
            <div className="absolute inset-x-5 top-8 h-52 rounded-full bg-blue-600/20 blur-3xl" aria-hidden />
            <img
              src="/aion-portrait"
              alt="Aion"
              className="relative z-10 max-h-[42dvh] w-auto rounded-[44%_44%_38%_38%/28%_28%_18%_18%] object-contain drop-shadow-[0_0_38px_rgba(20,113,255,.38)]"
            />
          </div>

          <div className="relative z-10 mt-3 text-center">
            <p className="font-serif text-lg font-light text-foreground">Your personal AI operating environment.</p>
            <p className="mx-auto mt-2 max-w-sm text-xs leading-relaxed text-muted-foreground">Conversation, memory, voice, projects, and controlled execution live in one local-first interface.</p>
            <div className="mt-4 grid grid-cols-3 border-t border-cyan/10 pt-4">
              {features.map(({ icon: Icon, title, text }) => (
                <div key={title} className="px-1 text-center sm:px-2">
                  <span className="mx-auto flex h-8 w-8 items-center justify-center rounded-full border border-cyan/20 bg-cyan/5 text-cyan"><Icon className="h-4 w-4" /></span>
                  <p className="mt-2 text-[0.58rem] font-medium uppercase tracking-[0.1em] text-foreground/85 sm:text-[0.64rem]">{title}</p>
                  <p className="mt-1 text-[0.58rem] text-muted-foreground sm:text-[0.62rem]">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="conversation" className="order-1 flex min-h-[620px] min-w-0 flex-col gap-3 lg:order-2 lg:min-h-[calc(100dvh-8.4rem)]">
          <div className={cn("px-2 text-center", compact ? "py-2" : "py-3 sm:py-4")}>
            <div className="flex flex-col items-center justify-center gap-1">
              <h1 className={cn("font-serif font-light tracking-[0.14em] text-foreground drop-shadow-[0_0_24px_rgba(129,183,255,.22)]", compact ? "text-3xl sm:text-4xl" : "text-4xl sm:text-5xl")}>AION OS</h1>
              <p className="max-w-xl text-sm text-foreground/72 sm:text-base">Speak, type, inspect, execute, and move between your workspaces without leaving AION.</p>
            </div>
            {!compact && (
              <div className="mt-3 flex flex-wrap items-center justify-center gap-2.5">
                <button type="button" onClick={focusComposer} className="inline-flex min-w-40 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-500 px-4 py-2.5 text-sm font-medium text-white shadow-[0_0_28px_rgba(0,173,255,.22)] transition-transform hover:-translate-y-0.5">Command AION <ArrowRight className="h-4 w-4" /></button>
                <button type="button" onClick={openTerminal} className="inline-flex min-w-40 items-center justify-center gap-2 rounded-xl border border-cyan/25 bg-[#071426]/80 px-4 py-2.5 text-sm text-foreground transition-colors hover:bg-cyan/7">Open Terminal <TerminalSquare className="h-4 w-4 text-cyan/75" /></button>
              </div>
            )}
          </div>

          <div className="flex min-h-[500px] min-w-0 flex-1 flex-col overflow-hidden rounded-[1.4rem] border border-cyan/25 bg-[#071426]/82 shadow-[inset_0_1px_0_rgba(93,223,255,.07),0_30px_80px_-45px_rgba(0,154,255,.4)] backdrop-blur-xl">
            <div className="flex items-center justify-between gap-3 border-b border-cyan/12 px-4 py-3 sm:px-5 sm:py-3.5">
              <div className="min-w-0">
                <p className="truncate text-sm font-medium text-foreground sm:text-base">AION Command Channel</p>
                <p className="mt-0.5 text-[0.68rem] text-muted-foreground sm:text-xs">Local reasoning · durable memory · controlled execution</p>
              </div>
              <div className="flex shrink-0 items-center gap-2 text-[0.68rem] text-muted-foreground sm:text-xs"><span className="h-2 w-2 rounded-full bg-positive shadow-[0_0_10px_var(--positive)]" />{listening ? "Listening" : presence === "idle" || presence === "complete" ? "Ready" : "Working"}</div>
            </div>
            <div className="min-h-[280px] flex-1 overflow-y-auto py-3 sm:py-4">
              <Conversation messages={messages} working={working} onCommand={onSubmit} />
            </div>
            <div className="border-t border-cyan/10 p-3 sm:p-3.5">
              <CommandComposer onSubmit={onSubmit} onVoiceToggle={onVoiceToggle} listening={listening} voiceAvailable={voiceAvailable} disabled={disabled} onOpenConnections={onOpenConnections} />
              <p className="mt-2 text-center text-[0.56rem] uppercase tracking-[0.12em] text-muted-foreground/60 sm:text-[0.62rem] sm:tracking-[0.16em]">Local-first · owner-controlled · memory-aware</p>
            </div>
          </div>
        </section>

        <aside
          id="system-access"
          className={cn(
            "order-3 flex flex-col gap-3 lg:min-h-[calc(100dvh-8.4rem)]",
            compact && "lg:hidden",
          )}
        >
          <section className="relative overflow-hidden rounded-[1.4rem] border border-cyan/22 bg-[#071426]/82 p-5 shadow-[inset_0_1px_0_rgba(93,223,255,.06)]">
            <div className="pointer-events-none absolute -right-16 -top-16 h-52 w-52 rounded-full border border-violet/18 shadow-[0_0_45px_rgba(91,72,255,.12)]" aria-hidden />
            <p className="text-[0.62rem] uppercase tracking-[0.22em] text-muted-foreground">Owner space</p>
            <div className="mt-2 flex items-center gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-full border border-cyan/20 bg-cyan/5 text-cyan"><LockKeyhole className="h-5 w-5" /></span><div><h2 className="font-serif text-2xl font-light text-foreground">Boardroom</h2><p className="text-xs text-muted-foreground">Private strategy, memory, and sovereign oversight.</p></div></div>
            <button type="button" onClick={onOpenBoardroom} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-cyan/25 bg-background/35 px-4 py-2.5 text-sm text-foreground transition-colors hover:bg-cyan/7">{ownerAuthenticated ? "Enter Boardroom" : "Authenticate & open"}<LockKeyhole className="h-4 w-4" /></button>
          </section>

          <section className="flex-1 rounded-[1.4rem] border border-cyan/22 bg-[#071426]/82 p-5 shadow-[inset_0_1px_0_rgba(93,223,255,.06)]">
            <h2 className="font-serif text-2xl font-light text-foreground">System Access</h2>
            <p className="mt-1 text-sm text-muted-foreground">Primary AION OS controls stay close to the conversation.</p>
            <div className="mt-4 space-y-2.5">
              <button type="button" onClick={voiceAvailable ? onVoiceToggle : undefined} disabled={!voiceAvailable || disabled} className={cn("group flex w-full items-center gap-3 rounded-xl border p-3.5 text-left transition-colors", voiceAvailable ? "border-cyan/14 bg-background/24 hover:border-cyan/30 hover:bg-cyan/5" : "cursor-not-allowed border-cyan/8 bg-background/15 opacity-55")}>
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600/12 text-cyan"><Mic className="h-5 w-5" /></span>
                <span className="min-w-0 flex-1"><span className="flex items-center gap-2"><span className="block text-sm font-medium text-foreground">Voice</span><span className={cn("text-[0.58rem] uppercase tracking-[0.12em]", voiceAvailable ? "text-cyan" : "text-muted-foreground/70")}>{voiceAvailable ? "Ready" : "Unavailable"}</span></span><span className="mt-0.5 block text-xs text-muted-foreground">EMEET → Whisper → AION → Piper</span></span>
                <ArrowRight className="h-4 w-4 text-cyan/55" />
              </button>

              <button type="button" onClick={openTerminal} className="group flex w-full items-center gap-3 rounded-xl border border-cyan/14 bg-background/24 p-3.5 text-left transition-colors hover:border-cyan/30 hover:bg-cyan/5">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600/12 text-cyan"><TerminalSquare className="h-5 w-5" /></span>
                <span className="min-w-0 flex-1"><span className="flex items-center gap-2"><span className="block text-sm font-medium text-foreground">Terminal</span><span className="text-[0.58rem] uppercase tracking-[0.12em] text-cyan">Controlled</span></span><span className="mt-0.5 block text-xs text-muted-foreground">Typed local execution with owner gates.</span></span>
                <ArrowRight className="h-4 w-4 text-cyan/55" />
              </button>

              <div className="flex w-full items-center gap-3 rounded-xl border border-cyan/14 bg-background/24 p-3.5 text-left">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600/12 text-cyan"><Database className="h-5 w-5" /></span>
                <span className="min-w-0 flex-1"><span className="flex items-center gap-2"><span className="block text-sm font-medium text-foreground">Memory</span><span className="text-[0.58rem] uppercase tracking-[0.12em] text-cyan">Durable</span></span><span className="mt-0.5 block text-xs text-muted-foreground">Conversation context persists locally.</span></span>
              </div>

              <button type="button" onClick={onOpenConnections} className="group flex w-full items-center gap-3 rounded-xl border border-cyan/14 bg-background/24 p-3.5 text-left transition-colors hover:border-cyan/30 hover:bg-cyan/5">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600/12 text-cyan"><Settings2 className="h-5 w-5" /></span>
                <span className="min-w-0 flex-1"><span className="block text-sm font-medium text-foreground">Connections</span><span className="mt-0.5 block text-xs text-muted-foreground">Manage optional external channels and services.</span></span>
                <ArrowRight className="h-4 w-4 text-cyan/55" />
              </button>

              <button type="button" onClick={focusComposer} className="group flex w-full items-center gap-3 rounded-xl border border-cyan/14 bg-background/24 p-3.5 text-left transition-colors hover:border-cyan/30 hover:bg-cyan/5">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600/12 text-cyan"><Link2 className="h-5 w-5" /></span>
                <span className="min-w-0 flex-1"><span className="block text-sm font-medium text-foreground">Links & research</span><span className="mt-0.5 block text-xs text-muted-foreground">Drop a link directly into the command channel.</span></span>
                <ArrowRight className="h-4 w-4 text-cyan/55" />
              </button>
            </div>
          </section>
        </aside>
      </div>
    </main>
  )
}
