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

async function runGateway(message: string, history: HistoryItem[]) {
  const model = process.env.AION_GATEWAY_MODEL ?? "openai/gpt-5.4"
  const result = await generateText({
    model,
    system: AION_SYSTEM,
    messages: [
      ...history.slice(-12).map((item) => ({ role: item.role, content: item.content })),
      { role: "user" as const, content: message },
    ],
  })

  return Response.json({
    reply: result.text,
    responseId: null,
    model,
    runtime: "vercel-ai-gateway-oidc",
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
        return await runGateway(message, priorHistory)
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

    const payload: Record<string, unknown> = {
      model: process.env.AION_MODEL ?? "gpt-5.4",
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

    return Response.json({
      reply,
      responseId: data.id ?? null,
      model: process.env.AION_MODEL ?? "gpt-5.4",
      runtime: "openai-responses-v1",
    })
  } catch (err) {
    console.error("[AION] chat route error:", err instanceof Error ? err.message : String(err))
    return Response.json(
      { error: "AION encountered an unexpected runtime error.", code: "AION_RUNTIME_ERROR" },
      { status: 500 },
    )
  }
}
