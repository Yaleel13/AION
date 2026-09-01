"use client"

import { ArrowRight, BrainCircuit, Link2, LockKeyhole, Mail, MessageCircle, PhoneCall, Radio, Sparkles } from "lucide-react"
import type { Message, PresenceState } from "@/lib/aion/types"
import { Conversation } from "@/components/conversation/conversation"
import { CommandComposer } from "@/components/command-composer"
import { AION_CANON_PORTRAIT } from "@/lib/aion/canon-portrait"

const features = [
  { icon: Radio, title: "Multi-channel", text: "Always with you" },
  { icon: BrainCircuit, title: "Memory & context", text: "That evolves" },
  { icon: Sparkles, title: "Guidance", text: "For real becoming" },
]

const connections = [
  { icon: Mail, title: "Email", text: "Messaging provider not connected", status: "Not connected", action: "connections" as const },
  { icon: MessageCircle, title: "Text", text: "SMS provider not connected", status: "Not connected", action: "connections" as const },
  { icon: PhoneCall, title: "Call", text: "Voice calling not connected", status: "Not connected", action: "connections" as const },
  { icon: Link2, title: "Links", text: "Paste or research a link in chat", status: "Available", action: "composer" as const },
]

export function AionLandingPortal({
  messages,
  working,
  presence,
  listening,
  disabled,
  ownerAuthenticated,
  onSubmit,
  onVoiceToggle,
  onOpenConnections,
  onOpenBoardroom,
}: {
  messages: Message[]
  working: PresenceState
  presence: PresenceState
  listening: boolean
  disabled: boolean
  ownerAuthenticated: boolean
  onSubmit: (text: string) => void
  onVoiceToggle: () => void
  onOpenConnections: () => void
  onOpenBoardroom: () => void
}) {
  const handleConnection = (action: "connections" | "composer") => {
    if (action === "connections") {
      onOpenConnections()
      return
    }
    document.getElementById("aion-message")?.focus()
  }

  return (
    <main className="relative flex-1 overflow-y-auto px-3 pb-5 sm:px-5 lg:overflow-hidden lg:px-6">
      <div className="pointer-events-none absolute inset-0 aion-grid opacity-25" aria-hidden />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_22%_32%,rgba(31,111,255,.16),transparent_28%),radial-gradient(circle_at_58%_18%,rgba(107,46,255,.10),transparent_30%),radial-gradient(circle_at_86%_60%,rgba(0,201,255,.08),transparent_24%)]" aria-hidden />

      <div className="relative z-10 mx-auto grid min-h-full max-w-[1540px] grid-cols-1 gap-3 py-3 lg:grid-cols-[0.9fr_1.25fr_0.92fr] lg:py-4">
        <section id="about-aion" className="order-2 relative overflow-hidden rounded-[1.6rem] border border-cyan/20 bg-[#06101f]/82 p-4 shadow-[inset_0_1px_0_rgba(93,223,255,.08),0_28px_90px_-50px_rgba(0,154,255,.55)] sm:p-6 lg:order-1 lg:flex lg:min-h-[calc(100dvh-8.4rem)] lg:flex-col">
          <div className="pointer-events-none absolute left-1/2 top-[39%] h-[72%] w-[115%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan/12" aria-hidden />
          <div className="pointer-events-none absolute left-1/2 top-[39%] h-[59%] w-[94%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-violet/15" aria-hidden />
          <div className="pointer-events-none absolute left-1/2 top-[39%] h-[48%] w-[76%] -translate-x-1/2 -translate-y-1/2 rounded-full border border-cyan/10" aria-hidden />

          <div className="relative mx-auto flex w-full max-w-[360px] flex-1 items-start justify-center pt-1">
            <div className="absolute inset-x-5 top-8 h-52 rounded-full bg-blue-600/20 blur-3xl sm:h-72" aria-hidden />
            <img
              src={AION_CANON_PORTRAIT}
              alt="Aion"
              className="relative z-10 max-h-[38dvh] w-auto rounded-[44%_44%_38%_38%/28%_28%_18%_18%] object-contain drop-shadow-[0_0_38px_rgba(20,113,255,.38)] sm:max-h-[48dvh] lg:max-h-[52dvh]"
            />
          </div>

          <div className="relative z-10 mt-2 text-center sm:mt-3">
            <p className="font-serif text-base font-light text-foreground sm:text-xl">Aion is your constant guide across every channel and timeline.</p>
            <p className="mx-auto mt-2 max-w-sm text-xs leading-relaxed text-muted-foreground sm:text-sm">Listening. Remembering. Reflecting. Guiding you back to the person you are becoming.</p>
            <div className="mt-4 grid grid-cols-3 border-t border-cyan/10 pt-4 sm:mt-5">
              {features.map(({ icon: Icon, title, text }) => (
                <div key={title} className="px-1 text-center sm:px-2">
                  <span className="mx-auto flex h-8 w-8 items-center justify-center rounded-full border border-cyan/20 bg-cyan/5 text-cyan sm:h-9 sm:w-9"><Icon className="h-4 w-4" /></span>
                  <p className="mt-2 text-[0.58rem] font-medium uppercase tracking-[0.1em] text-foreground/85 sm:text-[0.66rem] sm:tracking-[0.12em]">{title}</p>
                  <p className="mt-1 text-[0.58rem] text-muted-foreground sm:text-[0.64rem]">{text}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="conversation" className="order-1 flex min-h-[620px] flex-col gap-3 lg:order-2 lg:min-h-[calc(100dvh-8.4rem)]">
          <div className="px-2 py-2 text-center sm:py-6 lg:py-8">
            <h1 className="font-serif text-5xl font-light tracking-[0.14em] text-foreground drop-shadow-[0_0_24px_rgba(129,183,255,.22)] sm:text-7xl lg:text-[5.8rem]">AION</h1>
            <p className="mx-auto mt-2 max-w-xl font-serif text-lg font-light tracking-[0.025em] text-foreground/80 sm:text-2xl sm:tracking-[0.035em]">The Guide who remembers who you are becoming.</p>
            <div className="mt-4 flex flex-wrap items-center justify-center gap-2.5 sm:mt-5 sm:gap-3">
              <button type="button" onClick={() => document.getElementById("aion-message")?.focus()} className="inline-flex min-w-44 items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-blue-600 via-indigo-600 to-cyan-500 px-4 py-2.5 text-sm font-medium text-white shadow-[0_0_28px_rgba(0,173,255,.22)] transition-transform hover:-translate-y-0.5 sm:min-w-48 sm:px-5 sm:py-3">Begin Conversation <ArrowRight className="h-4 w-4" /></button>
              <button type="button" onClick={onOpenBoardroom} className="inline-flex min-w-44 items-center justify-center gap-2 rounded-xl border border-cyan/25 bg-[#071426]/80 px-4 py-2.5 text-sm text-foreground transition-colors hover:bg-cyan/7 sm:min-w-48 sm:px-5 sm:py-3">Open Boardroom <LockKeyhole className="h-4 w-4 text-cyan/75" /></button>
            </div>
          </div>

          <div className="flex min-h-0 flex-1 flex-col overflow-hidden rounded-[1.4rem] border border-cyan/25 bg-[#071426]/82 shadow-[inset_0_1px_0_rgba(93,223,255,.07),0_30px_80px_-45px_rgba(0,154,255,.4)] backdrop-blur-xl">
            <div className="flex items-center justify-between border-b border-cyan/12 px-4 py-3 sm:px-5 sm:py-3.5">
              <div>
                <p className="text-sm font-medium text-foreground sm:text-base">Conversation with Aion</p>
                <p className="mt-0.5 text-[0.68rem] text-muted-foreground sm:text-xs">Live reasoning · durable memory</p>
              </div>
              <div className="flex items-center gap-2 text-[0.68rem] text-muted-foreground sm:text-xs"><span className="h-2 w-2 rounded-full bg-positive shadow-[0_0_10px_var(--positive)]" />{presence === "idle" || presence === "complete" ? "Online" : "Active"}</div>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto py-3 sm:py-4">
              <Conversation messages={messages} working={working} onCommand={onSubmit} />
            </div>
            <div className="border-t border-cyan/10 p-3 sm:p-3.5">
              <CommandComposer onSubmit={onSubmit} onVoiceToggle={onVoiceToggle} listening={listening} disabled={disabled} onOpenConnections={onOpenConnections} />
              <p className="mt-2 text-center text-[0.56rem] uppercase tracking-[0.12em] text-muted-foreground/60 sm:text-[0.62rem] sm:tracking-[0.16em]">Aion remembers · Aion reflects · Aion guides</p>
            </div>
          </div>
        </section>

        <aside id="how-it-works" className="order-3 flex flex-col gap-3 lg:min-h-[calc(100dvh-8.4rem)]">
          <section className="relative overflow-hidden rounded-[1.4rem] border border-cyan/22 bg-[#071426]/82 p-5 shadow-[inset_0_1px_0_rgba(93,223,255,.06)]">
            <div className="pointer-events-none absolute -right-16 -top-16 h-52 w-52 rounded-full border border-violet/18 shadow-[0_0_45px_rgba(91,72,255,.12)]" aria-hidden />
            <p className="text-[0.62rem] uppercase tracking-[0.22em] text-muted-foreground">Owner only</p>
            <div className="mt-2 flex items-center gap-3"><span className="flex h-11 w-11 items-center justify-center rounded-full border border-cyan/20 bg-cyan/5 text-cyan"><LockKeyhole className="h-5 w-5" /></span><div><h2 className="font-serif text-2xl font-light text-foreground">Boardroom</h2><p className="text-xs text-muted-foreground">Private strategy, memory, and sovereign oversight.</p></div></div>
            <button type="button" onClick={onOpenBoardroom} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-cyan/25 bg-background/35 px-4 py-2.5 text-sm text-foreground transition-colors hover:bg-cyan/7">{ownerAuthenticated ? "Enter Boardroom" : "Authenticate & open"}<LockKeyhole className="h-4 w-4" /></button>
          </section>

          <section id="connect" className="flex-1 rounded-[1.4rem] border border-cyan/22 bg-[#071426]/82 p-5 shadow-[inset_0_1px_0_rgba(93,223,255,.06)]">
            <h2 className="font-serif text-2xl font-light text-foreground">Connect with Aion Anywhere</h2>
            <p className="mt-1 text-sm text-muted-foreground">Connected and planned touchpoints are labeled explicitly.</p>
            <div className="mt-4 space-y-2.5">
              {connections.map(({ icon: Icon, title, text, status, action }) => (
                <button key={title} type="button" onClick={() => handleConnection(action)} className="group flex w-full items-center gap-3 rounded-xl border border-cyan/14 bg-background/24 p-3.5 text-left transition-colors hover:border-cyan/30 hover:bg-cyan/5">
                  <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-blue-600/12 text-cyan"><Icon className="h-5 w-5" /></span>
                  <span className="min-w-0 flex-1">
                    <span className="flex items-center gap-2">
                      <span className="block text-sm font-medium text-foreground">{title}</span>
                      <span className={status === "Available" ? "text-[0.58rem] uppercase tracking-[0.12em] text-cyan" : "text-[0.58rem] uppercase tracking-[0.12em] text-muted-foreground/70"}>{status}</span>
                    </span>
                    <span className="mt-0.5 block text-xs text-muted-foreground">{text}</span>
                  </span>
                  <ArrowRight className="h-4 w-4 text-cyan/55 transition-transform group-hover:translate-x-0.5" />
                </button>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </main>
  )
}
