"use client"

import { useEffect, useState } from "react"
import { fetchRuntimeStatus, type RuntimeStatus } from "@/lib/aion/runtime-status"
import { cn } from "@/lib/utils"

/**
 * Banner fed only by GET /api/runtime/status — never Boardroom/fixture copy.
 */
export function RuntimeStatusBanner({ className }: { className?: string }) {
  const [status, setStatus] = useState<RuntimeStatus | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetchRuntimeStatus().then((data) => {
      if (cancelled) return
      if (!data?.ok) {
        setFailed(true)
        setStatus(data)
        return
      }
      setStatus(data)
      setFailed(false)
    })
    return () => {
      cancelled = true
    }
  }, [])

  if (!status && !failed) {
    return (
      <div
        className={cn(
          "border-b border-border/60 bg-surface/40 px-4 py-2 text-[0.7rem] text-muted-foreground",
          className,
        )}
      >
        Loading runtime status…
      </div>
    )
  }

  if (!status?.ok) {
    return (
      <div
        className={cn(
          "border-b border-caution/30 bg-caution/10 px-4 py-2 text-[0.7rem] text-caution",
          className,
        )}
      >
        Runtime status unavailable
        {status?.error ? ` — ${status.error}` : ""}. Demo surfaces below are fixtures.
      </div>
    )
  }

  const { storage, moltbook, autonomy, kill_switch, paper_market_data, providers } = status

  return (
    <div
      className={cn(
        "border-b border-border/60 bg-surface/50 px-4 py-2 text-[0.7rem] text-muted-foreground",
        className,
      )}
      data-source="runtime_status"
      data-fixture="false"
    >
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-x-4 gap-y-1">
        <span className="font-medium uppercase tracking-[0.14em] text-foreground/80">
          Runtime
        </span>
        <span>
          storage: {storage.backend}
          {storage.schema ? `/${storage.schema}` : ""}
          {storage.configured ? "" : " (misconfigured)"}
        </span>
        <span>
          moltbook: {moltbook.mode ?? "unset"}
          {moltbook.outbound_enabled ? " · outbound on" : " · outbound off"}
        </span>
        <span>
          autonomy: {autonomy.mode}
          {autonomy.dry_run ? " · dry-run" : " · dry-run off"}
          {autonomy.live_writes_enabled ? " · LIVE WRITES" : ""}
        </span>
        <span>kill-switch: {kill_switch.engaged ? "ENGAGED" : "off"}</span>
        <span title={paper_market_data.note}>
          paper: {paper_market_data.price_mode}
          {paper_market_data.live_trading ? " · LIVE TRADING" : " · not live trading"}
        </span>
        <span>
          providers: openai {providers.openai_configured ? "on" : "off"} · gemini{" "}
          {providers.gemini_configured ? "on" : "off"}
        </span>
      </div>
    </div>
  )
}
