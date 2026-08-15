import { Rocket, Globe, Activity } from "lucide-react"
import type { DeploymentWidgetData } from "@/lib/aion/types"
import { WidgetShell, WidgetAction } from "./widget-shell"
import { StatusDot } from "@/components/ui/status-dot"

const statusMeta = {
  ready: { tone: "positive" as const, label: "Ready" },
  building: { tone: "caution" as const, label: "Building" },
  error: { tone: "critical" as const, label: "Error" },
}

export function DeploymentWidget({ data }: { data: DeploymentWidgetData }) {
  const meta = statusMeta[data.status]
  return (
    <WidgetShell
      icon={<Rocket className="h-3.5 w-3.5" />}
      label="Deployment"
      meta={
        <span className="inline-flex items-center gap-1.5">
          <StatusDot tone={meta.tone} pulse={data.status === "building"} />
          {meta.label}
        </span>
      }
    >
      <div className="flex items-center gap-2 text-sm">
        <Globe className="h-4 w-4 text-gold" />
        <span className="font-mono text-foreground">{data.url}</span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className="rounded-lg bg-muted/40 px-3 py-2">
          <p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Commit</p>
          <p className="mt-0.5 font-mono text-sm text-foreground/90">{data.commit}</p>
        </div>
        <div className="rounded-lg bg-muted/40 px-3 py-2">
          <p className="text-[0.65rem] uppercase tracking-wider text-muted-foreground">Project</p>
          <p className="mt-0.5 font-mono text-sm text-foreground/90">{data.project}</p>
        </div>
      </div>

      <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
        <Activity className="h-3.5 w-3.5 text-positive" />
        {data.health}
      </div>

      <div className="mt-4 flex gap-2">
        <WidgetAction primary>Visit deployment</WidgetAction>
        <WidgetAction>View logs</WidgetAction>
      </div>
    </WidgetShell>
  )
}
