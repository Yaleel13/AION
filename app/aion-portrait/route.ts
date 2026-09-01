import { AION_CANON_PORTRAIT } from "@/lib/aion/canon-portrait"

const PREFIX = "data:image/jpeg;base64,"

export const dynamic = "force-static"

export function GET() {
  const encoded = AION_CANON_PORTRAIT.startsWith(PREFIX)
    ? AION_CANON_PORTRAIT.slice(PREFIX.length)
    : AION_CANON_PORTRAIT

  const image = Buffer.from(encoded, "base64")

  return new Response(image, {
    headers: {
      "Content-Type": "image/jpeg",
      "Content-Length": String(image.byteLength),
      "Cache-Control": "public, max-age=3600, stale-while-revalidate=86400",
    },
  })
}
