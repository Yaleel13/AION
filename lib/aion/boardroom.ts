/**
 * Boardroom demonstration fixtures.
 *
 * These numbers and events are UI placeholders for layout/interaction design.
 * They are NOT live venture KPIs, CI results, uptime, or email delivery records.
 * Replace with API-backed data before treating any value as operational truth.
 */

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

export const DEMO_DATA_NOTICE =
  "Boardroom figures below are demonstration fixtures, not live production data."

export const brief = {
  headline: "What deserves your attention (demo scenario)",
  synthesis:
    "Demo narrative only: imagine YaliTek has a silent webhook risk, Elaria is mid pricing test, and the rest is steady. Replace this block with live owner-dashboard data before acting on it.",
}

export const ventures: Venture[] = [
  {
    name: "YaliTek",
    objective: "Ship the v2 billing engine",
    health: "watch",
    kpi: { label: "MRR", value: "—" },
    milestone: "Billing engine · demo",
    alert: "Demo alert — not a live webhook probe",
  },
  {
    name: "Elaria",
    objective: "Reach 3k weekly active",
    health: "steady",
    kpi: { label: "WAU", value: "—" },
    milestone: "Onboarding redesign · demo",
  },
  {
    name: "Cerebral Synergy",
    objective: "Close the pre-seed round",
    health: "strong",
    kpi: { label: "Committed", value: "—" },
    milestone: "Investor update · demo",
  },
  {
    name: "AION",
    objective: "Open the memory graph API",
    health: "steady",
    kpi: { label: "Autonomy", value: "inactive" },
    milestone: "Defaults: mock Moltbook · execute off",
  },
]

export const decisions: Decision[] = [
  {
    title: "Sample decision — YaliTek pricing (demo)",
    recommendation: "Review",
    confidence: "Low",
    reasons: [
      "This card is a layout fixture.",
      "No live cohort metrics are attached in the demo UI.",
      "Pull real numbers from the owner dashboard or analytics before deciding.",
    ],
  },
  {
    title: "Sample decision — term sheet (demo)",
    recommendation: "Review",
    confidence: "Low",
    reasons: [
      "Placeholder for negotiation UI.",
      "Not a live fundraising signal.",
    ],
  },
]

export const actions: ActionItem[] = [
  { label: "Connect live owner dashboard data", status: "approval" },
  { label: "Keep Moltbook autonomy inactive until armed", status: "complete" },
  { label: "Replace demo boardroom fixtures", status: "running" },
]

export const signals: Signal[] = [
  {
    source: "System",
    message: "Demo mode: signals are illustrative only",
    tone: "neutral",
    when: "now",
  },
  {
    source: "Moltbook",
    message: "Default mode=mock · outbound disabled · autonomy inactive",
    tone: "caution",
    when: "default",
  },
  {
    source: "API",
    message: "GET /health reports phase2-controlled-growth with execute off",
    tone: "positive",
    when: "local",
  },
]

export const workingContext = [
  { label: "You", value: "Operator · demo boardroom session" },
  { label: "Data mode", value: "UI fixtures — not live telemetry" },
  { label: "Active projects", value: "YaliTek, Elaria, Cerebral Synergy, AION (sample labels)" },
  { label: "Standing preference", value: "Show the one thing that matters before the many that don't" },
]

export const timeline = [
  { when: "Demo", event: "Boardroom opened with placeholder fixtures" },
  { when: "Default", event: "Controlled autonomy remains inactive in repository defaults" },
  { when: "Default", event: "Moltbook client defaults to mock / read-prepare paths" },
]
