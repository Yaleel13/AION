"use client"

import type { PresenceState } from "@/lib/aion/types"
import { cn } from "@/lib/utils"

const stages = [
  { key: "artifact", label: "Artifact Communion" },
  { key: "prepare", label: "Transit Preparation" },
  { key: "portal", label: "Portal Live" },
  { key: "passage", label: "Passage Active" },
] as const

function activeStage(state: PresenceState) {
  switch (state) {
    case "thinking":
    case "researching":
      return 1
    case "executing":
      return 2
    case "complete":
      return 3
    default:
      return 0
  }
}

export function ConvergenceRail({ state }: { state: PresenceState }) {
  const active = activeStage(state)

  return (
    <div className="mx-auto flex w-full max-w-3xl items-center gap-2 px-4" aria-label="AION convergence state">
      {stages.map((stage, index) => (
        <div key={stage.key} className="flex min-w-0 flex-1 items-center gap-2">
          <div className="min-w-0 flex-1">
            <div
              className={cn(
                "h-px w-full transition-colors duration-500",
                index <= active ? "bg-cyan" : "bg-border",
              )}
            />
            <div className="mt-2 flex items-center gap-2">
              <span
                className={cn(
                  "size-1.5 shrink-0 rounded-full transition-all duration-500",
                  index === active ? "bg-cyan shadow-[0_0_16px_var(--cyan)]" : index < active ? "bg-cyan-muted" : "bg-border-strong",
                )}
              />
              <span
                className={cn(
                  "truncate text-[10px] uppercase tracking-[0.18em]",
                  index === active ? "text-cyan" : "text-muted-foreground",
                )}
              >
                {stage.label}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
