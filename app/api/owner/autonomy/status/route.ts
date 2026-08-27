import { NextResponse } from "next/server"

export const runtime = "nodejs"
export const dynamic = "force-dynamic"

function backendBase() {
  return (process.env.AION_API_BASE || "http://127.0.0.1:8000").replace(/\/$/, "")
}

function ownerHeaders() {
  const token = process.env.AION_OWNER_TOKEN
  if (!token) return null
  return { Authorization: `Bearer ${token}` }
}

export async function GET() {
  const headers = ownerHeaders()
  if (!headers) {
    return NextResponse.json(
      { error: "AION_OWNER_TOKEN is not configured on the Next.js server" },
      { status: 503 }
    )
  }
  try {
    const res = await fetch(`${backendBase()}/owner/autonomy/status`, {
      headers,
      cache: "no-store",
    })
    const json = await res.json()
    return NextResponse.json(json, { status: res.status })
  } catch (err) {
    return NextResponse.json(
      {
        error: err instanceof Error ? err.message : "Upstream unreachable",
        hint: "Start FastAPI (python run.py) and set AION_API_BASE / AION_OWNER_TOKEN",
      },
      { status: 502 }
    )
  }
}
