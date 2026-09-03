import { Sandbox } from "@vercel/sandbox"
import { hasValidOwnerSession, requireCsrfHeader } from "@/lib/aion/owner-session"

export const maxDuration = 180

const AION_REPO = "https://github.com/Yaleel13/AION.git"
const MAX_OUTPUT = 12_000
const ALLOWED_CHECKS = new Set(["inspect", "lint", "build", "all"])

type CheckName = "inspect" | "lint" | "build" | "all"

type CommandSummary = {
  name: string
  exitCode: number
  stdout: string
  stderr: string
}

function trimOutput(value: string) {
  return value.length > MAX_OUTPUT ? `${value.slice(0, MAX_OUTPUT)}\n…truncated` : value
}

async function summarize(name: string, command: Awaited<ReturnType<InstanceType<typeof Sandbox>["runCommand"]>>): Promise<CommandSummary> {
  return {
    name,
    exitCode: command.exitCode,
    stdout: trimOutput(await command.stdout()),
    stderr: trimOutput(await command.stderr()),
  }
}

export async function POST(req: Request) {
  if (!hasValidOwnerSession(req.headers.get("cookie"))) {
    return Response.json({ error: "Owner authentication required." }, { status: 401 })
  }
  const csrfError = requireCsrfHeader(req)
  if (csrfError) return csrfError

  let check: CheckName = "inspect"
  try {
    const body = (await req.json()) as { check?: string }
    if (body.check && !ALLOWED_CHECKS.has(body.check)) {
      return Response.json({ error: "Unsupported diagnostic check." }, { status: 400 })
    }
    if (body.check) check = body.check as CheckName
  } catch {
    // Empty body preserves the existing inspect-only behavior.
  }

  const sandbox = await Sandbox.create({
    persistent: false,
    timeout: 180_000,
    networkPolicy: {
      allow: ["github.com", "*.githubusercontent.com", "registry.npmjs.org"],
    },
  })

  try {
    const clone = await sandbox.runCommand("git", ["clone", "--depth", "1", AION_REPO, "repo"])
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
      const install = await sandbox.runCommand("npm", ["ci", "--prefix", "repo", "--no-audit", "--no-fund"])
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
          secretsInjected: false,
          arbitraryCommandsEnabled: false,
        })
      }

      // Dependency retrieval is complete. All code-quality checks run offline.
      await sandbox.update({ networkPolicy: "deny-all" })

      if (check === "lint" || check === "all") {
        const lint = await sandbox.runCommand("npm", ["run", "--prefix", "repo", "lint"])
        results.push(await summarize("npm run lint", lint))
      }

      if (check === "build" || check === "all") {
        const build = await sandbox.runCommand("npm", ["run", "--prefix", "repo", "build"])
        results.push(await summarize("npm run build", build))
      }
    } else {
      await sandbox.update({ networkPolicy: "deny-all" })
    }

    const checksOk = results.every((result) => result.exitCode === 0)

    return Response.json({
      ok: head.exitCode === 0 && status.exitCode === 0 && node.exitCode === 0 && checksOk,
      executor: "vercel-sandbox",
      check,
      sandbox: sandbox.name,
      persistent: false,
      repository: "Yaleel13/AION",
      revision: trimOutput((await head.stdout()).trim()),
      workingTree: (await status.stdout()).trim() || "clean",
      node: trimOutput((await node.stdout()).trim()),
      results,
      networkAfterInstall: "deny-all",
      secretsInjected: false,
      arbitraryCommandsEnabled: false,
      allowedChecks: ["inspect", "lint", "build", "all"],
    })
  } catch (error) {
    console.error("[AION] sandbox diagnostic failed:", error instanceof Error ? error.message : String(error))
    return Response.json(
      { error: "The isolated diagnostic executor could not complete the run." },
      { status: 502 },
    )
  } finally {
    await sandbox.stop().catch(() => undefined)
  }
}
