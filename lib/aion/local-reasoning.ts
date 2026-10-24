export type LocalHistoryItem = { role: "user" | "assistant"; content: string }

type OllamaChatResponse = {
  model?: string
  message?: { role?: string; content?: string }
  done?: boolean
  error?: string
}

export type LocalReasoningResult = {
  reply: string
  responseId: null
  model: string
  runtime: "ollama-local"
}

const DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
const DEFAULT_LOCAL_MODEL = "aion:latest"
const DEFAULT_LOCAL_CONTEXT = 4096
const DEFAULT_LOCAL_TIMEOUT_MS = 120_000

function positiveInt(value: string | undefined, fallback: number): number {
  if (!value) return fallback
  const parsed = Number.parseInt(value, 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback
}

function ollamaUrl(): string {
  return (process.env.AION_OLLAMA_URL ?? DEFAULT_OLLAMA_URL).trim().replace(/\/+$/, "")
}

export function localModel(): string {
  return process.env.AION_LOCAL_MODEL?.trim() || DEFAULT_LOCAL_MODEL
}

export function localRuntimeEnabled(): boolean {
  return (process.env.AION_RUNTIME_MODE ?? "").trim().toLowerCase() === "local"
}

export function cloudFallbackConfigured(): boolean {
  return Boolean(
    process.env.OPENAI_API_KEY ||
      process.env.VERCEL ||
      process.env.AION_GATEWAY_MODEL ||
      process.env.AION_GATEWAY_FALLBACK_MODEL ||
      process.env.AION_GATEWAY_FALLBACK_MODELS,
  )
}

export async function generateLocalReply(args: {
  message: string
  history: LocalHistoryItem[]
  systemInstructions: string
}): Promise<LocalReasoningResult> {
  const model = localModel()
  const context = positiveInt(process.env.AION_LOCAL_CONTEXT, DEFAULT_LOCAL_CONTEXT)
  const timeoutMs = positiveInt(process.env.AION_OLLAMA_TIMEOUT_MS, DEFAULT_LOCAL_TIMEOUT_MS)
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)

  try {
    const response = await fetch(`${ollamaUrl()}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        model,
        messages: [
          { role: "system", content: args.systemInstructions },
          ...args.history.slice(-12),
          { role: "user", content: args.message },
        ],
        stream: false,
        keep_alive: "30m",
        options: {
          num_ctx: context,
          temperature: 0.4,
        },
      }),
      cache: "no-store",
      signal: controller.signal,
    })

    const data = (await response.json()) as OllamaChatResponse
    if (!response.ok) {
      throw new Error(data.error || `Ollama returned HTTP ${response.status}`)
    }

    const reply = data.message?.content?.trim()
    if (!reply) throw new Error("Ollama returned no assistant text")

    return {
      reply,
      responseId: null,
      model: data.model?.trim() || model,
      runtime: "ollama-local",
    }
  } finally {
    clearTimeout(timeout)
  }
}
