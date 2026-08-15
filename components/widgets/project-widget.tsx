import { Boxes, AlertTriangle, ArrowRight } from "lucide-react"
import type { ProjectWidgetData, ProjectState } from "@/lib/aion/types"
import { WidgetShell, WidgetAction } from "./widget-shell"
import { StatusDot } from "@/components/ui/status-dot"

const stateMeta: Record<ProjectState, { label: string; tone: "positive" | "caution" | "critical" | "neutral" }> = {
  production: { label: "Production", tone: "positive" },
  building: { label: "Building", tone: "caution" },
  attention: { label: "Needs attention", tone: "caution" },
  paused: { label: "Paused", tone: "neutral" },
}

export function ProjectWidget({
  data,
  onCommand,
}: {
  data: ProjectWidgetData
  onCommand?: (text: string) => void
}) {
  const meta = stateMeta[data.state]
  return (
    <WidgetShell
      icon={<Boxes className="h-3.5 w-3.5" />}
      label="Project"
      meta={
        <span className="inline-flex items-center gap-1.5">
          <StatusDot tone={meta.tone} pulse={data.state === "attention"} />
          {meta.label}
        </span>
      }
    >
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="text-lg font-medium text-foreground">{data.name}</h3>
        <span className="text-xs text-muted-foreground">{data.lastDeployment}</span>
      </div>

      <div className="mt-3 flex flex-wrap gap-1.5">
        {data.services.map((s) => (
          <span
            key={s}
            className="rounded-md border border-border/70 px-2 py-0.5 text-[0.7rem] text-muted-foreground"
          >
            {s}
          </span>
        ))}
      </div>

      <p className="mt-3 text-sm text-muted-foreground">{data.activity}</p>

      {data.blockers > 0 && (
        <div className="mt-3 flex items-start gap-2 rounded-lg bg-caution/10 px-3 py-2.5 text-sm text-foreground/90">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-caution" />
          <span>{data.nextAction}</span>
        </div>
      )}

      <div className="mt-4 flex items-center gap-2">
        <WidgetAction
          primary
          onClick={() =>
            onCommand?.(
              data.blockers > 0
                ? `Repair the ${data.name} webhook failure now.`
                : `Open ${data.name} in the terminal.`,
            )
          }
        >
          {data.blockers > 0 ? "Review blocker" : "Open project"}
          <ArrowRight className="ml-1 inline h-3 w-3" />
        </WidgetAction>
      </div>
    </WidgetShell>
  )
}
