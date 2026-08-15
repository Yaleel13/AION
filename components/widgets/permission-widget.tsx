import { ShieldCheck, Lock, Check } from "lucide-react"
import type { PermissionWidgetData } from "@/lib/aion/types"
import { WidgetShell, WidgetAction } from "./widget-shell"

export function PermissionWidget({ data }: { data: PermissionWidgetData }) {
  return (
    <WidgetShell
      icon={<ShieldCheck className="h-3.5 w-3.5" />}
      label="AION is requesting access"
      accent="violet"
    >
      <p className="text-xs uppercase tracking-wider text-muted-foreground">Target</p>
      <p className="mt-0.5 text-sm font-medium text-foreground">{data.target}</p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        <div>
          <p className="text-[0.7rem] uppercase tracking-wider text-muted-foreground">Requested now</p>
          <ul className="mt-2 space-y-1.5">
            {data.abilities.map((a) => (
              <li key={a} className="flex items-center gap-2 text-sm text-foreground/90">
                <Check className="h-3.5 w-3.5 text-positive" />
                {a}
              </li>
            ))}
          </ul>
        </div>
        <div className="rounded-lg border border-caution/25 bg-caution/8 p-3">
          <p className="text-[0.7rem] uppercase tracking-wider text-caution">Requires separate approval</p>
          <ul className="mt-2 space-y-1.5">
            {data.elevated.map((a) => (
              <li key={a} className="flex items-center gap-2 text-sm text-foreground/80">
                <Lock className="h-3.5 w-3.5 text-caution" />
                {a}
              </li>
            ))}
          </ul>
        </div>
      </div>

      <div className="mt-4 flex flex-wrap gap-2">
        <WidgetAction primary>Allow session</WidgetAction>
        <WidgetAction>Review permissions</WidgetAction>
      </div>
    </WidgetShell>
  )
}
