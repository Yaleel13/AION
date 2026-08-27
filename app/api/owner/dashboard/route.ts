import { NextResponse } from "next/server"

function backendBase() {
  return process.env.AION_API_BASE?.replace(/\/$/, "") || "http://127.0.0.1:8000"
}

function ownerHeaders() {
  const token = process.env.AION_OWNER_TOKEN
  if (!token) {
    return null
  }
  return {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
  }
}

export async function GET() {
  const headers = ownerHeaders()
  if (!headers) {
    return NextResponse.json(
      {
        error:
          "AION_OWNER_TOKEN is not configured in the Next.js server environment",
      },
      { status: 503 }
    )
  }
  try {
    const res = await fetch(`${backendBase()}/owner/dashboard`, {
      headers,
      cache: "no-store",
    })
    const data = await res.json()
    return NextResponse.json(data, { status: res.status })
  } catch (err) {
    return NextResponse.json(
      {
        error:
          err instanceof Error
            ? `Backend unreachable: ${err.message}`
            : "Backend unreachable",
        hint: "Start FastAPI (python run.py) and set AION_API_BASE / AION_OWNER_TOKEN",
      },
      { status: 502 }
    )
  }
}
