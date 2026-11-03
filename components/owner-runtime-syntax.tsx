"use client"

import { useEffect, useRef, useState } from "react"
import { Loader2 } from "lucide-react"
import { AION_REQUEST_HEADER } from "@/lib/aion/request-headers"

type State = "idle" | "running" | "success" | "failure" | "unavailable"
type SyntaxResult = { ok?: boolean; status?: string; output?: string; truncated?: boolean }

export function OwnerRuntimeSyntax() {
  const [state, setState] = useState<State>("idle")
  const [message, setMessage] = useState("Check the runtime’s Python syntax.")
  const [output, setOutput] = useState("")
  const pending = useRef<AbortController | null>(null)

  useEffect(() => () => pending.current?.abort(), [])

  async function run() {
    if (pending.current) return
    const controller = new AbortController()
    pending.current = controller
    setState("running")
    setMessage("Running syntax check…")
    setOutput("")
    try {
      const response = await fetch("/api/owner/runtime/syntax", {
        method: "POST", credentials: "same-origin", cache: "no-store",
        headers: { "Content-Type": "application/json", ...AION_REQUEST_HEADER },
        body: "{}", signal: controller.signal,
      })
      const data = await response.json() as SyntaxResult
      if (response.status === 401 || response.status === 403) {
        setState("failure")
        setMessage("Owner authentication required. Unlock the Boardroom again.")
      } else if (!response.ok || data.status === "unavailable") {
        setState("unavailable")
        setMessage("Runtime unavailable. Start the local runtime and try again.")
      } else if (data.ok === true && data.status === "succeeded") {
        setState("success")
        setMessage("Syntax check passed.")
      } else {
        setState("failure")
        setMessage(data.status === "timeout" ? "Syntax check timed out." : "Syntax check failed.")
      }
      if (typeof data.output === "string") setOutput(data.output + (data.truncated ? "\nOutput truncated." : ""))
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
          Run syntax check
        </button>
      </div>
      {output ? <pre className="max-h-48 overflow-auto whitespace-pre-wrap break-words border border-cyan/15 bg-background/30 p-3 text-xs text-muted-foreground">{output}</pre> : null}
    </div>
  )
}
