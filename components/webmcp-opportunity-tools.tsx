"use client"

import { useEffect } from "react"

type PreparedOpportunity = {
  lead_id: string
  source_url: string
  requester_identity: string
  problem: string
  service: string
  fit_score: number
  confidence_score: number
  response_draft: string
  risks: string
}

type PreparationResponse = {
  prepared_count: number
  source_lead_count: number
  summary: string
  items: PreparedOpportunity[]
  error?: string
}

type WebMcpTool = {
  name: string
  description: string
  inputSchema: Record<string, unknown>
  annotations?: Record<string, boolean>
  execute: (input: Record<string, unknown>) => Promise<unknown> | unknown
}

type ModelContext = {
  registerTool: (tool: WebMcpTool, options?: { signal?: AbortSignal }) => void
}

function modelContext(): ModelContext | null {
  const value = (document as Document & { modelContext?: ModelContext }).modelContext
  return value && typeof value.registerTool === "function" ? value : null
}

async function loadPreparedOpportunities(): Promise<PreparationResponse> {
  const response = await fetch("/api/owner/moltbook-preparation", {
    cache: "no-store",
    credentials: "same-origin",
  })
  const body = (await response.json()) as PreparationResponse
  if (!response.ok) {
    throw new Error(body.error || `Opportunity review unavailable (${response.status})`)
  }
  return body
}

function publicOpportunity(item: PreparedOpportunity) {
  return {
    id: item.lead_id,
    source_url: item.source_url,
    requester: item.requester_identity,
    problem: item.problem,
    service: item.service,
    fit_score: item.fit_score,
    confidence_score: item.confidence_score,
    risks: item.risks,
  }
}

function score(item: PreparedOpportunity) {
  return Number(((item.fit_score * 0.55) + (item.confidence_score * 0.45)).toFixed(4))
}

export function WebMcpOpportunityTools() {
  useEffect(() => {
    const context = modelContext()
    if (!context) return

    const controller = new AbortController()
    const safeAnnotations = { readOnlyHint: true, untrustedContentHint: true }

    const tools: WebMcpTool[] = [
      {
        name: "list_opportunities",
        description: "List AION opportunities already prepared for owner review. Read-only. Requires the existing authenticated owner session and never contacts a third party.",
        inputSchema: {
          type: "object",
          properties: {
            limit: { type: "integer", minimum: 1, maximum: 8, default: 8 },
            minimum_confidence: { type: "number", minimum: 0, maximum: 1, default: 0 },
          },
          additionalProperties: false,
        },
        annotations: safeAnnotations,
        async execute(input) {
          const data = await loadPreparedOpportunities()
          const limit = Math.min(8, Math.max(1, Number(input.limit ?? 8)))
          const minimumConfidence = Math.min(1, Math.max(0, Number(input.minimum_confidence ?? 0)))
          const items = data.items
            .filter((item) => item.confidence_score >= minimumConfidence)
            .slice(0, limit)
            .map(publicOpportunity)
          return {
            count: items.length,
            qualified_pool: data.source_lead_count,
            prepared_count: data.prepared_count,
            opportunities: items,
          }
        },
      },
      {
        name: "get_opportunity",
        description: "Get one prepared AION opportunity by lead id with its evidence-oriented review fields. Read-only and owner-session protected.",
        inputSchema: {
          type: "object",
          properties: {
            id: { type: "string", minLength: 8 },
          },
          required: ["id"],
          additionalProperties: false,
        },
        annotations: safeAnnotations,
        async execute(input) {
          const data = await loadPreparedOpportunities()
          const id = String(input.id ?? "")
          const item = data.items.find((candidate) => candidate.lead_id === id)
          if (!item) return { found: false, id }
          return { found: true, opportunity: publicOpportunity(item) }
        },
      },
      {
        name: "rank_opportunities",
        description: "Rank a bounded set of prepared AION opportunities using fit and confidence only. This is deterministic, read-only, and does not approve, contact, apply, buy, trade, connect wallets, or send funds.",
        inputSchema: {
          type: "object",
          properties: {
            ids: {
              type: "array",
              minItems: 1,
              maxItems: 8,
              uniqueItems: true,
              items: { type: "string", minLength: 8 },
            },
            limit: { type: "integer", minimum: 1, maximum: 8, default: 8 },
          },
          additionalProperties: false,
        },
        annotations: safeAnnotations,
        async execute(input) {
          const data = await loadPreparedOpportunities()
          const requestedIds = Array.isArray(input.ids) ? new Set(input.ids.map(String)) : null
          const limit = Math.min(8, Math.max(1, Number(input.limit ?? 8)))
          const ranked = data.items
            .filter((item) => !requestedIds || requestedIds.has(item.lead_id))
            .map((item) => ({ ...publicOpportunity(item), rank_score: score(item) }))
            .sort((a, b) => b.rank_score - a.rank_score)
            .slice(0, limit)
            .map((item, index) => ({ rank: index + 1, ...item }))
          return { count: ranked.length, ranking: ranked }
        },
      },
      {
        name: "prepare_review",
        description: "Prepare a non-destructive review packet for up to eight existing AION opportunities. It returns drafts as reference material only and performs no approval, execution, contact, application, payment, wallet, or trading action.",
        inputSchema: {
          type: "object",
          properties: {
            ids: {
              type: "array",
              minItems: 1,
              maxItems: 8,
              uniqueItems: true,
              items: { type: "string", minLength: 8 },
            },
          },
          required: ["ids"],
          additionalProperties: false,
        },
        annotations: safeAnnotations,
        async execute(input) {
          const ids = Array.isArray(input.ids) ? input.ids.map(String).slice(0, 8) : []
          const data = await loadPreparedOpportunities()
          const byId = new Map(data.items.map((item) => [item.lead_id, item]))
          const packet = ids.flatMap((id) => {
            const item = byId.get(id)
            if (!item) return []
            return [{
              ...publicOpportunity(item),
              rank_score: score(item),
              response_draft_reference: item.response_draft,
              status: "review_only",
            }]
          })
          return {
            mode: "review_only",
            destructive_actions_available: false,
            count: packet.length,
            items: packet,
          }
        },
      },
    ]

    for (const tool of tools) {
      try {
        context.registerTool(tool, { signal: controller.signal })
      } catch (error) {
        console.warn(`[AION] WebMCP tool ${tool.name} was not registered:`, error)
      }
    }

    return () => controller.abort()
  }, [])

  return null
}
