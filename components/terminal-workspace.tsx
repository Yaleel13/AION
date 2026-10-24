"use client"

import { useCallback, useEffect, useState } from "react"
import {
  Hammer,
  LockKeyhole,
  Play,
  SearchCheck,
  ShieldCheck,
  Terminal,
  Wrench,
  X,
} from "lucide-react"
import { defer } from "@/lib/defer"
import { AION_REQUEST_HEADER } from "@/lib/aion/owner-session"

type SessionState = {
  configured: boolean
  authenticated: boolean
}

type CheckName = "inspect" | "lint" | "build" | "all"

type CommandSummary = {
  name: string
  exitCode: number
  stdout: string
  stderr: string
}

type DiagnosticResult = {
  ok?: boolean
  executor?: string
  mode?: string
  check?: CheckName
  sandbox?: string
  persistent?: boolean
  repository?: string
  revision?: string
  workingTree?: string
  node?: string
  system?: string
  cwd?: string | null
  networkAfterInstall?: string
  executionBoundary?: string
  secretsInjected?: boolean
  arbitraryCommandsEnabled?: boolean
  results?: CommandSummary[]
  allowedChecks?: CheckName[]
  error?: string
}

type RuntimeStatus = {
  operations?: {
    terminal_executor_connected?: boolean
    terminal_executor_mode?: string | null
  }
}

type ExecutorMode = "local-controlled" | "vercel-sandbox" | null

const CHECKS: Array<{
  id: CheckName
  label: string
  icon: typeof Play
}> = [
  { id: "inspect", label: "Inspect", icon: SearchCheck },
  { id: "lint", label: "Lint", icon: Wrench },
  { id: "build", label: "Build", icon: Hammer },
  { id: "all", label: "Run all", icon: Play },
]

function formatDiagnosticResult(result: DiagnosticResult) {
  const lines = [
    `check: ${result.check ?? "inspect"}`,
    `status: ${result.ok ? "passed" : "failed"}`,
    `executor: ${result.executor ?? "unknown"}`,
  ]

  if (result.mode) lines.push(`mode: ${result.mode}`)
  if (result.sandbox) lines.push(`sandbox: ${result.sandbox}`)
  if (result.repository) lines.push(`repository: ${result.repository}`)
  if (result.revision) lines.push(`revision: ${result.revision}`)
  if (result.workingTree) lines.push(`working tree: ${result.workingTree}`)
  if (result.cwd) lines.push(`working directory: ${result.cwd}`)
  if (result.node) lines.push(`node: ${result.node}`)
  if (result.system) lines.push(`system: ${result.system}`)

  if (typeof result.persistent === "boolean") {
    lines.push(`persistent: ${String(result.persistent)}`)
  }

  if (result.executionBoundary) {
    lines.push(`execution boundary: ${result.executionBoundary}`)
  }

  if (result.networkAfterInstall) {
    lines.push(`network policy: ${result.networkAfterInstall}`)
  }

  if (typeof result.secretsInjected === "boolean") {
    lines.push(
      `production secrets injected: ${String(result.secretsInjected)}`,
    )
  }

  if (typeof result.arbitraryCommandsEnabled === "boolean") {
    lines.push(
      `arbitrary commands enabled: ${String(
        result.arbitraryCommandsEnabled,
      )}`,
    )
  }

  return lines.join("\n")
}

export function TerminalWorkspace({
  onClose,
}: {
  onClose: () => void
}) {
  const [session, setSession] = useState<SessionState>({
    configured: true,
    authenticated: false,
  })
  const [executorMode, setExecutorMode] =
    useState<ExecutorMode>(null)
  const [token, setToken] = useState("")
  const [loading, setLoading] = useState(true)
  const [running, setRunning] = useState<CheckName | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<DiagnosticResult | null>(null)

  const localMode = executorMode === "local-controlled"

  const refreshSession = useCallback(async () => {
    setLoading(true)

    try {
      const runtimeResponse = await fetch("/api/runtime/status", {
        cache: "no-store",
      })

      if (runtimeResponse.ok) {
        const runtime = (await runtimeResponse.json()) as RuntimeStatus
        const mode = runtime.operations?.terminal_executor_mode
        const connected =
          runtime.operations?.terminal_executor_connected === true

        if (connected && mode === "local-controlled") {
          setExecutorMode("local-controlled")
          setSession({
            configured: true,
            authenticated: true,
          })
          setError(null)
          return
        }
      }

      setExecutorMode("vercel-sandbox")

      const response = await fetch("/api/aion/owner-session", {
        cache: "no-store",
      })

      setSession((await response.json()) as SessionState)
    } catch {
      setError("Executor status is unavailable.")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    defer(() => {
      void refreshSession()
    })
  }, [refreshSession])

  const unlock = useCallback(async () => {
    if (!token.trim()) return

    setError(null)
    setLoading(true)

    try {
      const response = await fetch("/api/aion/owner-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: token.trim() }),
      })

      const data = (await response.json()) as {
        authenticated?: boolean
        error?: string
      }

      if (!response.ok || !data.authenticated) {
        throw new Error(
          data.error || "Owner authentication failed.",
        )
      }

      setToken("")
      setSession((current) => ({
        ...current,
        authenticated: true,
      }))
    } catch (unlockError) {
      setError(
        unlockError instanceof Error
          ? unlockError.message
          : "Owner authentication failed.",
      )
    } finally {
      setLoading(false)
    }
  }, [token])

  const lock = useCallback(async () => {
    await fetch("/api/aion/owner-session", {
      method: "DELETE",
    }).catch(() => undefined)

    setSession((current) => ({
      ...current,
      authenticated: false,
    }))
    setResult(null)
    setToken("")
    setError(null)
  }, [])

  const runDiagnostic = useCallback(async (check: CheckName) => {
    setRunning(check)
    setError(null)
    setResult(null)

    try {
      const response = await fetch(
        "/api/owner/terminal/diagnose",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...AION_REQUEST_HEADER,
          },
          body: JSON.stringify({ check }),
        },
      )

      const data = (await response.json()) as DiagnosticResult

      if (response.status === 401) {
        setSession((current) => ({
          ...current,
          authenticated: false,
        }))
        throw new Error(
          "Owner session expired. Unlock the executor again.",
        )
      }

      if (!response.ok) {
        throw new Error(
          data.error || "Controlled executor diagnostic failed.",
        )
      }

      setResult(data)
    } catch (runError) {
      setError(
        runError instanceof Error
          ? runError.message
          : "Controlled executor diagnostic failed.",
      )
    } finally {
      setRunning(null)
    }
  }, [])

  const headerStatus = localMode
    ? "Local Executive ready"
    : session.authenticated
      ? "Sandbox ready"
      : "Owner locked"

  return (
    <div className="flex h-full flex-col overflow-hidden rounded-xl border border-border bg-[oklch(0.12_0.008_285)]">
      <div className="flex items-center justify-between gap-3 border-b border-border bg-surface/40 px-4 py-2.5">
        <div className="flex items-center gap-2">
          <Terminal className="h-4 w-4 text-gold" />
          <span className="text-xs font-medium uppercase tracking-[0.14em] text-muted-foreground">
            AION Terminal · {headerStatus}
          </span>
        </div>

        <button
          onClick={onClose}
          className="rounded-md p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground"
          aria-label="Close terminal"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-5">
        {loading ? (
          <div className="text-xs text-muted-foreground">
            Checking executor…
          </div>
        ) : session.authenticated ? (
          <>
            <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-4">
              <div className="flex items-center gap-2 text-sm font-medium text-foreground">
                <ShieldCheck className="h-4 w-4 text-emerald-400" />
                {localMode
                  ? "Native Local Executive available"
                  : "Isolated diagnostic executor available"}
              </div>

              <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
                {localMode
                  ? "AION can inspect, lint, and build the trusted local AION checkout through fixed allowlisted capabilities. These operations run on this machine through the Local Executive and do not expose an arbitrary shell."
                  : "AION can inspect, lint, and build the public AION repository inside an ephemeral Vercel Sandbox. Dependency download is allowed only before checks; network access is then disabled. Production secrets are never injected."}
              </p>
            </div>

            <div className="flex flex-wrap gap-2">
              {CHECKS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  type="button"
                  onClick={() => void runDiagnostic(id)}
                  disabled={running !== null}
                  className="inline-flex items-center gap-2 rounded-md bg-foreground px-3 py-2 text-xs font-medium text-background disabled:cursor-not-allowed disabled:opacity-50"
                >
                  <Icon className="h-3.5 w-3.5" />
                  {running === id
                    ? `Running ${label.toLowerCase()}…`
                    : label}
                </button>
              ))}

              {!localMode ? (
                <button
                  type="button"
                  onClick={lock}
                  disabled={running !== null}
                  className="inline-flex items-center gap-2 rounded-md border border-border px-3 py-2 text-xs text-muted-foreground hover:text-foreground disabled:opacity-50"
                >
                  <LockKeyhole className="h-3.5 w-3.5" />
                  Lock executor
                </button>
              ) : null}
            </div>

            {result ? (
              <div className="space-y-3">
                <pre className="whitespace-pre-wrap break-words rounded-lg border border-border bg-black/20 p-4 font-mono text-[0.72rem] leading-relaxed text-foreground">
                  {formatDiagnosticResult(result)}
                </pre>

                {(result.results ?? []).map((command) => (
                  <pre
                    key={command.name}
                    className="whitespace-pre-wrap break-words rounded-lg border border-border bg-black/20 p-4 font-mono text-[0.7rem] leading-relaxed text-foreground"
                  >{`$ ${command.name}
exit: ${command.exitCode}
${command.stdout || command.stderr || "(no output)"}${
                    command.stderr && command.stdout
                      ? `\n${command.stderr}`
                      : ""
                  }`}</pre>
                ))}
              </div>
            ) : null}

            <p className="text-[0.7rem] leading-relaxed text-muted-foreground">
              {localMode
                ? "Local execution is limited to AION's predefined capability registry. Arbitrary shell commands, caller-controlled arguments, sudo, destructive commands, credential operations, deployments, and package publishing remain unavailable."
                : "This remains a diagnostic executor, not an arbitrary shell. Repository writes, deployments, destructive commands, credential operations, package publishing, and other consequential actions remain unavailable until separately reviewed and approval-gated."}
            </p>
          </>
        ) : (
          <div className="mx-auto my-auto w-full max-w-md rounded-xl border border-caution/30 bg-caution/5 p-5">
            <div className="flex items-center gap-2 text-sm font-medium text-foreground">
              <LockKeyhole className="h-4 w-4 text-caution" />
              Owner authentication required
            </div>

            <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
              Enter the AION owner token you stored in Vercel. It
              is sent only to AION over HTTPS to create an HttpOnly
              owner session and is not saved in browser storage.
            </p>

            <div className="mt-4 flex gap-2">
              <input
                type="password"
                value={token}
                onChange={(event) => setToken(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void unlock()
                }}
                autoComplete="off"
                spellCheck={false}
                placeholder="AION owner token"
                className="min-w-0 flex-1 rounded-md border border-border bg-background/60 px-3 py-2 text-sm text-foreground outline-none focus:border-gold/50"
              />

              <button
                type="button"
                onClick={unlock}
                disabled={
                  !token.trim() || loading || !session.configured
                }
                className="rounded-md bg-foreground px-3 py-2 text-xs font-medium text-background disabled:cursor-not-allowed disabled:opacity-50"
              >
                Unlock executor
              </button>
            </div>

            {!session.configured ? (
              <p className="mt-3 text-xs text-caution">
                AION_OWNER_TOKEN is not configured on this deployment.
              </p>
            ) : null}
          </div>
        )}

        {error ? (
          <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
            {error}
          </div>
        ) : null}
      </div>
    </div>
  )
}
