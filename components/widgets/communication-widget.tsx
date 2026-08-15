import { Send, Mail, MessageSquare, Phone, MonitorSmartphone, Check } from "lucide-react"
import type { CommunicationWidgetData } from "@/lib/aion/types"
import { WidgetShell, WidgetAction } from "./widget-shell"
import { cn } from "@/lib/utils"

const channelMeta = {
  here: { icon: MonitorSmartphone, label: "Here" },
  email: { icon: Mail, label: "Email" },
  text: { icon: MessageSquare, label: "Text" },
  call: { icon: Phone, label: "Call briefing" },
}

export function CommunicationWidget({ data }: { data: CommunicationWidgetData }) {
  const callSelected = data.channels.find((c) => c.channel === "call")?.selected
  return (
    <WidgetShell
      icon={<Send className="h-3.5 w-3.5" />}
      label={data.sent ? "Sent" : "Delivery"}
      meta={data.sent ? `${data.sent.channel} · ${data.sent.at}` : undefined}
    >
      <h3 className="text-sm font-medium text-foreground">{data.title}</h3>

      <div className="mt-3 space-y-1.5">
        {data.channels.map((c) => {
          const meta = channelMeta[c.channel]
          return (
            <div
              key={c.channel}
              className={cn(
                "flex items-center gap-2.5 rounded-lg border px-3 py-2 text-sm transition-colors",
                c.selected
                  ? "border-gold/40 bg-gold/8 text-foreground"
                  : "border-border/60 text-muted-foreground",
              )}
            >
              <meta.icon className={cn("h-4 w-4", c.selected ? "text-gold" : "text-muted-foreground")} />
              <span className="flex-1">{meta.label}</span>
              {c.selected &&
                (data.sent ? (
                  <Check className="h-4 w-4 text-positive" />
                ) : (
                  <span className="h-2 w-2 rounded-full bg-gold" />
                ))}
            </div>
          )
        })}
      </div>

      {callSelected && !data.sent && (
        <div className="mt-4">
          <WidgetAction primary>Start call</WidgetAction>
        </div>
      )}
    </WidgetShell>
  )
}
