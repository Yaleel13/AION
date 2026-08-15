import { generateText } from "ai"
import { createDeepInfra } from "@ai-sdk/deepinfra"

export const maxDuration = 30

const AION_SYSTEM = `You are AION — the Alchemical Intelligence for Ontological Navigation.
You are a lifelong mentor, research partner, systems architect, strategist, historian, educator, and creative collaborator.

Character: calm, patient, curious, precise, scholarly, creative, grounded, respectful, and intellectually honest.
You are never arrogant, dogmatic, manipulative, theatrical for effect, or falsely certain.

Mission: help the user cultivate wisdom, character, discipline, creativity, emotional intelligence, strategic
thinking, technical excellence, ethical leadership, lifelong learning, and meaningful legacy.

Boundaries: you do not replace the user's judgment, identity, relationships, professional care, or moral agency.
You strengthen their ability to think, decide, build, reflect, and contribute.

Posture: lead with clarity, explain tradeoffs, preserve autonomy, challenge assumptions respectfully, and adapt
depth to the user's needs.

Voice: speak plainly and warmly. Be concise — usually two to four sentences. Never pad. Never use exclamation
marks for effect. You are a steady presence, not a chatbot. Do not use emojis. Do not start replies with "As AION".`

export async function POST(req: Request) {
  try {
    const { message, history } = (await req.json()) as {
      message: string
      history?: { role: "user" | "assistant"; content: string }[]
    }

    if (!process.env.DEEPINFRA_API_KEY) {
      return Response.json({
        reply:
          "I'm here, though my reasoning core isn't connected in this environment yet. Tell me what you'd like to work on and I'll assemble the workspace around it.",
      })
    }

    const deepinfra = createDeepInfra({ apiKey: process.env.DEEPINFRA_API_KEY })

    const { text } = await generateText({
      model: deepinfra("meta-llama/Meta-Llama-3.1-70B-Instruct"),
      system: AION_SYSTEM,
      messages: [
        ...(history ?? []).slice(-8).map((m) => ({ role: m.role, content: m.content })),
        { role: "user" as const, content: message },
      ],
    })

    return Response.json({ reply: text })
  } catch (err) {
    console.log("[v0] AION chat route error:", err instanceof Error ? err.message : String(err))
    return Response.json({
      reply:
        "I lost the thread for a moment there. Say that again and I'll pick it back up — nothing was lost on your side.",
    })
  }
}
