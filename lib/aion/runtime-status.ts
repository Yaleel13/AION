/** Typed contract for GET /api/runtime/status ← FastAPI GET /runtime/status. */

export type RuntimeStatus = {
  ok: boolean
  source: string
  fixture: boolean
  storage: {
    backend: string
    configured: boolean
    schema: string | null
    detail: string | null
  }
    moltbook: {
    configured: boolean
    mode: string | null
    api_key_present: boolean
    outbound_enabled: boolean
    execute_enabled: boolean
    controlled_outbound_ready?: boolean
    phase: string
    error?: string
  }
  autonomy: {
    mode: string
    dry_run: boolean
    live_writes_enabled: boolean
    experiment_active: boolean
    default: string
  }
  kill_switch: {
    engaged: boolean
    reason?: string
    engaged_at?: string | null
  }
  paper_market_data: {
    price_mode: string
    live_trading: boolean
    note: string
  }
  providers: {
    openai_configured: boolean
    gemini_configured: boolean
    vercel_ai_gateway_fallback_eligible?: boolean
  }
  operations?: {
    database_url_configured: boolean
    owner_token_configured: boolean
    cron_secret_configured: boolean
    terminal_executor_connected: boolean
    terminal_executor_mode: string | null
    arbitrary_terminal_commands_enabled: boolean
  }
  safety: {
    moltbook_outbound_default: boolean
    moltbook_execute_default?: boolean
    owner_approval_required_for_moltbook_write?: boolean
    autonomy_default: string
    autonomy_dry_run_default: boolean
    paper_is_not_live_trading?: boolean
  }
  error?: string
  hint?: string
}

export async function fetchRuntimeStatus(): Promise<RuntimeStatus | null> {
  try {
    const res = await fetch("/api/runtime/status", { cache: "no-store" })
    return (await res.json()) as RuntimeStatus
  } catch {
    return null
  }
}
