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

export function WidgetRenderer({ widget }: { widget: WidgetData }) {
  switch (widget.kind) {
    case "research":
      return <ResearchWidget data={widget} />
    case "project":
      return <ProjectWidget data={widget} />
    case "repository":
      return <RepositoryWidget data={widget} />
    case "deployment":
      return <DeploymentWidget data={widget} />
    case "data":
      return <DataWidget data={widget} />
    case "document":
      return <DocumentWidget data={widget} />
    case "communication":
      return <CommunicationWidget data={widget} />
    case "execution":
      return <ExecutionWidget data={widget} />
    case "permission":
      return <PermissionWidget data={widget} />
    default:
      return null
  }
}
