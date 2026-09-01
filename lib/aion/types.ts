export type PresenceState =
  | "idle"
  | "listening"
  | "thinking"
  | "researching"
  | "executing"
  | "complete"

export type ProjectState = "production" | "building" | "attention" | "paused"

export type WidgetKind =
  | "research"
  | "project"
  | "repository"
  | "deployment"
  | "data"
  | "document"
  | "communication"
  | "execution"
  | "connection"
  | "permission"

export interface ResearchWidgetData {
  kind: "research"
  topic: string
  summary: string
  findings: string[]
  confidence: "low" | "moderate" | "high"
  sources: { title: string; url: string }[]
}

export interface ProjectWidgetData {
  kind: "project"
  name: string
  state: ProjectState
  services: string[]
  lastDeployment: string
  activity: string
  blockers: number
  nextAction: string
}

export interface RepositoryWidgetData {
  kind: "repository"
  repo: string
  branch: string
  lastCommit: { message: string; sha: string; author: string; when: string }
  pullRequests: { title: string; number: number; state: "open" | "review" }[]
  ci: "passing" | "failing" | "running"
}

export interface DeploymentWidgetData {
  kind: "deployment"
  project: string
  status: "ready" | "building" | "error"
  url: string
  commit: string
  health: string
}

export interface DataWidgetData {
  kind: "data"
  title: string
  metrics: { label: string; value: string; delta?: string; direction?: "up" | "down" }[]
  series: { label: string; value: number }[]
}

export interface DocumentWidgetData {
  kind: "document"
  title: string
  type: string
  excerpt: string
  updated: string
}

export interface CommunicationWidgetData {
  kind: "communication"
  title: string
  channels: { channel: "here" | "email" | "text" | "call"; selected: boolean }[]
  sent?: { channel: string; at: string }
}

export interface ExecutionStep {
  label: string
  status: "done" | "working" | "pending" | "blocked"
}

export interface ExecutionWidgetData {
  kind: "execution"
  title: string
  steps: ExecutionStep[]
}

export interface ConnectionWidgetData {
  kind: "connection"
  title: string
}

export interface PermissionWidgetData {
  kind: "permission"
  target: string
  abilities: string[]
  elevated: string[]
}

export type WidgetData =
  | ResearchWidgetData
  | ProjectWidgetData
  | RepositoryWidgetData
  | DeploymentWidgetData
  | DataWidgetData
  | DocumentWidgetData
  | CommunicationWidgetData
  | ExecutionWidgetData
  | ConnectionWidgetData
  | PermissionWidgetData

/** When set, widgets in this message are fixture data — not live provider telemetry. */
export type MessageDataSource = "demo_fixture" | "live"

export interface Message {
  id: string
  role: "user" | "aion"
  content: string
  widgets?: WidgetData[]
  serif?: boolean
  /** Provenance for widget payloads; defaults to live when omitted. */
  dataSource?: MessageDataSource
}

export type InterfaceMode = "conversation" | "terminal" | "boardroom"
