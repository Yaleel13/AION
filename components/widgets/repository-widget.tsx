import { GitBranch, GitCommitHorizontal, GitPullRequest, CheckCircle2, XCircle, Loader2 } from "lucide-react"
import type { RepositoryWidgetData } from "@/lib/aion/types"
import { WidgetShell, WidgetAction } from "./widget-shell"

const ciMeta = {
  passing: { icon: CheckCircle2, className: "text-positive", label: "CI passing" },
  failing: { icon: XCircle, className: "text-critical", label: "CI failing" },
  running: { icon: Loader2, className: "text-caution animate-spin", label: "CI running" },
}

export function RepositoryWidget({ data }: { data: RepositoryWidgetData }) {
  const Ci = ciMeta[data.ci]
  return (
    <WidgetShell
      icon={<GitBranch className="h-3.5 w-3.5" />}
      label="Repository"
      meta={
        <span className="inline-flex items-center gap-1.5">
          <Ci.icon className={`h-3.5 w-3.5 ${Ci.className}`} />
          {Ci.label}
        </span>
      }
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="font-mono text-sm text-foreground">{data.repo}</h3>
        <span className="inline-flex items-center gap-1 rounded-md bg-muted/60 px-2 py-0.5 font-mono text-xs text-muted-foreground">
          <GitBranch className="h-3 w-3" />
          {data.branch}
        </span>
      </div>

      <div className="mt-3 flex items-start gap-2.5 rounded-lg bg-muted/40 px-3 py-2.5">
        <GitCommitHorizontal className="mt-0.5 h-4 w-4 shrink-0 text-gold" />
        <div className="min-w-0">
          <p className="truncate text-sm text-foreground/90">{data.lastCommit.message}</p>
          <p className="mt-0.5 font-mono text-xs text-muted-foreground">
            {data.lastCommit.sha} · {data.lastCommit.author} · {data.lastCommit.when}
          </p>
        </div>
      </div>

      <div className="mt-3 space-y-1.5">
        {data.pullRequests.map((pr) => (
          <div key={pr.number} className="flex items-center gap-2.5 text-sm">
            <GitPullRequest className="h-3.5 w-3.5 shrink-0 text-violet" />
            <span className="min-w-0 flex-1 truncate text-foreground/90">{pr.title}</span>
            <span className="shrink-0 rounded-md border border-border/70 px-1.5 py-0.5 text-[0.65rem] capitalize text-muted-foreground">
              #{pr.number} · {pr.state}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <WidgetAction primary>Open in terminal</WidgetAction>
        <WidgetAction>View pull requests</WidgetAction>
      </div>
    </WidgetShell>
  )
}
