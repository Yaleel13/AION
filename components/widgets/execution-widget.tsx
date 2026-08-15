"use client"

import { useEffect, useState } from "react"
import { Cog, Check, Loader2, Circle, ShieldAlert } from "lucide-react"
import type { ExecutionWidgetData, ExecutionStep } from "@/lib/aion/types"
import { WidgetShell, WidgetAction } from "./widget-shell"
import { cn } from "@/lib/utils"

function StepIcon({ status }: { status: ExecutionStep["status"] }) {
  if (status === "done") return <Check className="h-3.5 w-3.5 text-positive" />
  if (status === "working") return <Loader2 className="h-3.5 w-3.5 animate-spin text-gold" />
  if (status === "blocked") return <ShieldAlert className="h-3.5 w-3.5 text-caution" />
  return <Circle className="h-3.5 w-3.5 text-muted-foreground/50" />
}

export function ExecutionWidget({ data }: { data: ExecutionWidgetData }) {
  // Gently advance the "working" step to "done" over time for a live feel.
  const [steps, setSteps] = useState(data.steps)

  useEffect(() => {
    const workingIndex = steps.findIndex((s) => s.status === "working")
    if (workingIndex === -1) return
    const t = setTimeout(() => {
      setSteps((prev) => {
        const next = [...prev]
        next[workingIndex] = { ...next[workingIndex], status: "done" }
        if (next[workingIndex + 1] && next[workingIndex + 1].status === "pending") {
          next[workingIndex + 1] = { ...next[workingIndex + 1], status: "working" }
        }
        return next
      })
    }, 2600)
    return () => clearTimeout(t)
  }, [steps])

  const needsApproval = steps.some((s) => s.status === "pending") && steps.every((s) => s.status !== "working")

  return (
    <WidgetShell icon={<Cog className="h-3.5 w-3.5" />} label="Execution">
      <h3 className="text-sm font-medium text-foreground">{data.title}</h3>

      <ol className="mt-3 space-y-2">
        {steps.map((s, i) => (
          <li key={i} className="flex items-center gap-2.5 text-sm">
            <span className="flex h-5 w-5 items-center justify-center">
              <StepIcon status={s.status} />
            </span>
            <span
              className={cn(
                s.status === "done" && "text-muted-foreground line-through decoration-border-strong",
                s.status === "working" && "text-foreground",
                s.status === "pending" && "text-muted-foreground/70",
              )}
            >
              {s.label}
            </span>
          </li>
        ))}
      </ol>

      {needsApproval && (
        <div className="mt-4 flex items-center gap-2">
          <WidgetAction primary>Approve &amp; deploy</WidgetAction>
          <WidgetAction>Hold</WidgetAction>
        </div>
      )}
    </WidgetShell>
  )
}
