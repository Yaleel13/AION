import { Microscope, ArrowUpRight } from "lucide-react"
import type { ResearchWidgetData } from "@/lib/aion/types"
import { WidgetShell } from "./widget-shell"
import { cn } from "@/lib/utils"

const confidenceTone: Record<ResearchWidgetData["confidence"], string> = {
  low: "text-critical",
  moderate: "text-caution",
  high: "text-positive",
}

export function ResearchWidget({ data }: { data: ResearchWidgetData }) {
  return (
    <WidgetShell
      icon={<Microscope className="h-3.5 w-3.5" />}
      label="Research"
      accent="violet"
      meta={
        <span className="inline-flex items-center gap-1.5">
          <span className="text-muted-foreground">Confidence</span>
          <span className={cn("font-medium capitalize", confidenceTone[data.confidence])}>
            {data.confidence}
          </span>
        </span>
      }
    >
      <h3 className="font-serif text-lg leading-tight text-foreground">{data.topic}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{data.summary}</p>

      <ul className="mt-4 space-y-2.5">
        {data.findings.map((f, i) => (
          <li key={i} className="flex gap-2.5 text-sm leading-relaxed text-foreground/90">
            <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-gold" aria-hidden />
            {f}
          </li>
        ))}
      </ul>

      <div className="mt-4 flex flex-wrap gap-2 border-t border-border/60 pt-3">
        {data.sources.map((s, i) => (
          <a
            key={i}
            href={s.url}
            className="group inline-flex items-center gap-1 rounded-md bg-muted/60 px-2.5 py-1 text-xs text-muted-foreground transition-colors hover:text-foreground"
          >
            {s.title}
            <ArrowUpRight className="h-3 w-3 opacity-60 transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
          </a>
        ))}
      </div>
    </WidgetShell>
  )
}
