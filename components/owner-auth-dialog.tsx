"use client"

import { FormEvent, useEffect, useState } from "react"

export function OwnerAuthDialog({ open, onClose, onAuthenticated }: { open: boolean; onClose: () => void; onAuthenticated: () => void }) {
  const [token, setToken] = useState("")
  const [configured, setConfigured] = useState<boolean | null>(null)
  const [authenticated, setAuthenticated] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    if (!open) return
    let cancelled = false
    void fetch("/api/aion/owner-session", { cache: "no-store" })
      .then((res) => res.json())
      .then((data) => {
        if (cancelled) return
        setConfigured(Boolean(data.configured))
        setAuthenticated(Boolean(data.authenticated))
        if (data.authenticated) onAuthenticated()
      })
      .catch(() => {
        if (!cancelled) setError("Owner authentication status could not be loaded.")
      })
    return () => {
      cancelled = true
    }
  }, [open, onAuthenticated])

  if (!open) return null

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const response = await fetch("/api/aion/owner-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      })
      const data = await response.json()
      if (!response.ok || !data.authenticated) {
        throw new Error(data.error || "Owner authentication failed.")
      }
      setToken("")
      setAuthenticated(true)
      onAuthenticated()
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Owner authentication failed.")
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/55 px-4 backdrop-blur-sm" role="dialog" aria-modal="true" aria-labelledby="owner-auth-title">
      <div className="w-full max-w-md rounded-2xl border border-border/70 bg-background p-6 shadow-2xl">
        <div className="mb-5">
          <p className="text-xs uppercase tracking-[0.2em] text-muted-foreground">Owner Access</p>
          <h2 id="owner-auth-title" className="mt-1 text-xl font-semibold text-foreground">Unlock the Boardroom</h2>
          <p className="mt-2 text-sm text-muted-foreground">
            Enter the AION owner token. It is exchanged for a secure HttpOnly owner session and is not stored in the browser.
          </p>
        </div>

        {configured === false ? (
          <p className="rounded-xl border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            Owner authentication is not configured on this deployment.
          </p>
        ) : authenticated ? (
          <p className="rounded-xl border border-border bg-muted/40 p-3 text-sm text-foreground">Owner session is active.</p>
        ) : (
          <form onSubmit={submit} className="space-y-4">
            <label className="block text-sm font-medium text-foreground" htmlFor="owner-token">Owner token</label>
            <input
              id="owner-token"
              type="password"
              autoComplete="current-password"
              value={token}
              onChange={(event) => setToken(event.target.value)}
              className="w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm text-foreground outline-none ring-offset-background focus:ring-2 focus:ring-violet"
              placeholder="Enter owner token"
              required
            />
            {error && <p className="text-sm text-destructive">{error}</p>}
            <button
              type="submit"
              disabled={submitting || !token.trim()}
              className="w-full rounded-xl bg-foreground px-4 py-2.5 text-sm font-medium text-background transition-opacity disabled:opacity-50"
            >
              {submitting ? "Unlocking…" : "Unlock Owner Access"}
            </button>
          </form>
        )}

        <button type="button" onClick={onClose} className="mt-4 w-full rounded-xl px-4 py-2 text-sm text-muted-foreground hover:bg-muted">
          Close
        </button>
      </div>
    </div>
  )
}
