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
import { RuntimeStatusBanner } from "@/components/runtime-status-banner"
import { cn } from "@/lib/utils"

let idCounter = 0
const uid = () => `m${++idCounter}-${Date.now()}`

/** Demo / fixture greeting — not derived from overnight telemetry. */
const GREETING: Message = {
  id: "aion-greeting",
  role: "aion",
  content:
    "Good morning, Yaleel. This interface is connected to AION's reasoning runtime. Ask me what you want to understand, decide, research, or work on.",
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
  const [previousResponseId, setPreviousResponseId] = useState<string | null>(null)
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

      // Keep only deterministic local UI controls scripted. Anything that claims
      // external state, research, metrics, messages, repairs, or deployments must
      // come from the real runtime instead of the fixture router.
      const isLocalUiControl =
        turn.effect === "open-boardroom" ||
        String(turn.effect) === "close-boardroom" ||
        turn.effect === "open-terminal" ||
        turn.effect === "close-terminal"

      if (isLocalUiControl) {
        const q = trimmed.toLowerCase()
        const ventureMatch = ["YaliTek", "Elaria", "Cerebral Synergy", "AION"].find((v) =>
          q.includes(v.toLowerCase()),
        )
        if (ventureMatch && (mode === "boardroom" || turn.effect === "open-boardroom")) {
          setFocus({
            venture: ventureMatch,
            reasoning: `You asked me to concentrate on ${ventureMatch}.`,
          })
        } else if (turn.effect === "open-boardroom") {
          setFocus(null)
        }

        if (turn.effect === "open-boardroom") {
          setMode("boardroom")
        } else if (String(turn.effect) === "close-boardroom") {
          setMode("conversation")
        } else if (turn.effect === "open-terminal") {
          setTerminalOpen(true)
        } else if (turn.effect === "close-terminal") {
          setTerminalOpen(false)
        }
        if (turn.context) setContext(turn.context)

        pushMessage({
          id: uid(),
          role: "aion",
          content: turn.reply,
          serif: turn.serif,
        })
        setWorking("complete")
        setTimeout(() => setWorking("idle"), 500)
        busyRef.current = false
        return
      }

      try {
        const res = await fetch("/api/aion/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: trimmed,
            history: previousResponseId
              ? undefined
              : messages
                  .filter((m) => m.role === "user" || m.role === "aion")
                  .map((m) => ({ role: m.role === "aion" ? "assistant" : "user", content: m.content })),
            previousResponseId: previousResponseId ?? undefined,
          }),
        })

        const data = (await res.json()) as {
          reply?: string
          responseId?: string | null
          error?: string
          code?: string
        }

        if (!res.ok || !data.reply) {
          throw new Error(data.error || `AION runtime request failed (${res.status})`)
        }

        if (data.responseId) setPreviousResponseId(data.responseId)
        pushMessage({ id: uid(), role: "aion", content: data.reply })
      } catch (error) {
        const detail = error instanceof Error ? error.message : "Unknown runtime error"
        pushMessage({
          id: uid(),
          role: "aion",
          content: `I couldn't complete that through the live AION runtime. ${detail}`,
        })
      } finally {
        setWorking("complete")
        setTimeout(() => setWorking("idle"), 500)
        busyRef.current = false
      }
    },
    [messages, mode, previousResponseId, pushMessage],
  )

  const handleNewConversation = useCallback(() => {
    setMessages([GREETING])
    setPreviousResponseId(null)
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
      <RuntimeStatusBanner />
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
          <div
            className={cn(
              "flex min-w-0 flex-1 flex-col transition-all duration-500 ease-out",
              terminalOpen ? "lg:max-w-[54%]" : "max-w-full",
            )}
          >
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
