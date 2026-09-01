import type { FactEnvelope } from "@/lib/aion/fact-envelope"
import { formatFactProvenance } from "@/lib/aion/fact-envelope"
import { cn } from "@/lib/utils"

export function FactProvenanceBadge({
  envelope,
  className,
  compact = false,
}: {
  envelope: Pick<FactEnvelope<unknown>, "truth_class" | "source" | "is_demo" | "fetched_at" | "observed_at" | "source_object_id">
  className?: string
  compact?: boolean
}) {
  const isDemo = envelope.is_demo || envelope.truth_class === "DEMO"
  const label = compact
    ? isDemo
      ? "Demo"
      : "Live"
    : formatFactProvenance({
        value: null,
        truth_class: envelope.truth_class,
        source: envelope.source,
        source_object_id: envelope.source_object_id,
        observed_at: envelope.observed_at,
        fetched_at: envelope.fetched_at,
        confidence: isDemo ? 0 : 1,
        is_demo: isDemo,
      })

  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md border px-2 py-0.5 text-[0.62rem] font-medium uppercase tracking-[0.12em]",
        isDemo
          ? "border-caution/35 bg-caution/10 text-caution"
          : "border-positive/25 bg-positive/8 text-positive",
        className,
      )}
      data-truth-class={envelope.truth_class}
      data-demo={isDemo ? "true" : "false"}
      title={formatFactProvenance({
        value: null,
        truth_class: envelope.truth_class,
        source: envelope.source,
        source_object_id: envelope.source_object_id,
        observed_at: envelope.observed_at,
        fetched_at: envelope.fetched_at,
        confidence: isDemo ? 0 : 1,
        is_demo: isDemo,
      })}
    >
      {label}
    </span>
  )
}
