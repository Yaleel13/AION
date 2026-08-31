"use client"

import type { PresenceState } from "@/lib/aion/types"
import { cn } from "@/lib/utils"

const stages = [
  { key: "artifact", label: "Artifact Communion", shortLabel: "Artifact" },
  { key: "prepare", label: "Transit Preparation", shortLabel: "Transit" },
  { key: "portal", label: "Portal Live", shortLabel: "Portal" },
  { key: "passage", label: "Passage Active", shortLabel: "Passage" },
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
    <div className="mx-auto w-full max-w-3xl px-3 sm:px-4" aria-label="AION convergence state">
      <div className="grid grid-cols-4 gap-2 sm:gap-3">
        {stages.map((stage, index) => (
          <div key={stage.key} className="min-w-0">
            <div
              className={cn(
                "h-px w-full transition-colors duration-500",
                index <= active ? "bg-cyan" : "bg-border",
              )}
            />
            <div className="mt-2 flex min-w-0 items-center gap-1.5 sm:gap-2">
              <span
                className={cn(
                  "size-1.5 shrink-0 rounded-full transition-all duration-500",
                  index === active
                    ? "bg-cyan shadow-[0_0_16px_var(--cyan)]"
                    : index < active
                      ? "bg-cyan-muted"
                      : "bg-border-strong",
                )}
              />
              <span
                className={cn(
                  "min-w-0 text-[9px] uppercase tracking-[0.12em] sm:text-[10px] sm:tracking-[0.18em]",
                  index === active ? "text-cyan" : "text-muted-foreground",
                )}
                title={stage.label}
              >
                <span className="sm:hidden">{stage.shortLabel}</span>
                <span className="hidden sm:inline">{stage.label}</span>
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
