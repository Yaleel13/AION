export type AuditEvent = {
  capability: "runtime.syntax" | "runtime.tests" | "runtime_status"
  policy_decision: "allowed" | "denied" | "unavailable" | "not_evaluated"
  event: "policy" | "job_started" | "outcome"
  outcome: string | null
  timestamp: string
}
export type AuditLookup = { request_id: string; events: AuditEvent[] }

/** Strip all non-contract data even if an upstream accidentally includes it. */
export function auditLookup(value: unknown, requestId: string): AuditLookup | null {
  if (!value || typeof value !== "object") return null
  const data = value as Record<string, unknown>
  if (data.request_id !== requestId || !Array.isArray(data.events) || data.events.length > 100) return null
  const events: AuditEvent[] = []
  for (const value of data.events) {
    if (!value || typeof value !== "object") return null
    const row = value as Record<string, unknown>
    if (typeof row.capability !== "string" || !["runtime.syntax", "runtime.tests", "runtime_status"].includes(row.capability) ||
        typeof row.policy_decision !== "string" || !["allowed", "denied", "unavailable", "not_evaluated"].includes(row.policy_decision) ||
        typeof row.event !== "string" || !["policy", "job_started", "outcome"].includes(row.event) ||
        typeof row.timestamp !== "string" || !Number.isFinite(Date.parse(row.timestamp)) ||
        !(row.outcome === null || (typeof row.outcome === "string" && ["succeeded", "failed", "timeout", "unavailable", "cancelled", "denied", "policy_unavailable", "rejected"].includes(row.outcome)))) return null
    events.push({ capability: row.capability as AuditEvent["capability"],
      policy_decision: row.policy_decision as AuditEvent["policy_decision"], event: row.event as AuditEvent["event"],
      outcome: row.outcome as string | null, timestamp: new Date(row.timestamp).toISOString() })
  }
  return { request_id: requestId, events }
}
