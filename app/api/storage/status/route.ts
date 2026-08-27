import { createClient } from "@/utils/supabase/server";
import { NextResponse } from "next/server";

export const dynamic = "force-dynamic";

/**
 * Connectivity check against the dedicated AION Supabase project.
 * Reads the public ``aion_storage_status`` view (not operational secrets).
 */
export async function GET() {
  try {
    const supabase = await createClient();
    const { data, error } = await supabase
      .from("aion_storage_status")
      .select("*")
      .limit(1)
      .maybeSingle();

    if (error) {
      return NextResponse.json(
        {
          ok: false,
          backend: "supabase",
          error: error.message,
          hint: "Confirm NEXT_PUBLIC_SUPABASE_URL / PUBLISHABLE_KEY and that view public.aion_storage_status exists.",
        },
        { status: 503 },
      );
    }

    return NextResponse.json({
      ok: true,
      backend: "supabase",
      status: data,
    });
  } catch (exc) {
    return NextResponse.json(
      {
        ok: false,
        backend: "supabase",
        error: exc instanceof Error ? exc.message : String(exc),
      },
      { status: 500 },
    );
  }
}
