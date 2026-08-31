"use client"

import { useRef, useState } from "react"
import {
  Plus,
  Mic,
  ArrowUp,
  PhoneCall,
  Github,
  TerminalSquare,
  Paperclip,
  Link2,
  FolderGit2,
} from "lucide-react"
import { cn } from "@/lib/utils"

interface CommandComposerProps {
  onSubmit: (text: string) => void
  onVoiceToggle: () => void
  listening: boolean
  disabled?: boolean
  placeholder?: string
  onOpenConnections?: () => void
}

const advancedCapabilities = [
  { icon: Github, label: "Connect repository", command: "Connect this repository." },
  { icon: FolderGit2, label: "Open a project", command: "Open YaliTek." },
  { icon: TerminalSquare, label: "Open terminal", command: "Open it in the terminal." },
  { icon: Link2, label: "Research a link", command: "Research this link for me." },
  { icon: Paperclip, label: "Upload files", command: "" },
]

export function CommandComposer({
  onSubmit,
  onVoiceToggle,
  listening,
  disabled,
  placeholder = "Speak to AION…",
  onOpenConnections,
}: CommandComposerProps) {
  const [value, setValue] = useState("")
  const [menuOpen, setMenuOpen] = useState(false)
  const taRef = useRef<HTMLTextAreaElement>(null)

  const submit = () => {
    const text = value.trim()
    if (!text || disabled) return
    onSubmit(text)
    setValue("")
    if (taRef.current) taRef.current.style.height = "auto"
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.nativeEvent.isComposing || e.keyCode === 229) return
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  const autosize = (el: HTMLTextAreaElement) => {
    el.style.height = "auto"
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }

  return (
    <div className="relative">
      {menuOpen && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} aria-hidden />
          <div className="absolute bottom-full left-0 z-20 mb-3 w-64 animate-rise overflow-hidden rounded-2xl border border-cyan/15 bg-popover/95 p-1.5 shadow-2xl backdrop-blur-xl">
            {onOpenConnections && (
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false)
                  onOpenConnections()
                }}
                className="mb-1 flex w-full items-center gap-3 rounded-xl border-b border-cyan/10 px-3 py-2.5 text-left text-sm text-foreground/90 transition-colors hover:bg-cyan/7"
              >
                <Plus className="h-4 w-4 text-cyan" />
                Open connections
              </button>
            )}
            {advancedCapabilities.map((c) => (
              <button
                key={c.label}
                type="button"
                onClick={() => {
                  setMenuOpen(false)
                  if (c.command) onSubmit(c.command)
                }}
                className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm text-foreground/85 transition-colors hover:bg-cyan/7"
              >
                <c.icon className="h-4 w-4 text-cyan-muted" />
                {c.label}
              </button>
            ))}
          </div>
        </>
      )}

      <div
        className={cn(
          "relative flex items-end gap-2 overflow-hidden rounded-[1.35rem] border bg-surface/84 p-2 pl-2.5 backdrop-blur-xl transition-all",
          "before:pointer-events-none before:absolute before:inset-x-5 before:top-0 before:h-px before:bg-gradient-to-r before:from-transparent before:via-cyan/60 before:to-transparent",
          listening
            ? "border-magenta/35 shadow-[0_0_0_1px_color-mix(in_oklch,var(--magenta)_34%,transparent),0_18px_60px_-28px_var(--magenta)]"
            : "border-cyan/15 shadow-[0_14px_50px_-30px_rgba(0,0,0,0.95)] focus-within:border-cyan/35",
        )}
      >
        <button
          type="button"
          onClick={() => setMenuOpen((o) => !o)}
          className={cn(
            "flex h-10 w-10 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-all hover:bg-cyan/8 hover:text-cyan",
            menuOpen && "rotate-45 bg-cyan/8 text-cyan",
          )}
          aria-label="Advanced capabilities"
          aria-expanded={menuOpen}
        >
          <Plus className="h-5 w-5" />
        </button>

        <textarea
          ref={taRef}
          rows={1}
          value={value}
          disabled={disabled}
          onChange={(e) => {
            setValue(e.target.value)
            autosize(e.target)
          }}
          onKeyDown={handleKeyDown}
          placeholder={listening ? "Listening…" : placeholder}
          aria-label="Message to AION"
          className="max-h-[200px] min-h-[40px] flex-1 resize-none bg-transparent py-2.5 text-[0.98rem] leading-relaxed text-foreground placeholder:text-muted-foreground/65 focus:outline-none"
        />

        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={onVoiceToggle}
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-xl transition-all",
              listening
                ? "bg-magenta/12 text-magenta"
                : "text-muted-foreground hover:bg-cyan/8 hover:text-cyan",
            )}
            aria-label={listening ? "Stop listening" : "Speak to AION"}
            aria-pressed={listening}
          >
            <Mic className="h-4.5 w-4.5" />
          </button>

          <button
            type="button"
            onClick={() => onSubmit("Call me and walk me through it.")}
            className="hidden h-10 w-10 items-center justify-center rounded-xl text-muted-foreground transition-all hover:bg-cyan/8 hover:text-cyan sm:flex"
            aria-label="Voice call mode"
          >
            <PhoneCall className="h-4 w-4" />
          </button>

          <button
            type="button"
            onClick={submit}
            disabled={!value.trim() || disabled}
            className={cn(
              "flex h-10 w-10 items-center justify-center rounded-xl transition-all",
              value.trim() && !disabled
                ? "bg-cyan text-cyan-foreground shadow-[0_0_24px_color-mix(in_oklch,var(--cyan)_24%,transparent)] hover:bg-cyan/90"
                : "bg-muted text-muted-foreground",
            )}
            aria-label="Send"
          >
            <ArrowUp className="h-4.5 w-4.5" />
          </button>
        </div>
      </div>
    </div>
  )
}
