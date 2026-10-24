import { Sandbox } from "@vercel/sandbox"
import { hasValidOwnerSession, requireCsrfHeader } from "@/lib/aion/owner-session"

export const maxDuration = 180

const AION_REPO = "https://github.com/Yaleel13/AION.git"
const MAX_OUTPUT = 12_000
const ALLOWED_CHECKS = new Set(["inspect", "lint", "build", "all"])

const RUNTIME_URL = (
  process.env.AION_RUNTIME_URL ?? "http://127.0.0.1:8000"
).replace(/\/+$/, "")

const LOCAL_RUNTIME =
  (process.env.AION_RUNTIME_MODE ?? "").trim().toLowerCase() === "local"

type CheckName = "inspect" | "lint" | "build" | "all"

type CommandSummary = {
  name: string
  exitCode: number
  stdout: string
  stderr: string
}

type LocalCapabilityName =
  | "project.inspect"
  | "git.status"
  | "system.info"
  | "project.lint"
  | "project.build"

type LocalCapabilityResult = {
  ok: boolean
  executor: string
  mode?: string
  capability: string
  classification?: string
  exit_code: number
  stdout: string
  stderr: string
  cwd?: string
  arbitrary_commands_enabled?: boolean
  sudo_enabled?: boolean
}

function trimOutput(value: string) {
  return value.length > MAX_OUTPUT
    ? `${value.slice(0, MAX_OUTPUT)}\n…truncated`
    : value
}

function isLoopbackRequest(req: Request) {
  const hostname = new URL(req.url).hostname
  return ["localhost", "127.0.0.1", "[::1]", "::1"].includes(hostname)
}

async function runLocalCapability(
  capability: LocalCapabilityName,
): Promise<LocalCapabilityResult> {
  const response = await fetch(`${RUNTIME_URL}/local-executive/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    cache: "no-store",
    body: JSON.stringify({ capability }),
  })

  const payload = (await response.json()) as Partial<LocalCapabilityResult> & {
    detail?: string
  }

  if (!response.ok) {
    throw new Error(
      payload.detail ?? `Local capability ${capability} failed.`,
    )
  }

  if (
    typeof payload.capability !== "string" ||
    typeof payload.exit_code !== "number" ||
    typeof payload.stdout !== "string" ||
    typeof payload.stderr !== "string"
  ) {
    throw new Error(`Local capability ${capability} returned an invalid response.`)
  }

  return payload as LocalCapabilityResult
}

function summarizeLocal(result: LocalCapabilityResult): CommandSummary {
  return {
    name: result.capability,
    exitCode: result.exit_code,
    stdout: trimOutput(result.stdout),
    stderr: trimOutput(result.stderr),
  }
}

async function runLocalDiagnostic(check: CheckName) {
  const capabilities: LocalCapabilityName[] = [
    "project.inspect",
    "git.status",
    "system.info",
  ]

  if (check === "lint" || check === "all") {
    capabilities.push("project.lint")
  }

  if (check === "build" || check === "all") {
    capabilities.push("project.build")
  }

  const executed: LocalCapabilityResult[] = []

  for (const capability of capabilities) {
    executed.push(await runLocalCapability(capability))
  }

  const revision = executed.find(
    (result) => result.capability === "project.inspect",
  )
  const status = executed.find(
    (result) => result.capability === "git.status",
  )
  const system = executed.find(
    (result) => result.capability === "system.info",
  )

  return Response.json({
    ok: executed.every((result) => result.ok && result.exit_code === 0),
    executor: "aion-local-controlled",
    mode: "local-controlled",
    check,
    repository: "Yaleel13/AION",
    revision: revision?.stdout.trim() || "unknown",
    workingTree: status?.stdout.trim() || "clean",
    system: system?.stdout.trim() || "unknown",
    cwd: executed[0]?.cwd ?? null,
    persistent: true,
    results: executed.map(summarizeLocal),
    networkAfterInstall: "not-applicable-local-host",
    executionBoundary: "trusted-local-project",
    arbitraryCommandsEnabled: false,
    allowedChecks: ["inspect", "lint", "build", "all"],
  })
}

async function summarize(
  name: string,
  command: Awaited<ReturnType<InstanceType<typeof Sandbox>["runCommand"]>>,
): Promise<CommandSummary> {
  return {
    name,
    exitCode: command.exitCode,
    stdout: trimOutput(await command.stdout()),
    stderr: trimOutput(await command.stderr()),
  }
}

async function runSandboxDiagnostic(check: CheckName) {
  const sandbox = await Sandbox.create({
    persistent: false,
    timeout: 180_000,
    networkPolicy: {
      allow: ["github.com", "*.githubusercontent.com", "registry.npmjs.org"],
    },
  })

  try {
    const clone = await sandbox.runCommand(
      "git",
      ["clone", "--depth", "1", AION_REPO, "repo"],
    )

    if (clone.exitCode !== 0) {
      return Response.json(
        {
          ok: false,
          executor: "vercel-sandbox",
          stage: "clone",
          result: await summarize("git clone", clone),
        },
        { status: 502 },
      )
    }

    const [head, status, node] = await Promise.all([
      sandbox.runCommand("git", ["-C", "repo", "rev-parse", "--short", "HEAD"]),
      sandbox.runCommand("git", ["-C", "repo", "status", "--short"]),
      sandbox.runCommand("node", ["--version"]),
    ])

    const results: CommandSummary[] = []

    if (check !== "inspect") {
      const install = await sandbox.runCommand(
        "npm",
        ["ci", "--prefix", "repo", "--no-audit", "--no-fund"],
      )

      results.push(await summarize("npm ci", install))

      if (install.exitCode !== 0) {
        return Response.json({
          ok: false,
          executor: "vercel-sandbox",
          check,
          repository: "Yaleel13/AION",
          revision: (await head.stdout()).trim(),
          results,
          networkAfterInstall: "not-reached",
          executionBoundary: "ephemeral-sandbox",
          secretsInjected: false,
          arbitraryCommandsEnabled: false,
        })
      }

      await sandbox.update({ networkPolicy: "deny-all" })

      if (check === "lint" || check === "all") {
        const lint = await sandbox.runCommand(
          "npm",
          ["run", "--prefix", "repo", "lint"],
        )
        results.push(await summarize("npm run lint", lint))
      }

      if (check === "build" || check === "all") {
        const build = await sandbox.runCommand(
          "npm",
          ["run", "--prefix", "repo", "build"],
        )
        results.push(await summarize("npm run build", build))
      }
    } else {
      await sandbox.update({ networkPolicy: "deny-all" })
    }

    const checksOk = results.every((result) => result.exitCode === 0)

    return Response.json({
      ok:
        head.exitCode === 0 &&
        status.exitCode === 0 &&
        node.exitCode === 0 &&
        checksOk,
      executor: "vercel-sandbox",
      mode: "vercel-sandbox-diagnostics",
      check,
      sandbox: sandbox.name,
      persistent: false,
      repository: "Yaleel13/AION",
      revision: trimOutput((await head.stdout()).trim()),
      workingTree: (await status.stdout()).trim() || "clean",
      node: trimOutput((await node.stdout()).trim()),
      results,
      networkAfterInstall: "deny-all",
      executionBoundary: "ephemeral-sandbox",
      secretsInjected: false,
      arbitraryCommandsEnabled: false,
      allowedChecks: ["inspect", "lint", "build", "all"],
    })
  } finally {
    await sandbox.stop().catch(() => undefined)
  }
}

export async function POST(req: Request) {
  /*
   * Local AION OS:
   *   localhost presence + CSRF header.
   *
   * Cloud:
   *   authenticated owner session + CSRF header.
   */
  if (LOCAL_RUNTIME) {
    if (!isLoopbackRequest(req)) {
      return Response.json(
        { error: "Local Executive UI access is localhost-only." },
        { status: 403 },
      )
    }
  } else if (!hasValidOwnerSession(req.headers.get("cookie"))) {
    return Response.json(
      { error: "Owner authentication required." },
      { status: 401 },
    )
  }

  const csrfError = requireCsrfHeader(req)
  if (csrfError) return csrfError

  let check: CheckName = "inspect"

  try {
    const body = (await req.json()) as { check?: string }

    if (body.check && !ALLOWED_CHECKS.has(body.check)) {
      return Response.json(
        { error: "Unsupported diagnostic check." },
        { status: 400 },
      )
    }

    if (body.check) {
      check = body.check as CheckName
    }
  } catch {
    // Empty body preserves inspect-only behavior.
  }

  try {
    if (LOCAL_RUNTIME) {
      return await runLocalDiagnostic(check)
    }

    return await runSandboxDiagnostic(check)
  } catch (error) {
    console.error(
      "[AION] terminal diagnostic failed:",
      error instanceof Error ? error.message : String(error),
    )

    return Response.json(
      {
        error:
          error instanceof Error
            ? error.message
            : "The controlled executor could not complete the run.",
      },
      { status: 502 },
    )
  }
}
