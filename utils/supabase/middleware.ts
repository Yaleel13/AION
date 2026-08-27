import { createServerClient } from "@supabase/ssr";
import { type NextRequest, NextResponse } from "next/server";

function supabaseEnv() {
  const url = (process.env.NEXT_PUBLIC_SUPABASE_URL || "").trim();
  const key = (process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY || "").trim();
  return { url, key, configured: Boolean(url && key) };
}

/**
 * Refresh the Auth session cookies on each matched request.
 * If Supabase env is missing/invalid, pass through without crashing the edge
 * middleware (MIDDLEWARE_INVOCATION_FAILED).
 */
export async function updateSession(request: NextRequest) {
  const passthrough = NextResponse.next({
    request: {
      headers: request.headers,
    },
  });

  const { url, key, configured } = supabaseEnv();
  if (!configured) {
    return { supabase: null, response: passthrough };
  }

  let supabaseResponse = passthrough;

  try {
    const supabase = createServerClient(url, key, {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options),
          );
        },
      },
    });

    // Important: do not remove when configured — keeps the session fresh.
    await supabase.auth.getUser();

    return { supabase, response: supabaseResponse };
  } catch {
    // Never fail the whole site from session refresh errors.
    return { supabase: null, response: passthrough };
  }
}
