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
  runtime: "ollama-local" | "aion-local-self-model"
}

const DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
const DEFAULT_LOCAL_MODEL = "aion:latest"
const DEFAULT_LOCAL_CONTEXT = 4096
const DEFAULT_LOCAL_TIMEOUT_MS = 120_000

const LOCAL_OS_CAPABILITY_REPLY = `I'm AION, the operating intelligence for this local AION OS environment.

Right now I can:
- Reason locally through Ollama using the configured AION model without requiring an API key.
- Remember conversations through durable local memory.
- Hear you through the EMEET microphone, transcribe locally with whisper.cpp, reason locally, speak with Piper, and play the reply through this machine's speakers.
- Inspect this machine through controlled capabilities for system information, storage, memory, and running processes.
- Inspect Git and this project with git status/diff plus project inspect, test, lint, and build actions.
- Inspect local audio, camera, and media runtime availability.
- Open the controlled Terminal workspace and use approved typed actions rather than an unrestricted shell.
- Use the owner-only Boardroom for private strategy and oversight.

My current limits are deliberate:
- I do not have arbitrary shell access, sudo, or root escalation.
- I do not accept caller-supplied commands, arguments, device paths, or shell fragments through the local executor.
- Camera devices can be inventoried, but general visual understanding is not operational yet.
- Email, SMS, and phone calling are not connected yet.
- I will not claim that I researched the web, deployed something, sent a message, published, purchased, or changed an external system unless a connected tool actually confirms it.

So I'm more than a generic conversational assistant: I'm the local reasoning, memory, voice, and controlled-execution layer of AION OS, with owner control kept above automation.`

const LOCAL_OS_CAPABILITY_CONTEXT = `Current AION OS runtime capabilities on this machine:

Operational now:
- Local reasoning through Ollama using the configured AION model. Local mode does not require API keys.
- Durable local conversation memory stored by AION's local memory service.
- Local voice conversation: EMEET microphone capture -> whisper.cpp speech recognition -> AION local reasoning -> Piper speech synthesis -> local speaker playback. Voice is explicit one-shot capture, not continuous background listening.
- Controlled local execution through a fixed typed capability registry. Arbitrary shell commands are not enabled.
- System inspection capabilities: system.info, system.storage, system.memory, system.processes.
- Media inspection capabilities: media.audio.inputs, media.camera.inputs, media.runtime.
- Voice capabilities: media.voice.listen and media.voice.ask.
- Git/project capabilities: git.status, git.diff, project.inspect, project.test, project.lint, project.build.
- Owner-only Boardroom interface for private strategy and oversight.
- A controlled Terminal workspace that routes through approved local capabilities rather than unrestricted shell access.

Current limits / not yet connected:
- No sudo or root escalation.
- No arbitrary caller-supplied commands, arguments, paths, or shell fragments.
- Camera devices can be inventoried, but general vision understanding is not yet an operational AION capability.
- Email, SMS, and phone calling are not connected unless a provider is explicitly configured later.
- Do not claim that web research, deployment, messaging, purchases, publishing, or other external actions occurred unless a connected tool actually confirms them.

Identity and self-description rule:
When the user asks what you are, what you can do, what your capabilities are, or what AION OS can do, answer from this actual runtime state. Speak as AION in first person when natural. Do not fall back to generic chatbot/AI-assistant boilerplate such as "I answer questions and generate text." Distinguish what is operational now from what is planned, gated, unavailable, or not connected.`

const SELF_CAPABILITY_PATTERNS = [
  /\bwhat (?:are|is) (?:your|aion(?: os)?(?:'s)?) capabilities\b/i,
  /\bwhat can you do\b/i,
  /\bwhat can aion(?: os)? do\b/i,
  /\bwhat are you capable of\b/i,
  /\bhow can you help me\b/i,
  /\btell me (?:about )?your capabilities\b/i,
]

function isSelfCapabilityQuestion(message: string): boolean {
  const normalized = message.trim()
  return SELF_CAPABILITY_PATTERNS.some((pattern) => pattern.test(normalized))
}

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
  const explicitlyAllowed = ["1", "true", "yes", "on"].includes(
    (process.env.AION_ALLOW_CLOUD_FALLBACK ?? "").trim().toLowerCase(),
  )
  if (!explicitlyAllowed) return false

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

  if (isSelfCapabilityQuestion(args.message)) {
    return {
      reply: LOCAL_OS_CAPABILITY_REPLY,
      responseId: null,
      model,
      runtime: "aion-local-self-model",
    }
  }

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
          {
            role: "system",
            content: `${args.systemInstructions}\n\n${LOCAL_OS_CAPABILITY_CONTEXT}`,
          },
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
