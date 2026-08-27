"use client"

import { useEffect, useRef, useState } from "react"
import { X, Maximize2, RotateCw, Copy, Circle } from "lucide-react"
import { StatusDot } from "@/components/ui/status-dot"
import { cn } from "@/lib/utils"

interface Line {
  text: string
  tone?: "prompt" | "output" | "success" | "muted" | "warn"
}

const script: Line[] = [
  { text: "# Demo / fixture transcript — not a live remote session", tone: "muted" },
  { text: "aion@remote:~/Yaleel13/AION$ git status", tone: "prompt" },
  { text: "On branch main", tone: "output" },
  { text: "Your branch is up to date with 'origin/main'.", tone: "muted" },
  { text: "", tone: "output" },
  { text: "aion@remote:~/Yaleel13/AION$ python -m pytest tests/ -q", tone: "prompt" },
  { text: "collected 8 items", tone: "muted" },
  { text: "tests/test_endpoints.py ........                          [100%]", tone: "success" },
  { text: "8 passed in 1.24s", tone: "success" },
  { text: "", tone: "output" },
  { text: "aion@remote:~/Yaleel13/AION$ curl -s localhost:8000/health", tone: "prompt" },
  { text: '{"status":"ok"}', tone: "output" },
  { text: "", tone: "output" },
  { text: "aion@remote:~/Yaleel13/AION$ tail -n 2 logs/resend-webhook.log", tone: "prompt" },
  { text: "WARN  signature verification skipped — handler returned early", tone: "warn" },
  { text: "→ AION: this is the source of the silent failure. Patch prepared, awaiting approval.", tone: "muted" },
]

const toneClass: Record<NonNullable<Line["tone"]>, string> = {
  prompt: "text-gold",
  output: "text-foreground/90",
  success: "text-positive",
  muted: "text-muted-foreground",
  warn: "text-caution",
}

export function TerminalWorkspace({ onClose }: { onClose: () => void }) {
  const [visible, setVisible] = useState(0)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (visible >= script.length) return
    const t = setTimeout(() => setVisible((v) => v + 1), 320)
    return () => clearTimeout(t)
  }, [visible])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" })
  }, [visible])

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-border bg-[oklch(0.12_0.008_285)]">
      {/* Header */}
      <div className="flex items-center justify-between gap-3 border-b border-border bg-surface/40 px-4 py-2.5">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5" aria-hidden>
            <Circle className="h-2.5 w-2.5 fill-critical/70 text-critical/70" />
            <Circle className="h-2.5 w-2.5 fill-caution/70 text-caution/70" />
            <Circle className="h-2.5 w-2.5 fill-positive/70 text-positive/70" />
          </div>
          <span className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            AION Terminal · Demo / fixture
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground" aria-label="Copy output">
            <Copy className="h-3.5 w-3.5" />
          </button>
          <button className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground" aria-label="Reconnect">
            <RotateCw className="h-3.5 w-3.5" />
          </button>
          <button className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground" aria-label="Expand">
            <Maximize2 className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={onClose}
            className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label="Close terminal"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

      {/* Meta row */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1 border-b border-border/60 px-4 py-2 text-[0.7rem] text-muted-foreground">
        <span>
          Project <span className="font-mono text-foreground/80">Yaleel13/AION</span>
        </span>
        <span>
          Environment <span className="text-foreground/80">Remote</span>
        </span>
        <span className="inline-flex items-center gap-1.5">
          <StatusDot tone="positive" pulse />
          Connected
        </span>
      </div>

      {/* Output */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto p-4 font-mono text-[0.8rem] leading-relaxed"
        role="log"
        aria-label="Terminal output"
      >
        {script.slice(0, visible).map((line, i) => (
          <div key={i} className={cn("whitespace-pre-wrap", toneClass[line.tone ?? "output"])}>
            {line.text || "\u00A0"}
          </div>
        ))}
        {visible >= script.length && (
          <div className="mt-1 flex items-center text-gold">
            aion@remote:~/Yaleel13/AION$
            <span className="ml-1 inline-block h-4 w-2 animate-[pulse-soft_1.1s_step-end_infinite] bg-gold" />
          </div>
        )}
      </div>
    </div>
  )
}
