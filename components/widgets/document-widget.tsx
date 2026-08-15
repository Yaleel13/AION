import { FileText } from "lucide-react"
import type { DocumentWidgetData } from "@/lib/aion/types"
import { WidgetShell, WidgetAction } from "./widget-shell"

export function DocumentWidget({
  data,
  onCommand,
}: {
  data: DocumentWidgetData
  onCommand?: (text: string) => void
}) {
  return (
    <WidgetShell
      icon={<FileText className="h-3.5 w-3.5" />}
      label="Document"
      meta={data.updated}
    >
      <div className="flex items-start gap-3">
        <div className="flex h-12 w-10 shrink-0 items-center justify-center rounded-md border border-border/70 bg-muted/40">
          <FileText className="h-5 w-5 text-gold" />
        </div>
        <div className="min-w-0">
          <h3 className="text-sm font-medium text-foreground">{data.title}</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">{data.type}</p>
          <p className="mt-2 text-sm leading-relaxed text-muted-foreground">{data.excerpt}</p>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <WidgetAction primary onClick={() => onCommand?.(`Open the document "${data.title}".`)}>
          Open
        </WidgetAction>
        <WidgetAction onClick={() => onCommand?.(`Preview the document "${data.title}".`)}>
          Preview
        </WidgetAction>
        <WidgetAction onClick={() => onCommand?.(`Download the document "${data.title}".`)}>
          Download
        </WidgetAction>
        <WidgetAction onClick={() => onCommand?.(`Email me the "${data.title}".`)}>Send</WidgetAction>
      </div>
    </WidgetShell>
  )
}
