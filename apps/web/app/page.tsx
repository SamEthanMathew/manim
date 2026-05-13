"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ensureAnonymousSession } from "@/lib/supabase/anon";
import { createSupabaseBrowserClient } from "@/lib/supabase/browser";
import type { Job } from "@manim/shared";

export const dynamic = "force-dynamic";

type Tone = "balanced" | "formal" | "playful" | "technical";

export default function Home() {
  const router = useRouter();
  const supabase = createSupabaseBrowserClient();

  const [ready, setReady] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [hasKey, setHasKey] = useState<boolean | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [duration, setDuration] = useState(600);
  const [tone, setTone] = useState<Tone>("balanced");
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<Job[]>([]);

  // Sign in anonymously and check whether the user already has a BYOK key.
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        await ensureAnonymousSession();
        if (cancelled) return;
        setReady(true);
        await Promise.all([refreshKey(), refreshRecent()]);
      } catch (e) {
        if (!cancelled) setAuthError(e instanceof Error ? e.message : "Auth init failed");
      }
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function refreshKey() {
    const res = await fetch("/api/settings");
    if (res.ok) {
      const s = await res.json();
      setHasKey(Boolean(s.has_openai_key) || Boolean(s.has_anthropic_key));
    }
  }

  async function refreshRecent() {
    const { data } = await supabase
      .from("jobs")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(10);
    setRecent((data ?? []) as unknown as Job[]);
  }

  const startUpload = useCallback(async () => {
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      if (!hasKey) {
        setShowKeyModal(true);
        setBusy(false);
        return;
      }

      const { data: { user } } = await supabase.auth.getUser();
      if (!user) throw new Error("No session — refresh and try again.");

      const uploadName = `${user.id}/${crypto.randomUUID()}.pdf`;
      const { error: upErr } = await supabase.storage
        .from("pdfs")
        .upload(uploadName, file, { contentType: "application/pdf" });
      if (upErr) throw upErr;

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
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setBusy(false);
    }
  }, [file, hasKey, duration, tone, router, supabase]);

  if (authError) {
    return (
      <main className="min-h-screen flex items-center justify-center px-6">
        <p className="max-w-md text-center text-red-400 text-sm">{authError}</p>
      </main>
    );
  }
  if (!ready) {
    return (
      <main className="min-h-screen flex items-center justify-center">
        <p className="text-gray-500 text-sm">Starting…</p>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-6 py-12 max-w-3xl mx-auto">
      <header className="flex items-center justify-between mb-12">
        <h1 className="font-mono text-lg tracking-tight">manim</h1>
        <Link href="/settings" className="text-sm text-gray-400 hover:text-white">
          settings
        </Link>
      </header>

      <section className="space-y-3 mb-10">
        <h2 className="text-4xl md:text-5xl font-bold tracking-tight leading-tight">
          Upload a PDF.
          <br />
          Get a 3Blue1Brown-style video.
        </h2>
        <p className="text-gray-400 text-base">
          Drop a textbook chapter, paper, or lecture notes. We extract the math, plan a
          curriculum, write a script, generate Manim code per scene, and render the video.
        </p>
      </section>

      <section className="space-y-5">
        <FileDrop file={file} onFile={setFile} />

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="block text-xs uppercase tracking-wide text-gray-500 mb-1">
              Duration
            </label>
            <select
              value={duration}
              onChange={(e) => setDuration(parseInt(e.target.value, 10))}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-sm"
            >
              <option value={300}>5 minutes</option>
              <option value={600}>10 minutes</option>
              <option value={900}>15 minutes</option>
            </select>
          </div>
          <div>
            <label className="block text-xs uppercase tracking-wide text-gray-500 mb-1">
              Tone
            </label>
            <select
              value={tone}
              onChange={(e) => setTone(e.target.value as Tone)}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-sm"
            >
              <option value="balanced">Balanced</option>
              <option value="formal">Formal</option>
              <option value="playful">Playful</option>
              <option value="technical">Technical</option>
            </select>
          </div>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <button
          onClick={startUpload}
          disabled={!file || busy}
          className="w-full px-6 py-3 bg-accent-blue text-white rounded-md font-medium hover:opacity-90 disabled:opacity-40"
        >
          {busy ? "Uploading…" : "Generate video"}
        </button>

        <p className="text-xs text-gray-500 text-center">
          You&apos;ll be asked for an OpenAI or Anthropic API key on the first run. It&apos;s
          encrypted and used only to run your job — we never bill for tokens.
        </p>
      </section>

      {recent.length > 0 && (
        <section className="mt-16">
          <h3 className="text-xs uppercase tracking-wide text-gray-500 mb-3">Recent jobs</h3>
          <ul className="space-y-1">
            {recent.map((j) => (
              <li key={j.id}>
                <Link
                  href={`/jobs/${j.id}`}
                  className="flex justify-between items-center p-3 border border-gray-800 rounded hover:border-gray-700"
                >
                  <span className="font-mono text-xs text-gray-500">{j.id.slice(0, 8)}</span>
                  <span className="text-sm text-gray-300 flex-1 ml-4 truncate">
                    {j.pdf_storage_path.split("/").pop()}
                  </span>
                  <span className="text-xs px-2 py-0.5 rounded bg-gray-800">{j.status}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      )}

      {showKeyModal && (
        <KeyModal
          onClose={() => setShowKeyModal(false)}
          onSaved={async () => {
            setShowKeyModal(false);
            await refreshKey();
            void startUpload();
          }}
        />
      )}
    </main>
  );
}

// ─── File drop component ──────────────────────────────────────────────────────

function FileDrop({ file, onFile }: { file: File | null; onFile: (f: File | null) => void }) {
  const [hovering, setHovering] = useState(false);

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setHovering(false);
    const f = e.dataTransfer.files?.[0];
    if (f && f.type === "application/pdf") onFile(f);
  }

  return (
    <label
      onDragOver={(e) => { e.preventDefault(); setHovering(true); }}
      onDragLeave={() => setHovering(false)}
      onDrop={onDrop}
      className={`
        block border-2 border-dashed rounded-lg p-10 text-center cursor-pointer
        transition-colors
        ${hovering ? "border-accent-blue bg-gray-900" : "border-gray-700 hover:border-gray-600"}
      `}
    >
      <input
        type="file"
        accept="application/pdf"
        className="hidden"
        onChange={(e) => onFile(e.target.files?.[0] ?? null)}
      />
      {file ? (
        <div className="space-y-1">
          <p className="text-white">{file.name}</p>
          <p className="text-xs text-gray-500">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
        </div>
      ) : (
        <div className="space-y-1">
          <p className="text-gray-300">Drop a PDF here, or click to pick one</p>
          <p className="text-xs text-gray-500">Max 50 pages · academic content works best</p>
        </div>
      )}
    </label>
  );
}

// ─── Inline BYOK modal ────────────────────────────────────────────────────────

function KeyModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => Promise<void> }) {
  const [provider, setProvider] = useState<"openai" | "anthropic">("openai");
  const [key, setKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function save() {
    setSaving(true);
    setErr(null);
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ provider, api_key: key }),
    });
    if (!res.ok) {
      setErr(await res.text());
      setSaving(false);
      return;
    }
    await onSaved();
  }

  return (
    <div className="fixed inset-0 bg-black/70 flex items-center justify-center px-4 z-50">
      <div className="bg-accent-ink border border-gray-700 rounded-lg p-6 w-full max-w-md space-y-4">
        <h3 className="text-lg font-semibold">Add your API key</h3>
        <p className="text-sm text-gray-400">
          We use your key to call the LLM for your job. It&apos;s encrypted at rest and
          never shared. Generating a 10-min video costs ~$2-3 in tokens.
        </p>

        <div className="flex gap-2">
          <button
            onClick={() => setProvider("openai")}
            className={`flex-1 px-3 py-2 rounded text-sm border ${
              provider === "openai" ? "border-accent-blue bg-gray-800" : "border-gray-700"
            }`}
          >
            OpenAI
          </button>
          <button
            onClick={() => setProvider("anthropic")}
            className={`flex-1 px-3 py-2 rounded text-sm border ${
              provider === "anthropic" ? "border-accent-blue bg-gray-800" : "border-gray-700"
            }`}
          >
            Anthropic
          </button>
        </div>

        <input
          type="password"
          value={key}
          onChange={(e) => setKey(e.target.value)}
          placeholder={provider === "openai" ? "sk-..." : "sk-ant-..."}
          className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded font-mono text-sm"
        />

        {err && <p className="text-sm text-red-400">{err}</p>}

        <div className="flex gap-2">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-700 rounded text-sm"
          >
            Cancel
          </button>
          <button
            onClick={save}
            disabled={!key || saving}
            className="flex-1 px-4 py-2 bg-accent-blue rounded text-sm font-medium disabled:opacity-40"
          >
            {saving ? "Saving…" : "Save and continue"}
          </button>
        </div>

        <p className="text-xs text-gray-500 text-center">
          Get a key:{" "}
          <a
            href={provider === "openai"
              ? "https://platform.openai.com/api-keys"
              : "https://console.anthropic.com/settings/keys"}
            target="_blank"
            rel="noreferrer"
            className="text-accent-blue hover:underline"
          >
            {provider === "openai" ? "OpenAI" : "Anthropic"} dashboard ↗
          </a>
        </p>
      </div>
    </div>
  );
}
