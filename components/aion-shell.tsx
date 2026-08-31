"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import type { Message, PresenceState, InterfaceMode } from "@/lib/aion/types"
import { routeCommand } from "@/lib/aion/mock"
import { TopBar } from "@/components/top-bar"
import { Conversation } from "@/components/conversation/conversation"
import { CommandComposer } from "@/components/command-composer"
import { AionPresence } from "@/components/aion-presence"
import { ConvergenceRail } from "@/components/convergence-rail"
import { TerminalWorkspace } from "@/components/terminal-workspace"
import { Boardroom } from "@/components/boardroom"
import { ConnectionSheet } from "@/components/connection-sheet"
import { ProjectContext } from "@/components/project-context"
import { RuntimeStatusBanner } from "@/components/runtime-status-banner"
import { OwnerAuthDialog } from "@/components/owner-auth-dialog"
import { cn } from "@/lib/utils"

let idCounter = 0
const uid = () => `m${++idCounter}-${Date.now()}`

const CONVERSATION_STORAGE_KEY = "aion.conversation.v1"
const MAX_PERSISTED_MESSAGES = 50

const GREETING: Message = {
  id: "aion-greeting",
  role: "aion",
  content:
    "Hello, Yaleel. I am here. Tell me what you want to understand, decide, research, build, or bring into alignment.",
  serif: true,
}

type StoredConversation = {
  version: 2
  clientSessionId: string
  messages: Message[]
  previousResponseId: string | null
}

type DurableMessage = {
  role: "user" | "assistant"
  content: string
}

type DurableMemoryResponse = {
  found?: boolean
  messages?: DurableMessage[]
  previous_response_id?: string | null
}

const busyStates: PresenceState[] = ["thinking", "researching", "executing"]

function createClientSessionId() {
  return crypto.randomUUID()
}

export function AionShell() {
  const [messages, setMessages] = useState<Message[]>([GREETING])
  const [working, setWorking] = useState<PresenceState>("idle")
  const [mode, setMode] = useState<InterfaceMode>("conversation")
  const [context, setContext] = useState<string | null>(null)
  const [focus, setFocus] = useState<{ venture: string; reasoning: string } | null>(null)
  const [terminalOpen, setTerminalOpen] = useState(false)
  const [connectionOpen, setConnectionOpen] = useState(false)
  const [ownerAuthOpen, setOwnerAuthOpen] = useState(false)
  const [ownerAuthenticated, setOwnerAuthenticated] = useState(false)
  const [listening, setListening] = useState(false)
  const [previousResponseId, setPreviousResponseId] = useState<string | null>(null)
  const [clientSessionId, setClientSessionId] = useState<string | null>(null)
  const [conversationHydrated, setConversationHydrated] = useState(false)
  const busyRef = useRef(false)

  useEffect(() => {
    void fetch("/api/aion/owner-session", { cache: "no-store" })
      .then((res) => res.json())
      .then((data) => setOwnerAuthenticated(Boolean(data.authenticated)))
      .catch(() => setOwnerAuthenticated(false))
  }, [])

  useEffect(() => {
    let cancelled = false

    async function hydrateConversation() {
      let localMessages: Message[] = [GREETING]
      let localPreviousResponseId: string | null = null
      let sessionId = createClientSessionId()

      try {
        const raw = window.localStorage.getItem(CONVERSATION_STORAGE_KEY)
        if (raw) {
          const stored = JSON.parse(raw) as Partial<StoredConversation> & {
            version?: number
            clientSessionId?: string
          }
          if (Array.isArray(stored.messages) && stored.messages.length > 0) {
            localMessages = stored.messages.slice(-MAX_PERSISTED_MESSAGES)
          }
          if (typeof stored.previousResponseId === "string") {
            localPreviousResponseId = stored.previousResponseId
          }
          if (typeof stored.clientSessionId === "string" && stored.clientSessionId.length >= 16) {
            sessionId = stored.clientSessionId
          }
        }
      } catch (error) {
        console.warn("[AION] Could not restore browser conversation:", error)
      }

      if (cancelled) return
      setClientSessionId(sessionId)
      setMessages(localMessages)
      setPreviousResponseId(localPreviousResponseId)

      try {
        const res = await fetch("/api/aion/memory", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ clientSessionId: sessionId }),
        })
        const data = (await res.json()) as DurableMemoryResponse

        if (!cancelled && res.ok && data.found && Array.isArray(data.messages)) {
          const restored: Message[] = data.messages.slice(-MAX_PERSISTED_MESSAGES).map((item) => ({
            id: uid(),
            role: item.role === "assistant" ? "aion" : "user",
            content: item.content,
          }))
          setMessages([GREETING, ...restored].slice(-MAX_PERSISTED_MESSAGES))
          setPreviousResponseId(
            typeof data.previous_response_id === "string" ? data.previous_response_id : null,
          )
        }
      } catch (error) {
        console.warn("[AION] Durable memory restore unavailable; using browser copy:", error)
      } finally {
        if (!cancelled) setConversationHydrated(true)
      }
    }

    void hydrateConversation()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!conversationHydrated || !clientSessionId) return

    const stored: StoredConversation = {
      version: 2,
      clientSessionId,
      messages: messages.slice(-MAX_PERSISTED_MESSAGES),
      previousResponseId,
    }

    try {
      window.localStorage.setItem(CONVERSATION_STORAGE_KEY, JSON.stringify(stored))
    } catch (error) {
      console.warn("[AION] Could not persist browser conversation:", error)
    }
  }, [clientSessionId, conversationHydrated, messages, previousResponseId])

  const presence: PresenceState = listening && working === "idle" ? "listening" : working

  const pushMessage = useCallback((m: Message) => setMessages((prev) => [...prev, m]), [])

  const handleOwnerAuthenticated = useCallback(() => {
    setOwnerAuthenticated(true)
    setOwnerAuthOpen(false)
    setMode("boardroom")
  }, [])

  const handleSend = useCallback(
    async (text: string) => {
      const trimmed = text.trim()
      if (!trimmed || busyRef.current || !clientSessionId) return
      busyRef.current = true
      setListening(false)

      pushMessage({ id: uid(), role: "user", content: trimmed })

      const turn = routeCommand(trimmed)
      setWorking(turn.working)

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
          setFocus({ venture: ventureMatch, reasoning: `You asked me to concentrate on ${ventureMatch}.` })
        } else if (turn.effect === "open-boardroom") {
          setFocus(null)
        }

        if (turn.effect === "open-boardroom") {
          if (!ownerAuthenticated) {
            setOwnerAuthOpen(true)
            pushMessage({ id: uid(), role: "aion", content: "Owner authentication is required to unlock the Boardroom." })
            setWorking("complete")
            setTimeout(() => setWorking("idle"), 500)
            busyRef.current = false
            return
          }
          setMode("boardroom")
        } else if (String(turn.effect) === "close-boardroom") {
          setMode("conversation")
        } else if (turn.effect === "open-terminal") {
          setTerminalOpen(true)
        } else if (turn.effect === "close-terminal") {
          setTerminalOpen(false)
        }
        if (turn.context) setContext(turn.context)

        pushMessage({ id: uid(), role: "aion", content: turn.reply, serif: turn.serif })
        setWorking("complete")
        setTimeout(() => setWorking("idle"), 500)
        busyRef.current = false
        return
      }

      try {
        const boundedHistory = messages
          .filter((m) => m.id !== GREETING.id && (m.role === "user" || m.role === "aion"))
          .slice(-12)
          .map((m) => ({ role: m.role === "aion" ? "assistant" : "user", content: m.content }))

        const res = await fetch("/api/aion/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            message: trimmed,
            clientSessionId,
            history: boundedHistory,
            previousResponseId: previousResponseId ?? undefined,
          }),
        })

        const data = (await res.json()) as { reply?: string; responseId?: string | null; error?: string; code?: string }
        if (!res.ok || !data.reply) throw new Error(data.error || `AION runtime request failed (${res.status})`)

        setPreviousResponseId(typeof data.responseId === "string" ? data.responseId : null)
        pushMessage({ id: uid(), role: "aion", content: data.reply })
      } catch (error) {
        const detail = error instanceof Error ? error.message : "Unknown runtime error"
        pushMessage({ id: uid(), role: "aion", content: `I couldn't complete that through the live AION runtime. ${detail}` })
      } finally {
        setWorking("complete")
        setTimeout(() => setWorking("idle"), 500)
        busyRef.current = false
      }
    },
    [clientSessionId, messages, mode, ownerAuthenticated, previousResponseId, pushMessage],
  )

  const handleNewConversation = useCallback(() => {
    setMessages([GREETING])
    setPreviousResponseId(null)
    setClientSessionId(createClientSessionId())
    setContext(null)
    setTerminalOpen(false)
    setMode("conversation")
    setWorking("idle")
    try {
      window.localStorage.removeItem(CONVERSATION_STORAGE_KEY)
    } catch (error) {
      console.warn("[AION] Could not clear browser conversation:", error)
    }
  }, [])

  const handleConnect = useCallback((title: string) => {
    setConnectionOpen(false)
    if (title === "Terminal Session") {
      setTerminalOpen(true)
      setContext("AION Repository · Vercel Sandbox")
    }
  }, [])

  const isBusy = busyStates.includes(working)
  const showHero = mode === "conversation" && messages.length <= 1

  return (
    <div className="relative flex h-dvh flex-col overflow-hidden bg-background">
      <RuntimeStatusBanner />
      <TopBar
        state={presence}
        mode={mode}
        hasNotifications={false}
        onNewConversation={handleNewConversation}
        onNotifications={() => handleSend("What needs my attention today?")}
        onSettings={() => setConnectionOpen(true)}
        onAccount={() => {
          if (ownerAuthenticated) setMode("boardroom")
          else setOwnerAuthOpen(true)
        }}
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
          <div className="pointer-events-none absolute inset-0 aion-grid opacity-30" aria-hidden />
          <div className="pointer-events-none absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-cyan/5 to-transparent" aria-hidden />

          <div className={cn("relative z-10 flex min-w-0 flex-1 flex-col transition-all duration-500 ease-out", terminalOpen ? "lg:max-w-[54%]" : "max-w-full")}>
            <div className={cn("shrink-0 transition-all duration-700", showHero ? "pt-3 sm:pt-5" : "pt-2")}>
              <div className="mx-auto flex w-full max-w-4xl flex-col items-center px-4 text-center">
                <div className="relative">
                  <div className="absolute inset-x-6 bottom-2 h-12 rounded-full bg-cyan/10 blur-2xl" aria-hidden />
                  <AionPresence state={presence} size={showHero ? 236 : 92} />
                </div>
                {showHero ? (
                  <div className="-mt-2 pb-3">
                    <h1 className="font-serif text-2xl font-light tracking-[0.08em] text-foreground sm:text-3xl">
                      The Guide who remembers who you are becoming.
                    </h1>
                    <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-muted-foreground">
                      Speak naturally. AION can think with you, research, connect systems, surface memory, and open deeper operational tools when needed.
                    </p>
                  </div>
                ) : null}
              </div>
              <ConvergenceRail state={presence} />
            </div>

            {context && <div className="shrink-0 pt-3"><ProjectContext label={context} onDismiss={() => setContext(null)} /></div>}

            <div className="flex-1 overflow-y-auto pt-4 pb-2">
              <Conversation messages={messages} working={working} onCommand={handleSend} />
            </div>

            <div className="shrink-0 px-4 pb-5 pt-2 sm:pb-6">
              <div className="mx-auto w-full max-w-3xl">
                <CommandComposer
                  onSubmit={handleSend}
                  onVoiceToggle={() => setListening((v) => !v)}
                  listening={listening}
                  disabled={isBusy || !conversationHydrated}
                  onOpenConnections={() => setConnectionOpen(true)}
                />
                <p className="mt-2 text-center text-[10px] uppercase tracking-[0.18em] text-muted-foreground/60">
                  Conversation first · deeper systems appear when useful
                </p>
              </div>
            </div>
          </div>

          {terminalOpen && <div className="relative z-10 hidden w-full p-3 lg:block lg:max-w-[46%]"><TerminalWorkspace onClose={() => setTerminalOpen(false)} /></div>}
        </div>
      )}

      <ConnectionSheet open={connectionOpen} onClose={() => setConnectionOpen(false)} onConnect={handleConnect} />
      <OwnerAuthDialog
        open={ownerAuthOpen}
        onClose={() => setOwnerAuthOpen(false)}
        onAuthenticated={handleOwnerAuthenticated}
      />
    </div>
  )
}
