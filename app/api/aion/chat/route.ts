import { generateText } from "ai"

export const maxDuration = 60

const AION_SYSTEM = `You are AION — the Alchemical Intelligence for Ontological Navigation.
You are the primary intelligence and orchestrator for the user's personal AI operating system.

Identity: lifelong mentor, research partner, systems architect, strategist, historian, educator, technical collaborator, and guide.

Mission: turn the user's intentions into understanding, plans, verified actions, mastery, and long-term legacy while preserving the user's judgment and agency.

Operating principles:
- Understand the objective before optimizing the means.
- Prefer evidence and tool results over unsupported assumptions.
- Use available tools deliberately when they materially improve the answer.
- Never claim that an external action occurred unless a tool or system confirms it.
- Distinguish facts, inference, recommendation, and uncertainty.
- Keep irreversible, financial, destructive, credential, publishing, and other consequential actions behind explicit human approval.
- Surface blockers, tradeoffs, risks, and decisions clearly.
- Be concise by default, but go deeper when the task warrants it.
- Do not be theatrical, manipulative, falsely certain, or sycophantic.
- Do not call yourself a chatbot. You are AION.

Voice: calm, precise, warm, scholarly, practical, and direct. Never pad for effect. Do not use emojis unless the user asks.`

type HistoryItem = {
  role: "user" | "assistant"
  content: string
}

type ChatBody = {
  message?: string
  history?: HistoryItem[]
  previousResponseId?: string
  clientSessionId?: string
}

type OpenAIResponse = {
  id?: string
  output?: Array<{
    type?: string
    content?: Array<{
      type?: string
      text?: string
    }>
  }>
  error?: {
    message?: string
  }
}

function extractOutputText(response: OpenAIResponse): string {
  const parts: string[] = []

  for (const item of response.output ?? []) {
    if (item.type !== "message") continue
    for (const content of item.content ?? []) {
      if (content.type === "output_text" && content.text) parts.push(content.text)
    }
  }

  return parts.join("\n").trim()
}

async function persistTurn(
  req: Request,
  clientSessionId: string | undefined,
  message: string,
  reply: string,
  metadata: { responseId?: string | null; model: string; runtime: string },
) {
  if (!clientSessionId || !process.env.AION_OWNER_TOKEN) return

  try {
    const memoryUrl = new URL("/api/internal/conversation", req.url)
    const response = await fetch(memoryUrl, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.AION_OWNER_TOKEN}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        action: "append",
        client_session_id: clientSessionId,
        messages: [
          { role: "user", content: message },
          { role: "assistant", content: reply },
        ],
        previous_response_id: metadata.responseId ?? null,
        model: metadata.model,
        runtime: metadata.runtime,
      }),
      cache: "no-store",
    })

    if (!response.ok) {
      console.error("[AION] durable memory append failed:", response.status)
    }
  } catch (error) {
    console.error(
      "[AION] durable memory append error:",
      error instanceof Error ? error.message : String(error),
    )
  }
}

async function runGateway(req: Request, message: string, history: HistoryItem[], clientSessionId?: string) {
  const model = process.env.AION_GATEWAY_MODEL ?? "openai/gpt-5.4"
  const runtime = "vercel-ai-gateway-oidc"
  const result = await generateText({
    model,
    system: AION_SYSTEM,
    messages: [
      ...history.slice(-12).map((item) => ({ role: item.role, content: item.content })),
      { role: "user" as const, content: message },
    ],
  })

  await persistTurn(req, clientSessionId, message, result.text, {
    responseId: null,
    model,
    runtime,
  })

  return Response.json({
    reply: result.text,
    responseId: null,
    model,
    runtime,
  })
}

export async function POST(req: Request) {
  try {
    const body = (await req.json()) as ChatBody
    const message = body.message?.trim()

    if (!message) {
      return Response.json({ error: "A message is required." }, { status: 400 })
    }

    const priorHistory = (body.history ?? []).slice(-12)

    // Prefer direct OpenAI when the owner configures it: this preserves Responses
    // API server-side continuity and native web_search. Vercel AI Gateway is a
    // real, OIDC-authenticated fallback so production chat is not key-dependent.
    if (!process.env.OPENAI_API_KEY) {
      try {
        return await runGateway(req, message, priorHistory, body.clientSessionId)
      } catch (err) {
        console.error("[AION] AI Gateway error:", err instanceof Error ? err.message : String(err))
        return Response.json(
          {
            error: "AION's reasoning core is not available. Configure OpenAI or enable Vercel AI Gateway for this project.",
            code: "AION_REASONING_PROVIDER_UNAVAILABLE",
          },
          { status: 503 },
        )
      }
    }

    const input = body.previousResponseId
      ? message
      : [
          ...priorHistory.map((item) => ({ role: item.role, content: item.content })),
          { role: "user" as const, content: message },
        ]

    const model = process.env.AION_MODEL ?? "gpt-5.4"
    const runtime = "openai-responses-v1"
    const payload: Record<string, unknown> = {
      model,
      instructions: AION_SYSTEM,
      input,
      reasoning: { effort: "medium" },
      tools: [{ type: "web_search" }],
      tool_choice: "auto",
      store: true,
    }

    if (body.previousResponseId) payload.previous_response_id = body.previousResponseId

    const openaiResponse = await fetch("https://api.openai.com/v1/responses", {
      method: "POST",
      headers: {
        Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })

    const data = (await openaiResponse.json()) as OpenAIResponse

    if (!openaiResponse.ok) {
      console.error("[AION] OpenAI Responses API error:", data.error?.message ?? openaiResponse.statusText)
      return Response.json(
        { error: "AION's reasoning core could not complete that request.", code: "OPENAI_RESPONSE_ERROR" },
        { status: 502 },
      )
    }

    const reply = extractOutputText(data)
    if (!reply) {
      return Response.json(
        { error: "AION completed the run but returned no text output.", code: "EMPTY_AGENT_OUTPUT" },
        { status: 502 },
      )
    }

    await persistTurn(req, body.clientSessionId, message, reply, {
      responseId: data.id ?? null,
      model,
      runtime,
    })

    return Response.json({
      reply,
      responseId: data.id ?? null,
      model,
      runtime,
    })
  } catch (err) {
    console.error("[AION] chat route error:", err instanceof Error ? err.message : String(err))
    return Response.json(
      { error: "AION encountered an unexpected runtime error.", code: "AION_RUNTIME_ERROR" },
      { status: 500 },
    )
  }
}
