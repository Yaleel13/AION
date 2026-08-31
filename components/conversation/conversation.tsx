"use client"

import { useEffect, useRef } from "react"
import type { Message as MessageType, PresenceState } from "@/lib/aion/types"
import { Message } from "./message"

const workingLabel: Partial<Record<PresenceState, string>> = {
  thinking: "Interpreting",
  researching: "Mapping the archive",
  executing: "Activating systems",
  listening: "Listening",
}

export function Conversation({
  messages,
  working,
  onCommand,
}: {
  messages: MessageType[]
  working: PresenceState
  onCommand?: (text: string) => void
}) {
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages, working])

  const isWorking = working !== "idle" && working !== "complete"

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6 px-4 pb-5">
      {messages.map((m) => (
        <Message key={m.id} message={m} onCommand={onCommand} />
      ))}

      {isWorking && (
        <div className="flex items-center gap-3 border-l border-cyan/25 pl-3 text-sm text-muted-foreground" aria-live="polite">
          <span className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="h-1.5 w-1.5 rounded-full bg-cyan shadow-[0_0_10px_color-mix(in_oklch,var(--cyan)_45%,transparent)]"
                style={{ animation: "pulse-soft 1.4s ease-in-out infinite", animationDelay: `${i * 0.18}s` }}
              />
            ))}
          </span>
          <span className="font-serif italic text-foreground/75">{workingLabel[working] ?? "Working"}…</span>
        </div>
      )}

      <div ref={endRef} />
    </div>
  )
}
