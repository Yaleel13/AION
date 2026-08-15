import type { Message as MessageType } from "@/lib/aion/types"
import { WidgetRenderer } from "@/components/widgets/widget-renderer"
import { cn } from "@/lib/utils"

export function Message({
  message,
  onCommand,
}: {
  message: MessageType
  onCommand?: (text: string) => void
}) {
  if (message.role === "user") {
    return (
      <div className="flex animate-rise justify-end">
        <div className="max-w-[85%] rounded-2xl rounded-br-md bg-surface-raised px-4 py-2.5 text-sm leading-relaxed text-foreground/90">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className="animate-rise space-y-4">
      {message.content && (
        <div className="flex gap-3">
          <span
            className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-gold shadow-[0_0_8px_var(--gold)]"
            aria-hidden
          />
          <p
            className={cn(
              "max-w-[68ch] leading-relaxed text-foreground/95",
              message.serif
                ? "font-serif text-xl font-light italic text-foreground"
                : "text-[0.95rem]",
            )}
          >
            {message.content}
          </p>
        </div>
      )}

      {message.widgets && message.widgets.length > 0 && (
        <div className="ml-[18px] grid gap-3">
          {message.widgets.map((w, i) => (
            <WidgetRenderer key={i} widget={w} onCommand={onCommand} />
          ))}
        </div>
      )}
    </div>
  )
}
