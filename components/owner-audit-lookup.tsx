"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { runtimeRequestId } from "@/lib/aion/runtime-correlation"
import { auditLookup, type AuditEvent } from "@/lib/aion/capability-audit"
import { defer } from "@/lib/defer"

export function OwnerAuditLookup({ initialRequestId = "" }: { initialRequestId?: string }) {
  const initialId = runtimeRequestId(initialRequestId)
  const [input, setInput] = useState(initialRequestId)
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [message, setMessage] = useState(initialId ? "Loading audit records…" : "Enter a runtime request ID to look up audit records.")
  const [busy, setBusy] = useState(Boolean(initialId))
  const pending = useRef<AbortController | null>(null)

  const read = useCallback(async (id: string, controller: AbortController) => {
    try {
      const response = await fetch(`/api/owner/audit?request_id=${id}`, {
        credentials: "same-origin", cache: "no-store", signal: controller.signal,
      })
      if (controller.signal.aborted) return
      if (response.status === 401 || response.status === 403) { setMessage("Owner authentication required. Unlock the Boardroom again."); return }
      if (!response.ok) { setMessage("Audit lookup unavailable. Try again when the runtime is connected."); return }
      const data = auditLookup(await response.json(), id)
      if (controller.signal.aborted) return
      if (!data) { setMessage("Audit lookup unavailable."); return }
      setEvents(data.events)
      setMessage(data.events.length ? "Matching audit records" : "No audit records found for this request ID.")
    } catch {
      if (!controller.signal.aborted) setMessage("Audit lookup unavailable. Try again when the runtime is connected.")
    } finally {
      if (pending.current === controller) { pending.current = null; setBusy(false) }
    }
  }, [])

  function lookup(value: string) {
    pending.current?.abort()
    setEvents([])
    const id = runtimeRequestId(value)
    if (!id) { setMessage("Enter a valid runtime request ID (32 lowercase hex characters)."); setBusy(false); return }
    const controller = new AbortController()
    pending.current = controller
    setBusy(true)
    setMessage("Loading audit records…")
    void read(id, controller)
  }

  useEffect(() => {
    if (initialId) {
      const controller = new AbortController()
      pending.current = controller
      defer(() => { if (!controller.signal.aborted) void read(initialId, controller) })
    }
    return () => pending.current?.abort()
  }, [initialId, read])

  return <div className="space-y-3" aria-busy={busy}>
    <form className="flex flex-wrap gap-2" onSubmit={event => { event.preventDefault(); void lookup(input) }}>
      <label className="flex min-w-0 flex-1 flex-col gap-1 text-xs">Runtime request ID
        <input value={input} onChange={event => setInput(event.target.value)} spellCheck={false} autoComplete="off"
          className="min-w-0 border border-cyan/25 bg-background p-2 font-mono text-xs" />
      </label>
      <button type="submit" disabled={busy} className="self-end border border-cyan/25 px-3 py-2 text-xs disabled:opacity-50">Look up audit</button>
    </form>
    <p role="status" className="text-xs text-muted-foreground">{message}</p>
    {events.length ? <ol className="space-y-2" aria-label="Matching audit events">
      {events.map((event, index) => <li key={`${event.timestamp}-${index}`} className="break-words border border-cyan/15 p-2 text-xs">
        <time dateTime={event.timestamp}>{event.timestamp}</time>
        <p>{event.capability} · {event.event === "job_started" ? "Job started" : event.event === "policy" ? "Policy decision" : "Outcome"}</p>
        <p>Policy: {event.policy_decision}{event.outcome ? ` · Outcome: ${event.outcome}` : ""}</p>
      </li>)}
    </ol> : null}
  </div>
}
