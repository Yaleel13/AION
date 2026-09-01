/** Provenance metadata for any integration-derived or displayed fact. */

export type TruthClass = "LIVE_VERIFIED" | "LIVE_STALE" | "INFERRED" | "DEMO"

export interface FactEnvelope<T> {
  value: T
  truth_class: TruthClass
  source: string
  source_object_id?: string
  observed_at?: string
  fetched_at?: string
  expires_at?: string
  sync_cursor?: string
  confidence: number
  is_demo: boolean
  trace_id?: string
}

export const DEMO_FIXTURE_SOURCE = "demo_fixture" as const

function isoNow(): string {
  return new Date().toISOString()
}

/** Wrap fixture / synthetic data — never present as live provider telemetry. */
export function demoFact<T>(
  value: T,
  options: { source?: string; sourceObjectId?: string } = {},
): FactEnvelope<T> {
  const fetchedAt = isoNow()
  return {
    value,
    truth_class: "DEMO",
    source: options.source ?? DEMO_FIXTURE_SOURCE,
    source_object_id: options.sourceObjectId,
    fetched_at: fetchedAt,
    confidence: 0,
    is_demo: true,
  }
}

/** Wrap verified live provider or runtime data. */
export function liveVerifiedFact<T>(
  value: T,
  options: {
    source: string
    sourceObjectId?: string
    observedAt?: string
    fetchedAt?: string
    expiresAt?: string
    syncCursor?: string
    traceId?: string
  },
): FactEnvelope<T> {
  return {
    value,
    truth_class: "LIVE_VERIFIED",
    source: options.source,
    source_object_id: options.sourceObjectId,
    observed_at: options.observedAt,
    fetched_at: options.fetchedAt ?? isoNow(),
    expires_at: options.expiresAt,
    sync_cursor: options.syncCursor,
    confidence: 1,
    is_demo: false,
    trace_id: options.traceId,
  }
}

export function formatFactProvenance(envelope: FactEnvelope<unknown>): string {
  if (envelope.is_demo || envelope.truth_class === "DEMO") {
    return `${envelope.source} · demo fixture · not live data`
  }
  const age =
    envelope.fetched_at != null
      ? `verified ${relativeAge(envelope.fetched_at)}`
      : envelope.observed_at != null
        ? `observed ${relativeAge(envelope.observed_at)}`
        : "verified recently"
  const objectId = envelope.source_object_id ? ` · ${envelope.source_object_id}` : ""
  return `${envelope.source}${objectId} · ${age} · live`
}

function relativeAge(iso: string): string {
  const deltaMs = Date.now() - new Date(iso).getTime()
  if (!Number.isFinite(deltaMs) || deltaMs < 0) return "just now"
  const seconds = Math.floor(deltaMs / 1000)
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 48) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}
