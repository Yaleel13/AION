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
  effect?: "open-terminal" | "open-boardroom" | "close-boardroom" | "close-terminal" | "set-context"
  /** Context label to set when effect is set-context */
  context?: string
}

const ventures = ["YaliTek", "Elaria", "Cerebral Synergy", "AION"]

/**
 * Demo / fixture intent router — scripted widgets, not live ops data.
 * Stands in for /api/aion/chat. Real status: GET /api/runtime/status.
 */
export const MOCK_ROUTER_DATA_SOURCE = "demo_fixture" as const

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
    return { working: "thinking", reply: "Collapsing the Boardroom. I'm here.", effect: "close-boardroom" }
  }

  // Terminal
  if (has("terminal", "shell", "command line", "open it in the terminal")) {
    return {
      working: "executing",
      reply:
        "Opening a terminal session against Yaleel13/AION. I'll narrate what I run here as I go — nothing executes on production without your approval.",
      effect: "open-terminal",
      context: "AION Repository",
    }
  }

  // GitHub / repository
  if (has("repo", "github", "repository", "aion repo")) {
    return {
      working: "researching",
      reply: "Here's the current state of Yaleel13/AION.",
      context: "AION Repository",
      widgets: [
        {
          kind: "repository",
          repo: "Yaleel13/AION",
          branch: "main",
          lastCommit: {
            message: "Add epistemic intelligence skill layer",
            sha: "a3f19c2",
            author: "Yaleel13",
            when: "3h ago",
          },
          pullRequests: [
            { title: "Wire /api/aion/context to memory graph", number: 42, state: "review" },
            { title: "Terminal session transport", number: 41, state: "open" },
          ],
          ci: "passing",
        },
      ],
    }
  }

  // Deployment / fix a deployment
  if (has("deploy", "deployment", "vercel", "production status")) {
    return {
      working: "researching",
      reply: "Production is healthy. Here's the latest deployment for the AION service.",
      widgets: [
        {
          kind: "deployment",
          project: "aion-service",
          status: "ready",
          url: "aion.yalitek.com",
          commit: "a3f19c2",
          health: "All checks passing · p95 142ms",
        },
      ],
    }
  }

  // Repair / fix webhook (execution)
  if (has("fix", "repair", "webhook", "broken", "error")) {
    return {
      working: "executing",
      reply:
        "I've traced the failure to the Resend webhook handler. Here's the repair in progress — I'll hold before deploying.",
      widgets: [
        {
          kind: "execution",
          title: "Repairing /api/resend/webhook",
          steps: [
            { label: "Inspect repository", status: "done" },
            { label: "Identify handler", status: "done" },
            { label: "Compare production logs", status: "done" },
            { label: "Prepare patch", status: "working" },
            { label: "Deploy", status: "pending" },
          ],
        },
      ],
    }
  }

  // Research
  if (has("research", "look into", "investigate", "find out", "study")) {
    return {
      working: "researching",
      reply: "I've gathered the essentials. Here's what holds up to scrutiny.",
      widgets: [
        {
          kind: "research",
          topic: input.replace(/research/i, "").trim() || "Applied longevity protocols",
          summary:
            "The strongest evidence clusters around three interventions. The rest is promising but under-powered.",
          findings: [
            "Consistent aerobic base training shows the largest all-cause effect size.",
            "Time-restricted eating helps metabolic markers; effect on lifespan is unproven in humans.",
            "Most supplement claims rest on animal models that have not replicated in people.",
          ],
          confidence: "moderate",
          sources: [
            { title: "Nature Aging — meta-analysis", url: "https://www.nature.com/nataging/" },
            { title: "NIH longitudinal cohort", url: "https://www.nih.gov/" },
            { title: "Cell Metabolism review", url: "https://www.cell.com/cell-metabolism/home" },
          ],
        },
      ],
    }
  }

  // Email / text / call — communication layer
  if (has("email me", "email this", "send me", "email the")) {
    return {
      working: "executing",
      reply: "Prepared and sent. You'll also find it here.",
      widgets: [
        {
          kind: "communication",
          title: "Executive Strategy Report",
          channels: [
            { channel: "here", selected: true },
            { channel: "email", selected: true },
            { channel: "text", selected: false },
            { channel: "call", selected: false },
          ],
          sent: { channel: "Email", at: "7:42 AM" },
        },
      ],
    }
  }

  if (has("text me", "sms", "notify me")) {
    return {
      working: "thinking",
      reply: "Understood — I'll text you the moment the deployment reports healthy.",
      widgets: [
        {
          kind: "communication",
          title: "Deployment health watch",
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
      reply: "A call briefing is ready whenever you are. I'll walk you through it line by line.",
      widgets: [
        {
          kind: "communication",
          title: "Call briefing ready",
          channels: [
            { channel: "here", selected: false },
            { channel: "email", selected: false },
            { channel: "text", selected: false },
            { channel: "call", selected: true },
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
          "Here's the full breakdown. The three abilities I requested are read-and-act only — I can inspect files, run terminal commands and review logs. Anything that modifies production, deletes resources or spends money stays locked behind a separate, explicit approval each time.",
      }
    }
    return {
      working: "executing",
      reply:
        "Access granted for this session. I'll work within those bounds and pause for your explicit approval before anything irreversible.",
      context: "Session access · granted",
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

  // Review a business / venture / project widget
  if (has("review my business", "yalitek", "open yalitek", "work on", "project")) {
    const name = has("yalitek") ? "YaliTek" : ventures[0]
    return {
      working: "researching",
      reply: `Here's where ${name} stands right now.`,
      context: `Working in: ${name} Production`,
      widgets: [
        {
          kind: "project",
          name,
          state: "attention",
          services: ["GitHub", "Vercel", "Supabase", "Stripe"],
          lastDeployment: "Successful · 2h ago",
          activity: "6 commits today · 1 new customer",
          blockers: 1,
          nextAction: "Resolve the Resend webhook failure before the next release.",
        },
      ],
    }
  }

  // Attention / focus / what needs my attention — priority widgets
  if (has("attention", "focus", "what should i", "today", "priorities", "prepare me")) {
    return {
      working: "thinking",
      reply: "Three things deserve your attention this morning. In order.",
      widgets: [
        {
          kind: "project",
          name: "YaliTek",
          state: "attention",
          services: ["Vercel", "Resend"],
          lastDeployment: "Successful · 2h ago",
          activity: "1 blocker detected",
          blockers: 1,
          nextAction: "A webhook is failing silently. I can repair it now.",
        },
        {
          kind: "data",
          title: "Elaria — weekly signal",
          metrics: [
            { label: "Active users", value: "2,410", delta: "+12%", direction: "up" },
            { label: "Retention", value: "48%", delta: "+3pts", direction: "up" },
            { label: "MRR", value: "$8.2k", delta: "-2%", direction: "down" },
          ],
          series: [
            { label: "Mon", value: 40 },
            { label: "Tue", value: 52 },
            { label: "Wed", value: 49 },
            { label: "Thu", value: 63 },
            { label: "Fri", value: 71 },
            { label: "Sat", value: 68 },
            { label: "Sun", value: 80 },
          ],
        },
        {
          kind: "document",
          title: "Cerebral Synergy — investor update",
          type: "Draft · awaiting your review",
          excerpt:
            "Q3 momentum held. Two decisions are queued for you before this goes out to the syndicate.",
          updated: "Updated 18m ago",
        },
      ],
    }
  }

  // Logs — stream deployment / production logs into the terminal
  if (has("logs", "log output", "tail the log")) {
    return {
      working: "executing",
      reply:
        "Streaming the latest logs for aion-service. Everything's nominal except the Resend webhook warning — I've flagged it below in the terminal.",
      effect: "open-terminal",
      context: "aion-service · logs",
    }
  }

  // Document — open / preview / download a document
  if (has("open the document", "preview the document", "download the document", "read the document")) {
    const action = has("download the document")
      ? "queued for download"
      : has("preview the document")
        ? "opened in preview"
        : "opened"
    return {
      working: "thinking",
      reply: `Done — the document is ${action}. Say the word and I'll email or send it to whoever needs it.`,
      context: "Document · Cerebral Synergy investor update",
    }
  }

  // Fallback — AION stays conversational
  return {
    working: "thinking",
    reply:
      "I'm with you. Tell me what you want to work on — a business to review, a repository to open, research to run, or the Boardroom — and I'll assemble what we need.",
  }
}
