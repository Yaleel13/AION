"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import type { Message, PresenceState, InterfaceMode } from "@/lib/aion/types"
import { routeCommand } from "@/lib/aion/mock"
import { TopBar } from "@/components/top-bar"
import { AionLandingPortal } from "@/components/aion-landing-portal"
import { TerminalWorkspace } from "@/components/terminal-workspace"
import { Boardroom } from "@/components/boardroom"
import { ConnectionSheet } from "@/components/connection-sheet"
import { RuntimeStatusBanner } from "@/components/runtime-status-banner"
import { OwnerAuthDialog } from "@/components/owner-auth-dialog"

let idCounter = 0
const uid = () => `m${++idCounter}-${Date.now()}`

const CONVERSATION_STORAGE_KEY = "aion.conversation.v1"
const MAX_PERSISTED_MESSAGES = 50
const VOICE_CAPTURE_PHASE_MS = 7_000
const MAX_VOICE_PLAYBACK_LOCK_MS = 120_000
const VOICE_PLAYBACK_RELEASE_PADDING_MS = 250

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

type LocalVoiceResponse = {
  available?: boolean
  transcript?: string
  reply?: string
  played?: boolean
  audioDurationMs?: number | null
  timingsMs?: Record<string, number> | null
  error?: string
}

const busyStates: PresenceState[] = ["thinking", "researching", "executing"]

function createClientSessionId() {
  return crypto.randomUUID()
}

export function AionShell() {
  const [messages, setMessages] = useState<Message[]>([GREETING])
  const [working, setWorking] = useState<PresenceState>("idle")
  const [mode, setMode] = useState<InterfaceMode>("conversation")
  const [focus, setFocus] = useState<{ venture: string; reasoning: string } | null>(null)
  const [terminalOpen, setTerminalOpen] = useState(false)
  const [connectionOpen, setConnectionOpen] = useState(false)
  const [ownerAuthOpen, setOwnerAuthOpen] = useState(false)
  const [ownerAuthenticated, setOwnerAuthenticated] = useState(false)
  const [listening, setListening] = useState(false)
  const [speaking, setSpeaking] = useState(false)
  const [voiceAvailable, setVoiceAvailable] = useState(false)
  const [previousResponseId, setPreviousResponseId] = useState<string | null>(null)
  const [clientSessionId, setClientSessionId] = useState<string | null>(null)
  const [conversationHydrated, setConversationHydrated] = useState(false)
  const busyRef = useRef(false)
  const voicePhaseTimerRef = useRef<number | null>(null)
  const voicePlaybackTimerRef = useRef<number | null>(null)

  useEffect(() => {
    void fetch("/api/aion/owner-session", { cache: "no-store" })
      .then((res) => res.json())
      .then((data) => setOwnerAuthenticated(Boolean(data.authenticated)))
      .catch(() => setOwnerAuthenticated(false))
  }, [])

  useEffect(() => {
    let cancelled = false

    void fetch("/api/aion/voice", { cache: "no-store" })
      .then((res) => res.json())
      .then((data: LocalVoiceResponse) => {
        if (!cancelled) setVoiceAvailable(Boolean(data.available))
      })
      .catch(() => {
        if (!cancelled) setVoiceAvailable(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    return () => {
      if (voicePhaseTimerRef.current !== null) {
        window.clearTimeout(voicePhaseTimerRef.current)
      }
      if (voicePlaybackTimerRef.current !== null) {
        window.clearTimeout(voicePlaybackTimerRef.current)
      }
    }
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

  const handleOpenBoardroom = useCallback(() => {
    if (ownerAuthenticated) setMode("boardroom")
    else setOwnerAuthOpen(true)
  }, [ownerAuthenticated])

  const handleVoiceToggle = useCallback(async () => {
    if (!voiceAvailable || listening || speaking || busyRef.current) return

    busyRef.current = true
    setSpeaking(false)
    setWorking("idle")
    setListening(true)
    let playbackLockMs = 0

    voicePhaseTimerRef.current = window.setTimeout(() => {
      voicePhaseTimerRef.current = null
      setListening(false)
      setWorking("thinking")
    }, VOICE_CAPTURE_PHASE_MS)

    try {
      const res = await fetch("/api/aion/voice", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      })
      const data = (await res.json()) as LocalVoiceResponse
      if (!res.ok || !data.transcript || !data.reply) {
        throw new Error(data.error || `AION local voice request failed (${res.status})`)
      }

      pushMessage({ id: uid(), role: "user", content: data.transcript })
      pushMessage({ id: uid(), role: "aion", content: data.reply })

      if (data.timingsMs) {
        console.info("[AION] local voice timings (ms)", data.timingsMs)
      }

      if (data.played && typeof data.audioDurationMs === "number" && data.audioDurationMs > 0) {
        playbackLockMs = Math.min(data.audioDurationMs, MAX_VOICE_PLAYBACK_LOCK_MS)
        setSpeaking(true)
      }
    } catch (error) {
      const detail = error instanceof Error ? error.message : "Unknown local voice error"
      pushMessage({ id: uid(), role: "aion", content: `I couldn't complete that local voice turn. ${detail}` })
    } finally {
      if (voicePhaseTimerRef.current !== null) {
        window.clearTimeout(voicePhaseTimerRef.current)
        voicePhaseTimerRef.current = null
      }
      setListening(false)
      setWorking("complete")

      if (playbackLockMs > 0) {
        voicePlaybackTimerRef.current = window.setTimeout(() => {
          voicePlaybackTimerRef.current = null
          setSpeaking(false)
          setWorking("idle")
          busyRef.current = false
        }, playbackLockMs + VOICE_PLAYBACK_RELEASE_PADDING_MS)
      } else {
        setSpeaking(false)
        window.setTimeout(() => setWorking("idle"), 500)
        busyRef.current = false
      }
    }
  }, [listening, pushMessage, speaking, voiceAvailable])

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
        turn.effect === "close-boardroom" ||
        turn.effect === "open-terminal" ||
        turn.effect === "close-terminal"

      if (turn.widgets?.length) {
        pushMessage({
          id: uid(),
          role: "aion",
          content: turn.reply,
          widgets: turn.widgets,
          serif: turn.serif,
          dataSource: "demo_fixture",
        })
        setWorking("complete")
        window.setTimeout(() => setWorking("idle"), 500)
        busyRef.current = false
        return
      }

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
            window.setTimeout(() => setWorking("idle"), 500)
            busyRef.current = false
            return
          }
          setMode("boardroom")
        } else if (turn.effect === "close-boardroom") {
          setMode("conversation")
        } else if (turn.effect === "open-terminal") {
          setTerminalOpen(true)
        } else if (turn.effect === "close-terminal") {
          setTerminalOpen(false)
        }

        pushMessage({ id: uid(), role: "aion", content: turn.reply, serif: turn.serif, dataSource: "demo_fixture" })
        setWorking("complete")
        window.setTimeout(() => setWorking("idle"), 500)
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

        const data = (await res.json()) as { reply?: string; responseId?: string | null; error?: string }
        if (!res.ok || !data.reply) throw new Error(data.error || `AION runtime request failed (${res.status})`)

        setPreviousResponseId(typeof data.responseId === "string" ? data.responseId : null)
        pushMessage({ id: uid(), role: "aion", content: data.reply })
      } catch (error) {
        const detail = error instanceof Error ? error.message : "Unknown runtime error"
        pushMessage({ id: uid(), role: "aion", content: `I couldn't complete that through the live AION runtime. ${detail}` })
      } finally {
        setWorking("complete")
        window.setTimeout(() => setWorking("idle"), 500)
        busyRef.current = false
      }
    },
    [clientSessionId, messages, mode, ownerAuthenticated, previousResponseId, pushMessage],
  )

  const handleNewConversation = useCallback(() => {
    if (busyRef.current) return

    if (voicePlaybackTimerRef.current !== null) {
      window.clearTimeout(voicePlaybackTimerRef.current)
      voicePlaybackTimerRef.current = null
    }
    setMessages([GREETING])
    setPreviousResponseId(null)
    setClientSessionId(createClientSessionId())
    setTerminalOpen(false)
    setMode("conversation")
    setWorking("idle")
    setListening(false)
    setSpeaking(false)
    try {
      window.localStorage.removeItem(CONVERSATION_STORAGE_KEY)
    } catch (error) {
      console.warn("[AION] Could not clear browser conversation:", error)
    }
    window.setTimeout(() => {
      document.getElementById("conversation")?.scrollIntoView({ behavior: "smooth", block: "start" })
      document.getElementById("aion-message")?.focus()
    }, 60)
  }, [])

  const handleAttention = useCallback(() => {
    setMode("conversation")
    window.setTimeout(() => void handleSend("What needs my attention today?"), 0)
  }, [handleSend])

  const handleConnect = useCallback((title: string) => {
    setConnectionOpen(false)
    if (title === "Terminal Session") {
      setTerminalOpen(true)
    }
  }, [])

  const isBusy = busyStates.includes(working)
  const conversationDisabled = isBusy || listening || speaking || !conversationHydrated

  return (
    <div className="relative flex h-dvh flex-col overflow-hidden bg-background">
      <RuntimeStatusBanner />
      <TopBar
        state={presence}
        mode={mode}
        interactionLocked={conversationDisabled}
        hasNotifications={false}
        onHome={() => setMode("conversation")}
        onNewConversation={handleNewConversation}
        onNotifications={handleAttention}
        onSettings={() => setConnectionOpen(true)}
        onAccount={handleOpenBoardroom}
      />

      {mode === "boardroom" ? (
        <div className="min-h-0 flex-1 overflow-y-auto">
          <Boardroom
            presence={presence}
            working={working}
            focus={focus}
            listening={listening}
            onSubmit={handleSend}
            onVoiceToggle={handleVoiceToggle}
            onExit={() => setMode("conversation")}
            onOpenConnections={() => setConnectionOpen(true)}
          />
        </div>
      ) : terminalOpen ? (
        <div className="relative flex min-h-0 flex-1 flex-col lg:flex-row">
          <div className="min-h-0 flex-1 overflow-hidden lg:w-[58%]">
            <AionLandingPortal
              messages={messages}
              working={working}
              presence={presence}
              listening={listening}
              voiceAvailable={voiceAvailable}
              disabled={conversationDisabled}
              compact
              ownerAuthenticated={ownerAuthenticated}
              onSubmit={handleSend}
              onVoiceToggle={handleVoiceToggle}
              onOpenConnections={() => setConnectionOpen(true)}
              onOpenBoardroom={handleOpenBoardroom}
              onOpenTerminal={() => setTerminalOpen(true)}
            />
          </div>
          <div className="min-h-[42dvh] border-t border-cyan/12 p-3 lg:min-h-0 lg:w-[42%] lg:border-l lg:border-t-0">
            <TerminalWorkspace onClose={() => setTerminalOpen(false)} />
          </div>
        </div>
      ) : (
        <AionLandingPortal
          messages={messages}
          working={working}
          presence={presence}
          listening={listening}
          voiceAvailable={voiceAvailable}
          disabled={conversationDisabled}
          ownerAuthenticated={ownerAuthenticated}
          onSubmit={handleSend}
          onVoiceToggle={handleVoiceToggle}
          onOpenConnections={() => setConnectionOpen(true)}
          onOpenBoardroom={handleOpenBoardroom}
          onOpenTerminal={() => setTerminalOpen(true)}
        />
      )}

      <ConnectionSheet open={connectionOpen} onClose={() => setConnectionOpen(false)} onConnect={handleConnect} />
      <OwnerAuthDialog open={ownerAuthOpen} onClose={() => setOwnerAuthOpen(false)} onAuthenticated={handleOwnerAuthenticated} />
    </div>
  )
}
