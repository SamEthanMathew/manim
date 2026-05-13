import { createClient } from "@supabase/supabase-js";

/**
 * Service-role client. Bypasses RLS.
 * Only use in server-side API routes for trusted operations
 * (e.g., creating job rows, encrypting BYOK keys before insert).
 *
 * NEVER expose to the browser.
 */
export function createSupabaseAdminClient() {
  if (typeof window !== "undefined") {
    throw new Error("createSupabaseAdminClient cannot be called in the browser");
  }
  return createClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.SUPABASE_SERVICE_ROLE_KEY!,
    { auth: { autoRefreshToken: false, persistSession: false } },
  );
}
