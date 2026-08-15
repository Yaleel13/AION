"use client"

import { useEffect, useRef } from "react"
import type { Message as MessageType, PresenceState } from "@/lib/aion/types"
import { Message } from "./message"

const workingLabel: Partial<Record<PresenceState, string>> = {
  thinking: "Thinking",
  researching: "Researching",
  executing: "Working",
  listening: "Listening",
}

export function Conversation({
  messages,
  working,
}: {
  messages: MessageType[]
  working: PresenceState
}) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages, working])

  const isWorking = working !== "idle" && working !== "complete"

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-4 pb-4">
      {messages.map((m) => (
        <Message key={m.id} message={m} />
      ))}

      {isWorking && (
        <div className="flex items-center gap-2.5 text-sm text-muted-foreground" aria-live="polite">
          <span className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="h-1.5 w-1.5 rounded-full bg-gold"
                style={{ animation: "pulse-soft 1.4s ease-in-out infinite", animationDelay: `${i * 0.18}s` }}
              />
            ))}
          </span>
          <span className="font-serif italic">{workingLabel[working] ?? "Working"}…</span>
        </div>
      )}

      <div ref={endRef} />
    </div>
  )
}
