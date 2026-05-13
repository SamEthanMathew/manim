import { createBrowserClient } from "@supabase/ssr";

// Build-time placeholders so Next.js prerender doesn't throw when env vars
// aren't loaded. At runtime (Vercel) the real values from process.env take
// precedence; the placeholders are never reached.
const PLACEHOLDER_URL = "https://placeholder.supabase.co";
const PLACEHOLDER_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.placeholder";

export function createSupabaseBrowserClient() {
  return createBrowserClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL || PLACEHOLDER_URL,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || PLACEHOLDER_ANON_KEY,
  );
}
