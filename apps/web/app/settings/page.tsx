"use client";
import { useEffect, useState } from "react";

export const dynamic = "force-dynamic";

type Settings = {
  preferred_model: "gpt-4o" | "claude-sonnet-4-6" | "claude-opus-4-7";
  default_target_duration_sec: number;
  tone_hint: "balanced" | "formal" | "playful" | "technical";
  has_openai_key: boolean;
  has_anthropic_key: boolean;
};

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [openaiKey, setOpenaiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [savingKey, setSavingKey] = useState<"openai" | "anthropic" | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  useEffect(() => {
    document.title = "Settings — manim";
  }, []);

  async function refresh() {
    const res = await fetch("/api/settings");
    if (res.ok) setSettings(await res.json());
  }

  useEffect(() => {
    void refresh();
  }, []);

  async function saveKey(provider: "openai" | "anthropic", key: string) {
    setSavingKey(provider);
    setStatus(null);
    const res = await fetch("/api/settings", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ provider, api_key: key }),
    });
    setSavingKey(null);
    if (res.ok) {
      setStatus("Key saved.");
      if (provider === "openai") setOpenaiKey("");
      else setAnthropicKey("");
      await refresh();
    } else {
      setStatus(`Error: ${await res.text()}`);
    }
  }

  async function savePrefs(patch: Partial<Settings>) {
    await fetch("/api/settings", {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(patch),
    });
    await refresh();
  }

  return (
    <main className="min-h-screen px-4 sm:px-6 py-8 sm:py-12 max-w-2xl mx-auto">
      <h1 className="text-xl sm:text-2xl font-semibold mb-6 sm:mb-8">Settings</h1>

      <section className="space-y-4 mb-10 sm:mb-12">
        <h2 className="text-sm uppercase tracking-wide text-gray-300">API keys (BYOK)</h2>
        <p className="text-sm text-gray-300">
          Your keys are encrypted and used only to run your jobs. We never bill for tokens — your
          provider charges you directly.
        </p>

        <KeyRow
          label="OpenAI"
          value={openaiKey}
          onChange={setOpenaiKey}
          configured={settings?.has_openai_key ?? false}
          saving={savingKey === "openai"}
          onSave={() => saveKey("openai", openaiKey)}
        />
        <KeyRow
          label="Anthropic"
          value={anthropicKey}
          onChange={setAnthropicKey}
          configured={settings?.has_anthropic_key ?? false}
          saving={savingKey === "anthropic"}
          onSave={() => saveKey("anthropic", anthropicKey)}
        />
      </section>

      {settings && (
        <section className="space-y-6">
          <h2 className="text-sm uppercase tracking-wide text-gray-300">Preferences</h2>

          <div>
            <label htmlFor="pref-model" className="block text-sm mb-2">
              Preferred model
            </label>
            <select
              id="pref-model"
              value={settings.preferred_model}
              onChange={(e) =>
                void savePrefs({ preferred_model: e.target.value as Settings["preferred_model"] })
              }
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue"
            >
              <option value="gpt-4o">GPT-4o (OpenAI)</option>
              <option value="claude-sonnet-4-6">Claude Sonnet 4.6 (Anthropic)</option>
              <option value="claude-opus-4-7">Claude Opus 4.7 (Anthropic)</option>
            </select>
          </div>

          <div>
            <label htmlFor="pref-tone" className="block text-sm mb-2">
              Default tone
            </label>
            <select
              id="pref-tone"
              value={settings.tone_hint}
              onChange={(e) =>
                void savePrefs({ tone_hint: e.target.value as Settings["tone_hint"] })
              }
              className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-md focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue"
            >
              <option value="balanced">Balanced</option>
              <option value="formal">Formal</option>
              <option value="playful">Playful</option>
              <option value="technical">Technical</option>
            </select>
          </div>
        </section>
      )}

      {status && (
        <p
          role="status"
          aria-live="polite"
          className="mt-4 text-sm text-gray-300 break-words"
        >
          {status}
        </p>
      )}
    </main>
  );
}

function KeyRow({
  label,
  value,
  onChange,
  configured,
  saving,
  onSave,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  configured: boolean;
  saving: boolean;
  onSave: () => void;
}) {
  const inputId = `key-${label.toLowerCase()}`;
  return (
    <div className="space-y-1">
      <label htmlFor={inputId} className="block text-sm">
        {label}{" "}
        {configured && (
          <span className="text-xs text-accent-green ml-2">configured</span>
        )}
      </label>
      <div className="flex flex-col sm:flex-row gap-2">
        <input
          id={inputId}
          type="password"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={configured ? "Replace existing key…" : "Paste key…"}
          aria-label={`${label} API key`}
          className="flex-1 px-4 py-2 bg-gray-900 border border-gray-700 rounded-md font-mono text-sm min-w-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue"
        />
        <button
          type="button"
          onClick={onSave}
          disabled={!value || saving}
          aria-busy={saving}
          className="px-4 py-2 bg-accent-blue rounded-md text-sm font-medium hover:opacity-90 disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-blue focus-visible:ring-offset-2 focus-visible:ring-offset-[color:var(--bg)]"
        >
          {saving ? "Saving…" : "Save"}
        </button>
      </div>
    </div>
  );
}
