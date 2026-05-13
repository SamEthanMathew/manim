/**
 * Auto-anonymous sign-in helper.
 *
 * Called on first page load. If there's no existing session, silently
 * signs the visitor in as an anonymous user. Supabase issues them a
 * user_id that lets RLS, BYOK encryption, and job ownership all work
 * without the user ever seeing a signup form.
 */
import { createSupabaseBrowserClient } from "./browser";

export async function ensureAnonymousSession() {
  const supabase = createSupabaseBrowserClient();
  const { data: { session } } = await supabase.auth.getSession();
  if (session) return session;

  const { data, error } = await supabase.auth.signInAnonymously();
  if (error) {
    // Most likely cause: anonymous sign-ins not enabled in Supabase dashboard.
    console.error("Anonymous sign-in failed:", error.message);
    throw new Error(
      "This site can't create a session for you. " +
      "If you're the owner, enable Anonymous Sign-ins in Supabase Auth settings.",
    );
  }
  return data.session;
}
