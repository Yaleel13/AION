import { NextResponse } from "next/server"

type CapabilityListResponse = {
  capabilities?: Array<{ name?: string }>
}

type LocalExecutorResponse = {
  ok?: boolean
  capability?: string
  stdout?: string
  error?: string
}

type VoiceTurnPayload = {
  ok?: boolean
  transcript?: string
  reply?: string
  reasoning_model?: string
  memory_session_id?: string
  history_messages?: number
  memory_saved?: boolean
  played?: boolean
  playback_error?: string | null
  network_required?: boolean
  continuous_listening?: boolean
  error?: string
}

const VOICE_CAPABILITY = "media.voice.ask"
const AVAILABILITY_TIMEOUT_MS = 2_500
const VOICE_TURN_TIMEOUT_MS = 300_000
const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "::1"])

function localRuntimeEnabled(): boolean {
  return (process.env.AION_RUNTIME_MODE ?? "").trim().toLowerCase() === "local"
}

function requestIsLocalAndSameOrigin(request: Request): boolean {
  try {
    const requestUrl = new URL(request.url)
    if (!LOOPBACK_HOSTS.has(requestUrl.hostname)) return false

    const origin = request.headers.get("origin")
    if (!origin) return true

    return new URL(origin).origin === requestUrl.origin
  } catch {
    return false
  }
}

function loopbackRuntimeOrigin(): string | null {
  const configured = (process.env.AION_RUNTIME_URL ?? "http://127.0.0.1:8000").trim()

  try {
    const parsed = new URL(configured)
    if (!["http:", "https:"].includes(parsed.protocol)) return null
    if (!LOOPBACK_HOSTS.has(parsed.hostname)) return null
    if (parsed.username || parsed.password || parsed.search || parsed.hash) return null
    if (parsed.pathname !== "/" && parsed.pathname !== "") return null
    return parsed.origin
  } catch {
    return null
  }
}

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(url, { ...init, cache: "no-store", signal: controller.signal })
  } finally {
    clearTimeout(timeout)
  }
}

export async function GET(request: Request) {
  if (!requestIsLocalAndSameOrigin(request)) {
    return NextResponse.json({ available: false, reason: "loopback-only" }, { status: 403 })
  }

  if (!localRuntimeEnabled()) {
    return NextResponse.json({ available: false, reason: "local-runtime-disabled" })
  }

  const runtimeOrigin = loopbackRuntimeOrigin()
  if (!runtimeOrigin) {
    return NextResponse.json({ available: false, reason: "invalid-local-runtime" })
  }

  try {
    const response = await fetchWithTimeout(
      `${runtimeOrigin}/local-executive/capabilities`,
      { method: "GET" },
      AVAILABILITY_TIMEOUT_MS,
    )
    if (!response.ok) {
      return NextResponse.json({ available: false, reason: "local-executive-unavailable" })
    }

    const data = (await response.json()) as CapabilityListResponse
    const available = data.capabilities?.some((item) => item.name === VOICE_CAPABILITY) ?? false
    return NextResponse.json({ available, mode: available ? "local-controlled" : null })
  } catch {
    return NextResponse.json({ available: false, reason: "local-executive-unreachable" })
  }
}

export async function POST(request: Request) {
  if (!requestIsLocalAndSameOrigin(request)) {
    return NextResponse.json({ error: "AION local voice is available only from the loopback interface." }, { status: 403 })
  }

  if (!localRuntimeEnabled()) {
    return NextResponse.json({ error: "Local voice is unavailable outside AION local mode." }, { status: 503 })
  }

  const runtimeOrigin = loopbackRuntimeOrigin()
  if (!runtimeOrigin) {
    return NextResponse.json({ error: "AION local runtime must use a loopback endpoint." }, { status: 503 })
  }

  try {
    const response = await fetchWithTimeout(
      `${runtimeOrigin}/local-executive/execute`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ capability: VOICE_CAPABILITY }),
      },
      VOICE_TURN_TIMEOUT_MS,
    )

    const executor = (await response.json()) as LocalExecutorResponse
    if (!response.ok || !executor.ok || executor.capability !== VOICE_CAPABILITY) {
      return NextResponse.json(
        { error: executor.error || "AION local voice capability failed." },
        { status: response.ok ? 502 : response.status },
      )
    }

    let voice: VoiceTurnPayload
    try {
      voice = JSON.parse(executor.stdout ?? "") as VoiceTurnPayload
    } catch {
      return NextResponse.json({ error: "AION local voice returned an invalid response." }, { status: 502 })
    }

    if (!voice.ok || !voice.transcript || !voice.reply) {
      return NextResponse.json(
        { error: voice.error || "AION local voice did not return a complete turn." },
        { status: 502 },
      )
    }

    return NextResponse.json({
      ok: true,
      transcript: voice.transcript,
      reply: voice.reply,
      reasoningModel: voice.reasoning_model ?? null,
      memorySessionId: voice.memory_session_id ?? null,
      historyMessages: voice.history_messages ?? 0,
      memorySaved: voice.memory_saved ?? false,
      played: voice.played ?? false,
      playbackError: voice.playback_error ?? null,
      networkRequired: voice.network_required ?? false,
      continuousListening: voice.continuous_listening ?? false,
    })
  } catch (error) {
    const detail = error instanceof Error && error.name === "AbortError"
      ? "AION local voice turn timed out."
      : "AION local voice runtime is unreachable."
    return NextResponse.json({ error: detail }, { status: 503 })
  }
}
