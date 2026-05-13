"use client";
import { useState } from "react";
import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  const supabase = createSupabaseBrowserClient();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("sending");
    setError(null);

    const { error } = await supabase.auth.signInWithOtp({
      email,
      options: {
        emailRedirectTo: `${window.location.origin}/dashboard`,
      },
    });

    if (error) {
      setStatus("error");
      setError(error.message);
    } else {
      setStatus("sent");
    }
  }

  async function handleGoogle() {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: {
        redirectTo: `${window.location.origin}/dashboard`,
      },
    });
  }

  return (
    <main className="min-h-screen flex items-center justify-center px-6">
      <div className="w-full max-w-sm space-y-8">
        <h1 className="text-3xl font-bold text-center">Sign in to manim</h1>

        <form onSubmit={handleSubmit} className="space-y-4">
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
            className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-md focus:border-accent-blue focus:outline-none"
          />
          <button
            type="submit"
            disabled={status === "sending"}
            className="w-full px-4 py-3 bg-accent-blue rounded-md font-medium hover:opacity-90 disabled:opacity-50"
          >
            {status === "sending" ? "Sending…" : "Send magic link"}
          </button>
        </form>

        <div className="flex items-center gap-3 text-xs text-gray-500">
          <div className="flex-1 border-t border-gray-800" />
          <span>OR</span>
          <div className="flex-1 border-t border-gray-800" />
        </div>

        <button
          onClick={handleGoogle}
          className="w-full px-4 py-3 border border-gray-700 rounded-md font-medium hover:bg-gray-800"
        >
          Continue with Google
        </button>

        {status === "sent" && (
          <p className="text-sm text-accent-green text-center">
            Check your email for the magic link.
          </p>
        )}
        {error && <p className="text-sm text-red-400 text-center">{error}</p>}
      </div>
    </main>
  );
}
