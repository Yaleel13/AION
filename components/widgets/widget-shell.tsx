import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

interface WidgetShellProps {
  icon: ReactNode
  label: string
  meta?: ReactNode
  children: ReactNode
  className?: string
  accent?: "gold" | "violet"
}

/**
 * A temporary instrument summoned by AION into the conversation.
 * Restrained surface, hairline border, a quiet header — no left-stripe cards,
 * no glowing borders.
 */
export function WidgetShell({ icon, label, meta, children, className, accent = "gold" }: WidgetShellProps) {
  return (
    <div
      className={cn(
        "animate-rise overflow-hidden rounded-xl border border-border bg-surface/70 backdrop-blur-sm",
        className,
      )}
    >
      <div className="flex items-center justify-between gap-3 border-b border-border/70 px-4 py-2.5">
        <div className="flex items-center gap-2.5">
          <span
            className={cn(
              "flex h-6 w-6 items-center justify-center rounded-md",
              accent === "gold" ? "bg-gold/12 text-gold" : "bg-violet/15 text-violet",
            )}
          >
            {icon}
          </span>
          <span className="text-[0.7rem] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            {label}
          </span>
        </div>
        {meta && <div className="text-xs text-muted-foreground">{meta}</div>}
      </div>
      <div className="p-4">{children}</div>
    </div>
  )
}

export function WidgetAction({
  children,
  primary = false,
  onClick,
}: {
  children: ReactNode
  primary?: boolean
  onClick?: () => void
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-md px-3 py-1.5 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-1 focus-visible:ring-offset-surface",
        primary
          ? "bg-gold text-gold-foreground hover:bg-gold/90"
          : "border border-border-strong text-foreground/80 hover:bg-muted hover:text-foreground",
      )}
    >
      {children}
    </button>
  )
}
