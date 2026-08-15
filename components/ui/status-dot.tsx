import { cn } from "@/lib/utils"

type Tone = "positive" | "caution" | "critical" | "violet" | "neutral"

const toneMap: Record<Tone, string> = {
  positive: "bg-positive",
  caution: "bg-caution",
  critical: "bg-critical",
  violet: "bg-violet",
  neutral: "bg-muted-foreground",
}

export function StatusDot({
  tone = "neutral",
  pulse = false,
  className,
}: {
  tone?: Tone
  pulse?: boolean
  className?: string
}) {
  return (
    <span className={cn("relative inline-flex h-2 w-2 shrink-0", className)}>
      {pulse && (
        <span
          className={cn(
            "absolute inline-flex h-full w-full animate-ping rounded-full opacity-60",
            toneMap[tone],
          )}
        />
      )}
      <span className={cn("relative inline-flex h-2 w-2 rounded-full", toneMap[tone])} />
    </span>
  )
}
