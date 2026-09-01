import type { MessageDataSource, WidgetData } from "@/lib/aion/types"
import { FactProvenanceBadge } from "@/components/fact-provenance-badge"
import { DEMO_FIXTURE_SOURCE } from "@/lib/aion/fact-envelope"
import { ResearchWidget } from "./research-widget"
import { ProjectWidget } from "./project-widget"
import { RepositoryWidget } from "./repository-widget"
import { DeploymentWidget } from "./deployment-widget"
import { DataWidget } from "./data-widget"
import { DocumentWidget } from "./document-widget"
import { CommunicationWidget } from "./communication-widget"
import { ExecutionWidget } from "./execution-widget"
import { PermissionWidget } from "./permission-widget"

export function WidgetRenderer({
  widget,
  onCommand,
  dataSource,
}: {
  widget: WidgetData
  onCommand?: (text: string) => void
  dataSource?: MessageDataSource
}) {
  const isDemo = dataSource === "demo_fixture"
  const demoEnvelope = {
    truth_class: "DEMO" as const,
    source: DEMO_FIXTURE_SOURCE,
    is_demo: true,
    fetched_at: undefined,
    observed_at: undefined,
    source_object_id: `widget:${widget.kind}`,
  }

  const rendered = (() => {
    switch (widget.kind) {
      case "research":
        return <ResearchWidget data={widget} />
      case "project":
        return <ProjectWidget data={widget} onCommand={onCommand} />
      case "repository":
        return <RepositoryWidget data={widget} onCommand={onCommand} />
      case "deployment":
        return <DeploymentWidget data={widget} onCommand={onCommand} />
      case "data":
        return <DataWidget data={widget} />
      case "document":
        return <DocumentWidget data={widget} onCommand={onCommand} />
      case "communication":
        return <CommunicationWidget data={widget} onCommand={onCommand} />
      case "execution":
        return <ExecutionWidget data={widget} onCommand={onCommand} />
      case "permission":
        return <PermissionWidget data={widget} onCommand={onCommand} />
      default:
        return null
    }
  })()

  if (!rendered) return null

  if (!isDemo) return rendered

  return (
    <div className="space-y-2" data-source={DEMO_FIXTURE_SOURCE}>
      <div className="flex justify-end">
        <FactProvenanceBadge envelope={demoEnvelope} compact />
      </div>
      {rendered}
    </div>
  )
}
