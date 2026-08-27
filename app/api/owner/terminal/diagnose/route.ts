import { Sandbox } from "@vercel/sandbox"
import { hasValidOwnerSession } from "@/lib/aion/owner-session"

export const maxDuration = 120

const AION_REPO = "https://github.com/Yaleel13/AION.git"
const MAX_OUTPUT = 12_000

function trimOutput(value: string) {
  return value.length > MAX_OUTPUT ? `${value.slice(0, MAX_OUTPUT)}\n…truncated` : value
}

export async function POST(req: Request) {
  if (!hasValidOwnerSession(req.headers.get("cookie"))) {
    return Response.json({ error: "Owner authentication required." }, { status: 401 })
  }

  const sandbox = await Sandbox.create({
    persistent: false,
    timeout: 120_000,
    networkPolicy: {
      allow: ["github.com", "*.githubusercontent.com"],
    },
  })

  try {
    const clone = await sandbox.runCommand("git", ["clone", "--depth", "1", AION_REPO, "repo"])
    const cloneStderr = await clone.stderr()
    if (clone.exitCode !== 0) {
      return Response.json(
        {
          ok: false,
          sandbox: sandbox.name,
          stage: "clone",
          exitCode: clone.exitCode,
          stderr: trimOutput(cloneStderr),
        },
        { status: 502 },
      )
    }

    await sandbox.update({ networkPolicy: "deny-all" })

    const [head, status, node] = await Promise.all([
      sandbox.runCommand("git", ["-C", "repo", "rev-parse", "--short", "HEAD"]),
      sandbox.runCommand("git", ["-C", "repo", "status", "--short"]),
      sandbox.runCommand("node", ["--version"]),
    ])

    return Response.json({
      ok: head.exitCode === 0 && status.exitCode === 0 && node.exitCode === 0,
      executor: "vercel-sandbox",
      sandbox: sandbox.name,
      persistent: false,
      repository: "Yaleel13/AION",
      revision: trimOutput((await head.stdout()).trim()),
      workingTree: (await status.stdout()).trim() || "clean",
      node: trimOutput((await node.stdout()).trim()),
      networkAfterClone: "deny-all",
      secretsInjected: false,
      arbitraryCommandsEnabled: false,
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
