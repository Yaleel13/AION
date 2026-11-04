"use client"

import { useEffect, useRef, useState } from "react"
import { Loader2 } from "lucide-react"
import { AION_REQUEST_HEADER } from "@/lib/aion/request-headers"
import { runtimeRequestId } from "@/lib/aion/runtime-correlation"
import { OwnerAuditLookup } from "@/components/owner-audit-lookup"

type State = "idle" | "running" | "success" | "failure" | "unavailable"
type TestsResult = { ok?: boolean; status?: string; duration_ms?: number }

export function OwnerRuntimeTests() {
  const [state, setState] = useState<State>("idle")
  const [message, setMessage] = useState("Run the fixed runtime safety test manifest.")
  const [duration, setDuration] = useState<number>()
  const [requestId, setRequestId] = useState<string>()
  const [showAudit, setShowAudit] = useState(false)
  const pending = useRef<AbortController | null>(null)

  useEffect(() => () => pending.current?.abort(), [])

  async function run() {
    if (pending.current) return
    const controller = new AbortController()
    pending.current = controller
    setState("running")
    setMessage("Running fixed runtime tests…")
    setDuration(undefined)
    setRequestId(undefined)
    setShowAudit(false)
    try {
      const response = await fetch("/api/owner/runtime/tests", {
        method: "POST",
        credentials: "same-origin",
        cache: "no-store",
        headers: { "Content-Type": "application/json", ...AION_REQUEST_HEADER },
        body: "{}",
        signal: controller.signal,
      })
      setRequestId(runtimeRequestId(response.headers.get("x-aion-request-id")))
      const data = await response.json() as TestsResult
      setDuration(typeof data.duration_ms === "number" ? data.duration_ms : undefined)
      if (response.status === 401 || response.status === 403) {
        setState("failure")
        setMessage("Owner authentication required. Unlock the Boardroom again.")
      } else if (!response.ok || data.status === "unavailable") {
        setState("unavailable")
        setMessage("Runtime unavailable. Start the local runtime and try again.")
      } else if (data.ok === true && data.status === "succeeded") {
        setState("success")
        setMessage("Fixed runtime tests passed.")
      } else {
        setState("failure")
        setMessage(data.status === "timeout" ? "Runtime tests timed out." : "Runtime tests failed.")
      }
    } catch {
      if (!controller.signal.aborted) {
        setState("unavailable")
        setMessage("Runtime unavailable. Start the local runtime and try again.")
      }
    } finally {
      pending.current = null
    }
  }

  return (
    <div className="space-y-3" aria-busy={state === "running"}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p role="status" aria-live="polite" className="text-sm text-foreground">{message}</p>
        <button type="button" onClick={() => void run()} disabled={state === "running"}
          className="inline-flex min-h-10 items-center gap-2 border border-cyan/25 px-3 py-2 text-xs text-foreground transition-colors hover:bg-cyan/5 disabled:cursor-wait disabled:opacity-50">
          {state === "running" ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> : null}
          Run fixed tests
        </button>
      </div>
      {duration !== undefined ? <p className="text-xs text-muted-foreground">Duration: {duration} ms</p> : null}
      {requestId ? <p className="break-all text-xs text-muted-foreground">Reference: <code>{requestId}</code></p> : null}
      {requestId ? <button type="button" onClick={() => setShowAudit(true)} className="text-xs text-cyan underline">View audit records</button> : null}
      {requestId && showAudit ? <OwnerAuditLookup key={requestId} initialRequestId={requestId} /> : null}
    </div>
  )
}
