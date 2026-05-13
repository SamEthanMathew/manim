"use client";

import { useCallback, useEffect, useRef, useState } from "react";
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

  // Set the page title client-side.
  useEffect(() => {
    document.title = "manim — Upload a PDF";
  }, []);

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
    return <HomeSkeleton />;
  }

  return (
    <main className="min-h-screen px-4 sm:px-6 py-8 sm:py-12 max-w-3xl mx-auto">
      <header className="flex items-center justify-between mb-8 sm:mb-12">
        <h1 className="font-mono text-lg tracking-tight">manim</h1>
        <Link
          href="/settings"
          className="text-sm text-gray-300 hover:text-white rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--bg)] px-1"
        >
          settings
        </Link>
      </header>

      <section className="space-y-3 mb-8 sm:mb-10">
        <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold tracking-tight leading-tight">
          Upload a PDF.
          <br />
          Get a 3Blue1Brown-style video.
        </h2>
        <p className="text-gray-300 text-sm sm:text-base">
          Drop a textbook chapter, paper, or lecture notes. We extract the math, plan a
          curriculum, write a script, generate Manim code per scene, and render the video.
        </p>
      </section>

      <fieldset disabled={busy} className="space-y-5 disabled:opacity-90">
        <FileDrop file={file} onFile={setFile} disabled={busy} />

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
          <div>
            <label
              htmlFor="duration"
              className="block text-xs uppercase tracking-wide text-gray-300 mb-1"
            >
              Duration
            </label>
            <select
              id="duration"
              value={duration}
              onChange={(e) => setDuration(parseInt(e.target.value, 10))}
              disabled={busy}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue disabled:opacity-60"
            >
              <option value={300}>5 minutes</option>
              <option value={600}>10 minutes</option>
              <option value={900}>15 minutes</option>
            </select>
          </div>
          <div>
            <label
              htmlFor="tone"
              className="block text-xs uppercase tracking-wide text-gray-300 mb-1"
            >
              Tone
            </label>
            <select
              id="tone"
              value={tone}
              onChange={(e) => setTone(e.target.value as Tone)}
              disabled={busy}
              className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded-md text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue disabled:opacity-60"
            >
              <option value="balanced">Balanced</option>
              <option value="formal">Formal</option>
              <option value="playful">Playful</option>
              <option value="technical">Technical</option>
            </select>
          </div>
        </div>

        {error && (
          <p role="alert" className="text-sm text-red-400 break-words">
            {error}
          </p>
        )}

        <button
          type="button"
          onClick={startUpload}
          disabled={!file || busy}
          aria-busy={busy}
          className="w-full px-6 py-3 bg-accent-blue text-white rounded-md font-medium hover:opacity-90 disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--bg)]"
        >
          {busy ? "Uploading…" : "Generate video"}
        </button>

        <p className="text-xs text-gray-300 text-center">
          You&apos;ll be asked for an OpenAI or Anthropic API key on the first run. It&apos;s
          encrypted and used only to run your job — we never bill for tokens.
        </p>
      </fieldset>

      <RecentJobs recent={recent} />

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

// ─── Skeleton for initial load ────────────────────────────────────────────────

function HomeSkeleton() {
  return (
    <main
      aria-busy="true"
      aria-label="Loading"
      className="min-h-screen px-4 sm:px-6 py-8 sm:py-12 max-w-3xl mx-auto animate-pulse"
    >
      <div className="flex items-center justify-between mb-8 sm:mb-12">
        <div className="h-5 w-20 bg-gray-800 rounded" />
        <div className="h-4 w-14 bg-gray-800 rounded" />
      </div>
      <div className="space-y-3 mb-8 sm:mb-10">
        <div className="h-9 sm:h-12 w-3/4 bg-gray-800 rounded" />
        <div className="h-9 sm:h-12 w-2/3 bg-gray-800 rounded" />
        <div className="h-4 w-full bg-gray-800 rounded mt-4" />
        <div className="h-4 w-5/6 bg-gray-800 rounded" />
      </div>
      <div className="space-y-5">
        <div className="h-40 bg-gray-900 border-2 border-dashed border-gray-800 rounded-lg" />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
          <div className="h-16 bg-gray-900 border border-gray-800 rounded-md" />
          <div className="h-16 bg-gray-900 border border-gray-800 rounded-md" />
        </div>
        <div className="h-12 bg-gray-800 rounded-md" />
      </div>
      <span className="sr-only">Loading the upload form…</span>
    </main>
  );
}

// ─── Recent jobs (with empty-state hint) ──────────────────────────────────────

function RecentJobs({ recent }: { recent: Job[] }) {
  return (
    <section className="mt-12 sm:mt-16">
      <h3 className="text-xs uppercase tracking-wide text-gray-300 mb-3">Recent jobs</h3>
      {recent.length === 0 ? (
        <p className="text-sm text-gray-400 border border-dashed border-gray-800 rounded p-4">
          Your jobs will show up here once you start one.
        </p>
      ) : (
        <ul className="space-y-1">
          {recent.map((j) => (
            <li key={j.id}>
              <Link
                href={`/jobs/${j.id}`}
                className="flex flex-wrap sm:flex-nowrap gap-2 sm:gap-0 justify-between items-center p-3 border border-gray-800 rounded hover:border-gray-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--bg)]"
              >
                <span className="font-mono text-xs text-gray-400 shrink-0">
                  {j.id.slice(0, 8)}
                </span>
                <span className="text-sm text-gray-200 flex-1 min-w-0 sm:ml-4 truncate">
                  {j.pdf_storage_path.split("/").pop()}
                </span>
                <span className="text-xs px-2 py-0.5 rounded bg-gray-800 shrink-0">
                  {j.status}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

// ─── File drop component ──────────────────────────────────────────────────────

function FileDrop({
  file,
  onFile,
  disabled,
}: {
  file: File | null;
  onFile: (f: File | null) => void;
  disabled?: boolean;
}) {
  const [hovering, setHovering] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    setHovering(false);
    if (disabled) return;
    const f = e.dataTransfer.files?.[0];
    if (f && f.type === "application/pdf") onFile(f);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (disabled) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      inputRef.current?.click();
    }
  }

  return (
    <div
      role="button"
      tabIndex={disabled ? -1 : 0}
      aria-disabled={disabled || undefined}
      aria-label={file ? `Selected file: ${file.name}. Press Enter to change.` : "Upload a PDF. Press Enter to choose a file, or drop one here."}
      onClick={() => {
        if (!disabled) inputRef.current?.click();
      }}
      onKeyDown={onKeyDown}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setHovering(true);
      }}
      onDragLeave={() => setHovering(false)}
      onDrop={onDrop}
      className={`
        block border-2 border-dashed rounded-lg p-6 sm:p-10 text-center
        transition-colors focus:outline-none
        ${disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer"}
        focus-visible:ring-2 focus-visible:ring-accent-blue focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--bg)]
        ${hovering ? "border-accent-blue bg-gray-900" : "border-gray-700 hover:border-gray-600"}
      `}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        className="hidden"
        disabled={disabled}
        onChange={(e) => onFile(e.target.files?.[0] ?? null)}
      />
      {file ? (
        <div className="space-y-1">
          <p className="text-white break-all">{file.name}</p>
          <p className="text-xs text-gray-300">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
        </div>
      ) : (
        <div className="space-y-1">
          <p className="text-gray-200 text-sm sm:text-base">Drop a PDF here, or click to pick one</p>
          <p className="text-xs text-gray-300">Max 50 pages · academic content works best</p>
        </div>
      )}
    </div>
  );
}

// ─── Inline BYOK modal ────────────────────────────────────────────────────────

function KeyModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => Promise<void> }) {
  const [provider, setProvider] = useState<"openai" | "anthropic">("openai");
  const [key, setKey] = useState("");
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const dialogRef = useRef<HTMLDivElement>(null);
  const firstFocusRef = useRef<HTMLButtonElement>(null);
  const lastActiveRef = useRef<HTMLElement | null>(null);

  // Trap focus inside the modal and close on Escape.
  useEffect(() => {
    lastActiveRef.current = document.activeElement as HTMLElement | null;
    firstFocusRef.current?.focus();

    function handleKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
        return;
      }
      if (e.key !== "Tab") return;
      const root = dialogRef.current;
      if (!root) return;
      const focusables = Array.from(
        root.querySelectorAll<HTMLElement>(
          'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((el) => !el.hasAttribute("aria-hidden"));
      if (focusables.length === 0) return;
      const first = focusables[0];
      const last = focusables[focusables.length - 1];
      const active = document.activeElement as HTMLElement | null;
      if (e.shiftKey && active === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    }

    document.addEventListener("keydown", handleKey);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.removeEventListener("keydown", handleKey);
      document.body.style.overflow = prevOverflow;
      lastActiveRef.current?.focus?.();
    };
  }, [onClose]);

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
    <div
      className="fixed inset-0 bg-black/70 flex items-center justify-center px-4 z-50"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="byok-title"
        className="bg-accent-ink border border-gray-700 rounded-lg p-5 sm:p-6 w-full max-w-md space-y-4 max-h-[90vh] overflow-y-auto"
      >
        <h3 id="byok-title" className="text-lg font-semibold">
          Add your API key
        </h3>
        <p className="text-sm text-gray-300">
          We use your key to call the LLM for your job. It&apos;s encrypted at rest and
          never shared. Generating a 10-min video costs ~$2-3 in tokens.
        </p>

        <div className="flex gap-2">
          <button
            ref={firstFocusRef}
            type="button"
            onClick={() => setProvider("openai")}
            aria-pressed={provider === "openai"}
            className={`flex-1 px-3 py-2 rounded text-sm border focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue ${
              provider === "openai" ? "border-accent-blue bg-gray-800" : "border-gray-700"
            }`}
          >
            OpenAI
          </button>
          <button
            type="button"
            onClick={() => setProvider("anthropic")}
            aria-pressed={provider === "anthropic"}
            className={`flex-1 px-3 py-2 rounded text-sm border focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue ${
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
          aria-label={`${provider} API key`}
          className="w-full px-3 py-2 bg-gray-900 border border-gray-700 rounded font-mono text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue"
        />

        {err && (
          <p role="alert" className="text-sm text-red-400 break-words">
            {err}
          </p>
        )}

        <div className="flex flex-col-reverse sm:flex-row gap-2">
          <button
            type="button"
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-gray-700 rounded text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={save}
            disabled={!key || saving}
            aria-busy={saving}
            className="flex-1 px-4 py-2 bg-accent-blue rounded text-sm font-medium disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue"
          >
            {saving ? "Saving…" : "Save and continue"}
          </button>
        </div>

        <p className="text-xs text-gray-300 text-center">
          Get a key:{" "}
          <a
            href={provider === "openai"
              ? "https://platform.openai.com/api-keys"
              : "https://console.anthropic.com/settings/keys"}
            target="_blank"
            rel="noreferrer"
            className="text-accent-blue hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue rounded"
          >
            {provider === "openai" ? "OpenAI" : "Anthropic"} dashboard ↗
          </a>
        </p>
      </div>
    </div>
  );
}
