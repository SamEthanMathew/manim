import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { createSupabaseAdminClient } from "@/lib/supabase/admin";
import { encryptByok } from "@/lib/byok";

export async function GET() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return new NextResponse("Unauthorized", { status: 401 });

  const { data: s } = await supabase
    .from("user_settings")
    .select(
      "preferred_model, default_target_duration_sec, tone_hint, openai_api_key_encrypted, anthropic_api_key_encrypted",
    )
    .eq("user_id", user.id)
    .maybeSingle();

  return NextResponse.json({
    preferred_model: s?.preferred_model ?? "gpt-4o",
    default_target_duration_sec: s?.default_target_duration_sec ?? 600,
    tone_hint: s?.tone_hint ?? "balanced",
    has_openai_key: Boolean(s?.openai_api_key_encrypted),
    has_anthropic_key: Boolean(s?.anthropic_api_key_encrypted),
  });
}

export async function POST(req: Request) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return new NextResponse("Unauthorized", { status: 401 });

  let body: { provider?: string; api_key?: string };
  try {
    body = await req.json();
  } catch {
    return new NextResponse("Invalid JSON", { status: 400 });
  }
  if (
    !body.provider ||
    !["openai", "anthropic"].includes(body.provider) ||
    typeof body.api_key !== "string" ||
    body.api_key.length < 10
  ) {
    return new NextResponse("Invalid provider or api_key", { status: 400 });
  }

  const serverKey = process.env.BYOK_ENCRYPTION_KEY;
  if (!serverKey) {
    return new NextResponse("BYOK_ENCRYPTION_KEY not configured on server", { status: 500 });
  }

  // Validate the key with a cheap test call before saving.
  const valid = await validateKey(body.provider, body.api_key);
  if (!valid.ok) {
    return new NextResponse(`Key did not validate: ${valid.message}`, { status: 400 });
  }

  const encrypted = encryptByok(serverKey, body.api_key);
  const column =
    body.provider === "openai" ? "openai_api_key_encrypted" : "anthropic_api_key_encrypted";

  // Use admin client to write to user_settings (RLS would also allow this, but
  // we want to handle the upsert in a single call without conflict races).
  const admin = createSupabaseAdminClient();
  const { error } = await admin.from("user_settings").upsert(
    { user_id: user.id, [column]: encrypted },
    { onConflict: "user_id" },
  );
  if (error) return new NextResponse(error.message, { status: 500 });

  return NextResponse.json({ ok: true });
}

export async function PATCH(req: Request) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return new NextResponse("Unauthorized", { status: 401 });

  const body = await req.json().catch(() => null);
  if (!body || typeof body !== "object") {
    return new NextResponse("Invalid JSON", { status: 400 });
  }

  const allowed = ["preferred_model", "default_target_duration_sec", "tone_hint"] as const;
  const patch: Record<string, unknown> = {};
  for (const k of allowed) {
    if (k in body) patch[k] = body[k as keyof typeof body];
  }
  if (Object.keys(patch).length === 0) {
    return new NextResponse("No supported fields in patch", { status: 400 });
  }

  await supabase
    .from("user_settings")
    .upsert({ user_id: user.id, ...patch }, { onConflict: "user_id" });
  return NextResponse.json({ ok: true });
}

// ─── Key validation ─────────────────────────────────────────────────────────

async function validateKey(
  provider: string,
  apiKey: string,
): Promise<{ ok: true } | { ok: false; message: string }> {
  try {
    if (provider === "openai") {
      const res = await fetch("https://api.openai.com/v1/models", {
        headers: { Authorization: `Bearer ${apiKey}` },
      });
      if (res.ok) return { ok: true };
      return { ok: false, message: `OpenAI returned ${res.status}` };
    }
    // anthropic
    const res = await fetch("https://api.anthropic.com/v1/models", {
      headers: {
        "x-api-key": apiKey,
        "anthropic-version": "2023-06-01",
      },
    });
    if (res.ok) return { ok: true };
    return { ok: false, message: `Anthropic returned ${res.status}` };
  } catch (e) {
    return { ok: false, message: (e as Error).message };
  }
}
