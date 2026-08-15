"use client"

import { useCallback, useRef, useState } from "react"
import type { Message, PresenceState, InterfaceMode } from "@/lib/aion/types"
import { routeCommand } from "@/lib/aion/mock"
import { TopBar } from "@/components/top-bar"
import { Conversation } from "@/components/conversation/conversation"
import { CommandComposer } from "@/components/command-composer"
import { AionPresence } from "@/components/aion-presence"
import { TerminalWorkspace } from "@/components/terminal-workspace"
import { Boardroom } from "@/components/boardroom"
import { ConnectionSheet } from "@/components/connection-sheet"
import { ProjectContext } from "@/components/project-context"
import { cn } from "@/lib/utils"

let idCounter = 0
const uid = () => `m${++idCounter}-${Date.now()}`

const GREETING: Message = {
  id: "aion-greeting",
  role: "aion",
  content:
    "Good morning, Yaleel. I kept watch overnight. Three things moved while you were away — none of them a fire. Where would you like to begin?",
  serif: true,
}

const busyStates: PresenceState[] = ["thinking", "researching", "executing"]

export function AionShell() {
  const [messages, setMessages] = useState<Message[]>([GREETING])
  const [working, setWorking] = useState<PresenceState>("idle")
  const [mode, setMode] = useState<InterfaceMode>("conversation")
  const [context, setContext] = useState<string | null>(null)
  const [focus, setFocus] = useState<{ venture: string; reasoning: string } | null>(null)
  const [terminalOpen, setTerminalOpen] = useState(false)
  const [connectionOpen, setConnectionOpen] = useState(false)
  const [listening, setListening] = useState(false)
  const busyRef = useRef(false)

  const presence: PresenceState = listening && working === "idle" ? "listening" : working

  const pushMessage = useCallback((m: Message) => setMessages((prev) => [...prev, m]), [])

  const handleSend = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || busyRef.current) return
      busyRef.current = true
      setListening(false)

      pushMessage({ id: uid(), role: "user", content: trimmed })

      const turn = routeCommand(trimmed)
      setWorking(turn.working)

      // Boardroom focus detection — highlight a venture when named.
      const q = trimmed.toLowerCase()
      const ventureMatch = ["YaliTek", "Elaria", "Cerebral Synergy", "AION"].find((v) =>
        q.includes(v.toLowerCase()),
      )
      if (ventureMatch && (mode === "boardroom" || turn.effect === "open-boardroom")) {
        setFocus({
          venture: ventureMatch,
          reasoning: `You asked me to concentrate on ${ventureMatch}. I've surfaced its open decisions, live signals and the single next action that moves it forward.`,
        })
      } else if (turn.effect === "open-boardroom") {
        setFocus(null)
      }

      // Side effects
      if (turn.effect === "open-boardroom") {
        setTimeout(() => setMode("boardroom"), 650)
      } else if (String(turn.effect) === "close-boardroom") {
        setMode("conversation")
      } else if (turn.effect === "open-terminal") {
        setTimeout(() => setTerminalOpen(true), 450)
      } else if (turn.effect === "close-terminal") {
        setTerminalOpen(false)
      }
      if (turn.context) setContext(turn.context)

      const isScripted = Boolean(turn.widgets || turn.effect || turn.serif)

      await new Promise((r) => setTimeout(r, 850))

      if (isScripted) {
        pushMessage({
          id: uid(),
          role: "aion",
          content: turn.reply,
          serif: turn.serif,
          widgets: turn.widgets,
        })
        setWorking("complete")
        setTimeout(() => setWorking("idle"), 500)
        busyRef.current = false
        return
      }

      // Free-form — reach the real AION reasoning core.
      try {
        const res = await fetch("/api/aion/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: trimmed,
            history: messages
              .filter((m) => m.role === "user" || m.role === "aion")
              .map((m) => ({ role: m.role === "aion" ? "assistant" : "user", content: m.content })),
          }),
        })
        const data = (await res.json()) as { reply?: string }
        pushMessage({ id: uid(), role: "aion", content: data.reply || turn.reply })
      } catch {
        pushMessage({ id: uid(), role: "aion", content: turn.reply })
      } finally {
        setWorking("complete")
        setTimeout(() => setWorking("idle"), 500)
        busyRef.current = false
      }
    },
    [messages, mode, pushMessage],
  )

  const handleNewConversation = useCallback(() => {
    setMessages([GREETING])
    setContext(null)
    setTerminalOpen(false)
    setMode("conversation")
    setWorking("idle")
  }, [])

  const handleConnect = useCallback(
    (title: string) => {
      setConnectionOpen(false)
      handleSend(`Connect ${title}.`)
    },
    [handleSend],
  )

  const isBusy = busyStates.includes(working)
  const showHero = mode === "conversation" && messages.length <= 1

  return (
    <div className="relative flex h-dvh flex-col overflow-hidden bg-background">
      <TopBar
        state={presence}
        mode={mode}
        hasNotifications
        onNewConversation={handleNewConversation}
        onNotifications={() => handleSend("What needs my attention today?")}
        onSettings={() => setConnectionOpen(true)}
        onAccount={() => handleSend("Open the Boardroom.")}
      />

      {mode === "boardroom" ? (
        <div className="flex-1 overflow-y-auto">
          <Boardroom
            presence={presence}
            working={working}
            focus={focus}
            listening={listening}
            onSubmit={handleSend}
            onVoiceToggle={() => setListening((v) => !v)}
            onExit={() => setMode("conversation")}
          />
        </div>
      ) : (
        <div className="relative flex flex-1 overflow-hidden">
          {/* Conversation column */}
          <div
            className={cn(
              "flex min-w-0 flex-1 flex-col transition-all duration-500 ease-out",
              terminalOpen ? "lg:max-w-[54%]" : "max-w-full",
            )}
          >
            {/* Presence core — the always-present signature element */}
            <div
              className={cn(
                "flex shrink-0 items-center justify-center transition-all duration-700",
                showHero ? "pt-6 pb-2" : "pt-4 pb-1",
              )}
            >
              <AionPresence state={presence} size={showHero ? 180 : 84} />
            </div>

            {context && (
              <div className="shrink-0 pb-1">
                <ProjectContext label={context} onDismiss={() => setContext(null)} />
              </div>
            )}

            <div className="flex-1 overflow-y-auto pb-2">
              <Conversation messages={messages} working={working} onCommand={handleSend} />
            </div>

            <div className="shrink-0 px-4 pb-6 pt-2">
              <div className="mx-auto w-full max-w-3xl">
                <CommandComposer
                  onSubmit={handleSend}
                  onVoiceToggle={() => setListening((v) => !v)}
                  listening={listening}
                  disabled={isBusy}
                  onOpenConnections={() => setConnectionOpen(true)}
                />
              </div>
            </div>
          </div>

          {/* Terminal split-view */}
          {terminalOpen && (
            <div className="hidden w-full p-3 lg:block lg:max-w-[46%]">
              <TerminalWorkspace onClose={() => setTerminalOpen(false)} />
            </div>
          )}
        </div>
      )}

      <ConnectionSheet open={connectionOpen} onClose={() => setConnectionOpen(false)} onConnect={handleConnect} />
    </div>
  )
}
