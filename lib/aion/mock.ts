import type { PresenceState, WidgetData } from "./types"

export interface AionTurn {
  /** Presence state to hold while "thinking" before the reply lands */
  working: PresenceState
  /** AION's conversational reply */
  reply: string
  /** Render reply in serif (rare, philosophical / weighty statements) */
  serif?: boolean
  /** Contextual widgets summoned into the conversation */
  widgets?: WidgetData[]
  /** Side effects the shell should perform */
  effect?: "open-terminal" | "open-boardroom" | "close-terminal" | "set-context"
  /** Context label to set when effect is set-context */
  context?: string
}

const ventures = ["YaliTek", "Elaria", "Cerebral Synergy", "AION"]

/**
 * Demo intent router for the boardroom UI.
 * Scripted replies and widgets are illustrative fixtures only — they are not
 * live GitHub, Vercel, email, or production telemetry. Free-form chat should
 * go through /api/aion/chat when available.
 */
export function routeCommand(input: string): AionTurn {
  const q = input.toLowerCase().trim()

  const has = (...words: string[]) => words.some((w) => q.includes(w))

  // Boardroom
  if (has("boardroom", "war room", "command center")) {
    return {
      working: "thinking",
      reply:
        "Assembling the Boardroom. I'm bringing your ventures, open decisions and live signals into one field of view.",
      effect: "open-boardroom",
    }
  }

  if (has("close boardroom", "leave boardroom", "back to conversation", "exit boardroom")) {
    return { working: "thinking", reply: "Collapsing the Boardroom. I'm here.", effect: "close-boardroom" as never }
  }

  // Terminal
  if (has("terminal", "shell", "command line", "open it in the terminal")) {
    return {
      working: "executing",
      reply:
        "Opening a demonstration terminal for Yaleel13/AION. This UI script is illustrative — it does not run remote commands.",
      effect: "open-terminal",
      context: "AION Repository (demo)",
    }
  }

  // GitHub / repository
  if (has("repo", "github", "repository", "aion repo")) {
    return {
      working: "researching",
      reply:
        "Here's a demonstration repository card for Yaleel13/AION. Treat the commit/PR details as sample UI data unless I fetch them live.",
      context: "AION Repository (demo)",
      widgets: [
        {
          kind: "repository",
          repo: "Yaleel13/AION",
          branch: "main",
          lastCommit: {
            message: "Sample commit for boardroom demo",
            sha: "demo000",
            author: "Yaleel13",
            when: "demo",
          },
          pullRequests: [
            { title: "Sample PR — not a live GitHub item", number: 0, state: "open" },
          ],
          ci: "unknown",
        },
      ],
    }
  }

  // Deployment / fix a deployment
  if (has("deploy", "deployment", "vercel", "production status")) {
    return {
      working: "researching",
      reply:
        "I don't have live deployment telemetry in this scripted view. Here's a placeholder card so you can see how a status widget would look.",
      widgets: [
        {
          kind: "deployment",
          project: "aion-service",
          status: "ready",
          url: "demo.local",
          commit: "demo000",
          health: "Demo placeholder — not live production health",
        },
      ],
    }
  }

  // Repair / fix webhook (execution)
  if (has("fix", "repair", "webhook", "broken", "error")) {
    return {
      working: "executing",
      reply:
        "This is a demonstration repair checklist only. I have not inspected production logs or prepared a real patch.",
      widgets: [
        {
          kind: "execution",
          title: "Demo repair flow (not live)",
          steps: [
            { label: "Inspect repository", status: "pending" },
            { label: "Identify handler", status: "pending" },
            { label: "Compare production logs", status: "pending" },
            { label: "Prepare patch", status: "pending" },
            { label: "Deploy", status: "pending" },
          ],
        },
      ],
    }
  }

  // Research (demo card — not a live literature review)
  if (has("research", "look into", "investigate", "find out", "study")) {
    return {
      working: "researching",
      reply:
        "Here's a demonstration research card so you can see the layout. It is not a live literature review — ask in free-form chat when you want a real pass.",
      widgets: [
        {
          kind: "research",
          topic: input.replace(/research/i, "").trim() || "Sample research topic",
          summary:
            "Demo summary only. Replace with tool-backed findings before citing any claim.",
          findings: [
            "Fixture finding A — illustrative, not verified in this path.",
            "Fixture finding B — illustrative, not verified in this path.",
            "Fixture finding C — illustrative, not verified in this path.",
          ],
          confidence: "low",
          sources: [
            { title: "Source placeholder", url: "https://example.com" },
          ],
        },
      ],
    }
  }

  // Email / text / call — communication layer (demo only; no messages are sent)
  if (has("email me", "email this", "send me", "email the")) {
    return {
      working: "executing",
      reply:
        "I can draft that here. This demo path does not send email — connect a live mail tool before treating delivery as real.",
      widgets: [
        {
          kind: "communication",
          title: "Draft ready (not sent)",
          channels: [
            { channel: "here", selected: true },
            { channel: "email", selected: false },
            { channel: "text", selected: false },
            { channel: "call", selected: false },
          ],
        },
      ],
    }
  }

  if (has("text me", "sms", "notify me")) {
    return {
      working: "thinking",
      reply:
        "Noted. I don't have a live SMS channel in this demo UI, so I won't claim a text was sent.",
      widgets: [
        {
          kind: "communication",
          title: "Notification preference (demo)",
          channels: [
            { channel: "here", selected: false },
            { channel: "email", selected: false },
            { channel: "text", selected: true },
            { channel: "call", selected: false },
          ],
        },
      ],
    }
  }

  if (has("call me", "call briefing", "walk me through", "phone")) {
    return {
      working: "thinking",
      reply:
        "I can walk you through a briefing here in chat. This demo does not place phone calls.",
      widgets: [
        {
          kind: "communication",
          title: "Briefing in chat (demo)",
          channels: [
            { channel: "here", selected: true },
            { channel: "email", selected: false },
            { channel: "text", selected: false },
            { channel: "call", selected: false },
          ],
        },
      ],
    }
  }

  // Permission — grant / review requested access
  if (has("allow this session", "allow session", "grant access", "review the requested permissions")) {
    if (has("review the requested permissions")) {
      return {
        working: "thinking",
        reply:
          "In a live session I would request only scoped read/act abilities and keep production changes, deletions, and spend behind separate approval. This UI is still demonstration-only.",
      }
    }
    return {
      working: "executing",
      reply:
        "Demo acknowledgement only — this click does not grant real production credentials. Live access still requires an explicit owner-configured integration.",
      context: "Session access · demo",
    }
  }

  // Connect / link a project
  if (has("connect", "link", "authorize", "remote access", "allow access")) {
    return {
      working: "thinking",
      reply: "Before I touch anything, here's exactly what you'd be granting — and what still requires separate approval.",
      widgets: [
        {
          kind: "permission",
          target: "YaliTek production environment",
          abilities: ["Inspect files", "Run terminal commands", "Review logs"],
          elevated: ["Modify production", "Delete resources", "Purchase services"],
        },
      ],
    }
  }

  // Review a business / venture / project widget (demo scenario)
  if (has("review my business", "yalitek", "open yalitek", "work on", "project")) {
    const name = has("yalitek") ? "YaliTek" : ventures[0]
    return {
      working: "researching",
      reply: `Here's a demonstration project card for ${name}. It is sample UI data, not a live ops readout.`,
      context: `Demo context: ${name}`,
      widgets: [
        {
          kind: "project",
          name,
          state: "attention",
          services: ["GitHub", "Vercel", "Supabase", "Stripe"],
          lastDeployment: "Demo placeholder",
          activity: "Demo activity — not live",
          blockers: 0,
          nextAction: "Connect live project telemetry before acting on this card.",
        },
      ],
    }
  }

  // Attention / focus — demo priority widgets
  if (has("attention", "focus", "what should i", "today", "priorities", "prepare me")) {
    return {
      working: "thinking",
      reply:
        "This is a demonstration priority stack for layout only. It is not a live morning brief from production systems.",
      widgets: [
        {
          kind: "project",
          name: "YaliTek",
          state: "attention",
          services: ["Vercel", "Resend"],
          lastDeployment: "Demo placeholder",
          activity: "Demo blocker card",
          blockers: 0,
          nextAction: "Replace with owner-dashboard data before prioritizing real work.",
        },
        {
          kind: "data",
          title: "Elaria — demo metrics",
          metrics: [
            { label: "Active users", value: "—" },
            { label: "Retention", value: "—" },
            { label: "MRR", value: "—" },
          ],
          series: [
            { label: "Mon", value: 0 },
            { label: "Tue", value: 0 },
            { label: "Wed", value: 0 },
            { label: "Thu", value: 0 },
            { label: "Fri", value: 0 },
            { label: "Sat", value: 0 },
            { label: "Sun", value: 0 },
          ],
        },
        {
          kind: "document",
          title: "Sample document card",
          type: "Demo · not a live draft",
          excerpt: "Placeholder excerpt for boardroom document widgets.",
          updated: "Demo",
        },
      ],
    }
  }

  // Logs — open demo terminal only
  if (has("logs", "log output", "tail the log")) {
    return {
      working: "executing",
      reply:
        "Opening the demonstration terminal. It does not stream live production logs.",
      effect: "open-terminal",
      context: "demo terminal · not live logs",
    }
  }

  // Document — demo only
  if (has("open the document", "preview the document", "download the document", "read the document")) {
    return {
      working: "thinking",
      reply:
        "There is no live document attached in this demo path. Point me at a real file or draft when you want to work with one.",
      context: "Document · demo",
    }
  }

  // Fallback — AION stays conversational
  return {
    working: "thinking",
    reply:
      "I'm with you. Tell me what you want to work on — a business to review, a repository to open, research to run, or the Boardroom — and I'll assemble what we need.",
  }
}
