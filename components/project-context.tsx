"use client"

import { Layers, X } from "lucide-react"
import { StatusDot } from "@/components/ui/status-dot"

export function ProjectContext({ label, onDismiss }: { label: string; onDismiss: () => void }) {
  return (
    <div className="mx-auto flex w-full max-w-3xl items-center justify-center px-4">
      <div className="inline-flex animate-rise items-center gap-2 rounded-full border border-violet/30 bg-violet/8 py-1 pl-3 pr-1.5 text-xs">
        <StatusDot tone="violet" pulse />
        <Layers className="h-3.5 w-3.5 text-violet" />
        <span className="text-foreground/85">{label}</span>
        <button
          onClick={onDismiss}
          className="ml-0.5 rounded-full p-1 text-muted-foreground transition-colors hover:bg-violet/15 hover:text-foreground"
          aria-label="Dismiss context"
        >
          <X className="h-3 w-3" />
        </button>
      </div>
    </div>
  )
}
