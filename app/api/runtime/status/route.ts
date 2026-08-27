import { NextResponse } from "next/server"

export const dynamic = "force-dynamic"

function backendBase() {
  return process.env.AION_API_BASE?.replace(/\/$/, "") || "http://127.0.0.1:8000"
}

/**
 * Proxies FastAPI GET /runtime/status — truthful gates, not Boardroom fixtures.
 */
export async function GET() {
  try {
    const res = await fetch(`${backendBase()}/runtime/status`, {
      cache: "no-store",
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (err) {
    return NextResponse.json(
      {
        ok: false,
        fixture: false,
        source: "runtime_status_proxy",
        error:
          err instanceof Error
            ? `Backend unreachable: ${err.message}`
            : "Backend unreachable",
        hint: "Start FastAPI (python run.py) and set AION_API_BASE if needed",
      },
      { status: 502 },
    )
  }
}
