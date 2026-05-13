"use client";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { createSupabaseBrowserClient } from "@/lib/supabase/browser";

export default function UploadPage() {
  const router = useRouter();
  const supabase = createSupabaseBrowserClient();

  const [file, setFile] = useState<File | null>(null);
  const [duration, setDuration] = useState(600);
  const [tone, setTone] = useState<"balanced" | "formal" | "playful" | "technical">("balanced");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit() {
    if (!file) return;
    setBusy(true);
    setError(null);

    try {
      // 1. Upload PDF to Supabase Storage at <user_id>/<uuid>.pdf
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) throw new Error("Not signed in");

      const uploadName = `${user.id}/${crypto.randomUUID()}.pdf`;
      const { error: upErr } = await supabase.storage
        .from("pdfs")
        .upload(uploadName, file, { contentType: "application/pdf" });
      if (upErr) throw upErr;

      // 2. POST to API to create job + spawn pipeline
      const res = await fetch("/api/jobs", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          pdf_storage_path: uploadName,
          target_duration_sec: duration,
          tone_hint: tone,
        }),
      });
      if (!res.ok) throw new Error(await res.text());
      const { id } = await res.json();

      router.push(`/jobs/${id}`);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="min-h-screen px-6 py-12 max-w-2xl mx-auto">
      <h1 className="text-2xl font-semibold mb-2">Upload a PDF</h1>
      <p className="text-gray-400 mb-8 text-sm">
        Max 50 pages. Academic content works best. You&apos;ll review the generated script before
        rendering starts.
      </p>

      <div className="space-y-6">
        <div>
          <label className="block text-sm mb-2">PDF</label>
          <input
            type="file"
            accept="application/pdf"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-md"
          />
        </div>

        <div>
          <label className="block text-sm mb-2">Target duration</label>
          <select
            value={duration}
            onChange={(e) => setDuration(parseInt(e.target.value, 10))}
            className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-md"
          >
            <option value={300}>5 minutes</option>
            <option value={600}>10 minutes</option>
            <option value={900}>15 minutes</option>
          </select>
        </div>

        <div>
          <label className="block text-sm mb-2">Tone</label>
          <select
            value={tone}
            onChange={(e) => setTone(e.target.value as typeof tone)}
            className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-md"
          >
            <option value="balanced">Balanced (default)</option>
            <option value="formal">Formal</option>
            <option value="playful">Playful</option>
            <option value="technical">Technical</option>
          </select>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <button
          onClick={submit}
          disabled={!file || busy}
          className="w-full px-6 py-3 bg-accent-blue rounded-md font-medium hover:opacity-90 disabled:opacity-50"
        >
          {busy ? "Uploading…" : "Start"}
        </button>
      </div>
    </main>
  );
}
