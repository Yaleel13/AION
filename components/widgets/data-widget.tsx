import { BarChart3, TrendingUp, TrendingDown } from "lucide-react"
import type { DataWidgetData } from "@/lib/aion/types"
import { WidgetShell } from "./widget-shell"
import { cn } from "@/lib/utils"

export function DataWidget({ data }: { data: DataWidgetData }) {
  const max = Math.max(...data.series.map((s) => s.value), 1)
  return (
    <WidgetShell icon={<BarChart3 className="h-3.5 w-3.5" />} label="Data">
      <h3 className="text-sm font-medium text-foreground">{data.title}</h3>

      <div className="mt-3 grid grid-cols-3 gap-2">
        {data.metrics.map((m) => (
          <div key={m.label} className="rounded-lg bg-muted/40 px-3 py-2.5">
            <p className="truncate text-[0.65rem] uppercase tracking-wider text-muted-foreground">
              {m.label}
            </p>
            <p className="mt-1 text-lg font-medium tabular-nums text-foreground">{m.value}</p>
            {m.delta && (
              <p
                className={cn(
                  "mt-0.5 inline-flex items-center gap-1 text-xs tabular-nums",
                  m.direction === "up" ? "text-positive" : "text-critical",
                )}
              >
                {m.direction === "up" ? (
                  <TrendingUp className="h-3 w-3" />
                ) : (
                  <TrendingDown className="h-3 w-3" />
                )}
                {m.delta}
              </p>
            )}
          </div>
        ))}
      </div>

      <div className="mt-4 flex h-24 items-stretch gap-1.5" aria-hidden>
        {data.series.map((s) => (
          <div key={s.label} className="flex h-full flex-1 flex-col items-center gap-1.5">
            <div className="flex w-full flex-1 items-end">
              <div
                className="w-full rounded-t-sm bg-gradient-to-t from-violet/40 to-gold/70 transition-all"
                style={{ height: `${Math.max((s.value / max) * 100, 4)}%` }}
              />
            </div>
            <span className="text-[0.6rem] text-muted-foreground">{s.label}</span>
          </div>
        ))}
      </div>
    </WidgetShell>
  )
}
