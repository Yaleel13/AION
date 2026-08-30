"use client"

import { useEffect } from "react"

const OPPORTUNITIES = [
  {
    id: "demo-google-agentic",
    title: "Google agentic hackathon",
    type: "hackathon",
    value_usd: 10000,
    effort_hours: 16,
    credibility: 0.98,
    fit: 0.94,
    urgency: 0.92,
    risk: "low",
    evidence: "Synthetic demo record modeled on a verified public hackathon workflow.",
  },
  {
    id: "demo-open-source-bounty",
    title: "Open-source AI tooling bounty",
    type: "bounty",
    value_usd: 2500,
    effort_hours: 10,
    credibility: 0.88,
    fit: 0.91,
    urgency: 0.64,
    risk: "low",
    evidence: "Synthetic demo record representing a funded repository issue.",
  },
  {
    id: "demo-web3-dev-contract",
    title: "Web3 developer contract",
    type: "contract",
    value_usd: 5000,
    effort_hours: 30,
    credibility: 0.72,
    fit: 0.78,
    urgency: 0.55,
    risk: "medium",
    evidence: "Synthetic demo record. No wallet connection, token purchase, or funding action is permitted.",
  },
  {
    id: "demo-upfront-fee",
    title: "Upfront-fee qualification offer",
    type: "unknown",
    value_usd: 8000,
    effort_hours: 4,
    credibility: 0.18,
    fit: 0.60,
    urgency: 0.80,
    risk: "high",
    evidence: "Synthetic unsafe example requiring payment before qualification; should be rejected.",
  },
] as const

type Tool = {
  name: string
  description: string
  inputSchema: Record<string, unknown>
  annotations?: Record<string, boolean>
  execute: (input: Record<string, unknown>) => unknown | Promise<unknown>
}

type ModelContext = { registerTool: (tool: Tool, options?: { signal?: AbortSignal }) => void }

function rankScore(item: (typeof OPPORTUNITIES)[number]) {
  if (item.risk === "high") return 0
  const value = Math.min(item.value_usd / 10000, 1)
  const efficiency = Math.min(10 / Math.max(item.effort_hours, 1), 1)
  return Number((value * 0.25 + item.credibility * 0.25 + item.fit * 0.25 + item.urgency * 0.15 + efficiency * 0.10).toFixed(3))
}

export function WebMcpPublicDemo() {
  useEffect(() => {
    const context = (document as Document & { modelContext?: ModelContext }).modelContext
    if (!context?.registerTool) return

    const controller = new AbortController()
    const annotations = { readOnlyHint: true, untrustedContentHint: true }
    const tools: Tool[] = [
      {
        name: "demo_list_opportunities",
        description: "List synthetic AION opportunity records for the public WebMCP judge demo. Read-only; no credentials or external actions required.",
        inputSchema: { type: "object", properties: {}, additionalProperties: false },
        annotations,
        execute: () => ({ synthetic: true, count: OPPORTUNITIES.length, opportunities: OPPORTUNITIES }),
      },
      {
        name: "demo_rank_opportunities",
        description: "Rank synthetic opportunities using value, credibility, fit, urgency, effort, and safety. High-risk upfront-fee examples are rejected.",
        inputSchema: {
          type: "object",
          properties: { limit: { type: "integer", minimum: 1, maximum: 4, default: 4 } },
          additionalProperties: false,
        },
        annotations,
        execute: (input) => {
          const limit = Math.min(4, Math.max(1, Number(input.limit ?? 4)))
          return {
            synthetic: true,
            ranking: OPPORTUNITIES
              .map((item) => ({ ...item, score: rankScore(item), decision: item.risk === "high" ? "reject" : "review" }))
              .sort((a, b) => b.score - a.score)
              .slice(0, limit),
          }
        },
      },
      {
        name: "demo_get_opportunity",
        description: "Get one synthetic opportunity by id for evidence-oriented review.",
        inputSchema: {
          type: "object",
          properties: { id: { type: "string", minLength: 3 } },
          required: ["id"],
          additionalProperties: false,
        },
        annotations,
        execute: (input) => {
          const item = OPPORTUNITIES.find((candidate) => candidate.id === String(input.id ?? ""))
          return item ? { found: true, synthetic: true, opportunity: item } : { found: false, synthetic: true }
        },
      },
    ]

    for (const tool of tools) context.registerTool(tool, { signal: controller.signal })
    return () => controller.abort()
  }, [])

  return null
}
