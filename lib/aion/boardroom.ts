/**
 * Demo / fixture Boardroom copy — not live telemetry.
 * Real gates come from GET /api/runtime/status.
 */
import { demoFact, type FactEnvelope } from "@/lib/aion/fact-envelope"

export const BOARDROOM_DATA_SOURCE = "demo_fixture" as const

export type Health = "strong" | "steady" | "watch" | "risk"

export interface Venture {
  name: string
  objective: string
  health: Health
  kpi: { label: string; value: string }
  milestone: string
  alert?: string
}

export interface Decision {
  title: string
  recommendation: string
  confidence: "High" | "Moderate" | "Low"
  reasons: string[]
}

export interface Signal {
  source: string
  message: string
  tone: "positive" | "caution" | "critical" | "neutral"
  when: string
}

export interface ActionItem {
  label: string
  status: "running" | "complete" | "approval"
}

export const brief: FactEnvelope<{ headline: string; synthesis: string }> = demoFact(
  {
    headline: "What deserves your attention",
    synthesis:
      "YaliTek has a silent webhook failure that will start dropping receipts within the day — it's the one thing worth doing first. Elaria's growth is real but MRR dipped 2% on a pricing test you can now conclude. Everything else is holding.",
  },
  { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "boardroom:brief" },
)

export const ventures: FactEnvelope<Venture>[] = [
  demoFact(
    {
      name: "YaliTek",
      objective: "Ship the v2 billing engine",
      health: "watch",
      kpi: { label: "MRR", value: "$21.4k" },
      milestone: "Billing engine · 80%",
      alert: "Resend webhook failing silently",
    },
    { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "venture:YaliTek" },
  ),
  demoFact(
    {
      name: "Elaria",
      objective: "Reach 3k weekly active",
      health: "steady",
      kpi: { label: "WAU", value: "2,410" },
      milestone: "Onboarding redesign · shipped",
    },
    { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "venture:Elaria" },
  ),
  demoFact(
    {
      name: "Cerebral Synergy",
      objective: "Close the pre-seed round",
      health: "strong",
      kpi: { label: "Committed", value: "$680k" },
      milestone: "Investor update · drafting",
    },
    { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "venture:Cerebral Synergy" },
  ),
  demoFact(
    {
      name: "AION",
      objective: "Open the memory graph API",
      health: "steady",
      kpi: { label: "Uptime", value: "99.98%" },
      milestone: "Context endpoint · in review",
    },
    { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "venture:AION" },
  ),
]

export const decisions: FactEnvelope<Decision>[] = [
  demoFact(
    {
      title: "Approve YaliTek pricing change",
      recommendation: "Approve",
      confidence: "High",
      reasons: [
        "Test cohort converted 14% better at the new tier.",
        "Churn was unchanged across the 6-week window.",
        "Downside is reversible within one billing cycle.",
      ],
    },
    { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "decision:pricing" },
  ),
  demoFact(
    {
      title: "Cerebral Synergy — accept lead term sheet",
      recommendation: "Negotiate",
      confidence: "Moderate",
      reasons: [
        "Valuation is fair but the board seat is unusual this early.",
        "A second party is likely to match within the week.",
      ],
    },
    { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "decision:term-sheet" },
  ),
]

export const actions: FactEnvelope<ActionItem>[] = [
  demoFact({ label: "Deploy AION context API", status: "running" }, { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "action:context-api" }),
  demoFact({ label: "Prepare Elaria market analysis", status: "complete" }, { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "action:elaria-analysis" }),
  demoFact({ label: "Repair YaliTek webhook", status: "approval" }, { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "action:webhook" }),
]

export const signals: FactEnvelope<Signal>[] = [
  demoFact(
    { source: "GitHub", message: "CI failed on Yaleel13/AION #41", tone: "critical", when: "12m" },
    { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "signal:github" },
  ),
  demoFact(
    { source: "Stripe", message: "New annual purchase · YaliTek · $2,400", tone: "positive", when: "34m" },
    { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "signal:stripe" },
  ),
  demoFact(
    { source: "Vercel", message: "aion-service deployed · healthy", tone: "positive", when: "1h" },
    { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "signal:vercel" },
  ),
  demoFact(
    { source: "Email", message: "Investor requested the updated deck", tone: "caution", when: "2h" },
    { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "signal:email" },
  ),
  demoFact(
    { source: "Research", message: "New paper matches your longevity thread", tone: "neutral", when: "3h" },
    { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "signal:research" },
  ),
]

export const workingContext: FactEnvelope<{ label: string; value: string }>[] = [
  demoFact({ label: "You", value: "Operator across 4 ventures · optimizing for durable focus" }, { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "context:you" }),
  demoFact({ label: "This week", value: "Billing reliability, the pre-seed close, Elaria retention" }, { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "context:week" }),
  demoFact({ label: "Active projects", value: "YaliTek, Elaria, Cerebral Synergy, AION" }, { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "context:projects" }),
  demoFact({ label: "Standing preference", value: "Show the one thing that matters before the many that don't" }, { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "context:preference" }),
]

export const timeline: FactEnvelope<{ when: string; event: string }>[] = [
  demoFact({ when: "Today · 7:42 AM", event: "AION delivered the Executive Strategy Report by email" }, { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "timeline:strategy-report" }),
  demoFact({ when: "Today · 7:15 AM", event: "Repaired the Elaria onboarding regression and deployed" }, { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "timeline:elaria-deploy" }),
  demoFact({ when: "Yesterday", event: "Drafted the Cerebral Synergy investor update" }, { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "timeline:investor-update" }),
  demoFact({ when: "Yesterday", event: "Ran the longevity research thread and saved 3 sources" }, { source: BOARDROOM_DATA_SOURCE, sourceObjectId: "timeline:research" }),
]
