import type { WidgetData } from "@/lib/aion/types"
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
}: {
  widget: WidgetData
  onCommand?: (text: string) => void
}) {
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
}
