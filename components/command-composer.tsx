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
  { icon: Link2, label: "Paste a link", command: "Research this link for me." },
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
    // Respect CJK IME composition — don't submit mid-composition.
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
          <div className="absolute bottom-full left-0 z-20 mb-3 w-64 animate-rise overflow-hidden rounded-xl border border-border bg-popover/95 p-1 shadow-2xl backdrop-blur-md">
            {onOpenConnections && (
              <button
                type="button"
                onClick={() => {
                  setMenuOpen(false)
                  onOpenConnections()
                }}
                className="mb-1 flex w-full items-center gap-3 rounded-lg border-b border-border/60 px-3 py-2.5 text-left text-sm text-foreground/85 transition-colors hover:bg-muted"
              >
                <Plus className="h-4 w-4 text-gold" />
                Connect AION…
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
                className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left text-sm text-foreground/85 transition-colors hover:bg-muted"
              >
                <c.icon className="h-4 w-4 text-muted-foreground" />
                {c.label}
              </button>
            ))}
          </div>
        </>
      )}

      <div
        className={cn(
          "flex items-end gap-2 rounded-2xl border bg-surface/80 p-2 pl-2.5 backdrop-blur-md transition-all",
          listening
            ? "border-gold/50 shadow-[0_0_0_1px_var(--gold),0_8px_40px_-12px_var(--gold)]"
            : "border-border shadow-[0_8px_40px_-16px_rgba(0,0,0,0.8)] focus-within:border-border-strong",
        )}
      >
        <button
          type="button"
          onClick={() => setMenuOpen((o) => !o)}
          className={cn(
            "flex h-9 w-9 shrink-0 items-center justify-center rounded-xl text-muted-foreground transition-all hover:bg-muted hover:text-foreground",
            menuOpen && "rotate-45 bg-muted text-foreground",
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
          className="max-h-[200px] min-h-[36px] flex-1 resize-none bg-transparent py-2 text-[0.95rem] leading-relaxed text-foreground placeholder:text-muted-foreground/70 focus:outline-none"
        />

        <div className="flex shrink-0 items-center gap-1">
          <button
            type="button"
            onClick={onVoiceToggle}
            className={cn(
              "flex h-9 w-9 items-center justify-center rounded-xl transition-all",
              listening
                ? "bg-gold/15 text-gold"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
            aria-label={listening ? "Stop listening" : "Speak to AION"}
            aria-pressed={listening}
          >
            <Mic className="h-4.5 w-4.5" />
          </button>

          <button
            type="button"
            onClick={() => onSubmit("Call me and walk me through it.")}
            className="hidden h-9 w-9 items-center justify-center rounded-xl text-muted-foreground transition-all hover:bg-muted hover:text-foreground sm:flex"
            aria-label="Voice call mode"
          >
            <PhoneCall className="h-4 w-4" />
          </button>

          <button
            type="button"
            onClick={submit}
            disabled={!value.trim() || disabled}
            className={cn(
              "flex h-9 w-9 items-center justify-center rounded-xl transition-all",
              value.trim() && !disabled
                ? "bg-gold text-gold-foreground hover:bg-gold/90"
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
