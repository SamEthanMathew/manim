import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase/server";
import { spawnPipeline } from "@/lib/modal/spawn";

const MAX_DURATION = 1800;

export async function POST(req: Request) {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return new NextResponse("Unauthorized", { status: 401 });
  }

  let body: {
    pdf_storage_path?: string;
    target_duration_sec?: number;
    tone_hint?: string;
  };
  try {
    body = await req.json();
  } catch {
    return new NextResponse("Invalid JSON", { status: 400 });
  }

  if (!body.pdf_storage_path || typeof body.pdf_storage_path !== "string") {
    return new NextResponse("Missing pdf_storage_path", { status: 400 });
  }
  // Path safety: must begin with the user's id (matches storage RLS policy).
  if (!body.pdf_storage_path.startsWith(`${user.id}/`)) {
    return new NextResponse("Invalid pdf_storage_path", { status: 403 });
  }

  const duration = body.target_duration_sec ?? 600;
  if (duration < 60 || duration > MAX_DURATION) {
    return new NextResponse("Invalid target_duration_sec", { status: 400 });
  }

  // Rate limit: only 1 active job per user.
  const { data: active } = await supabase
    .from("jobs")
    .select("id, status")
    .eq("user_id", user.id)
    .not("status", "in", '("done","failed","cancelled")');
  if (active && active.length > 0) {
    return new NextResponse("You already have an active job. Wait for it to finish.", {
      status: 429,
    });
  }

  // Verify BYOK key exists.
  const { data: settings } = await supabase
    .from("user_settings")
    .select("openai_api_key_encrypted, anthropic_api_key_encrypted")
    .eq("user_id", user.id)
    .single();
  if (!settings?.openai_api_key_encrypted && !settings?.anthropic_api_key_encrypted) {
    return new NextResponse("Configure an OpenAI or Anthropic API key in /settings first.", {
      status: 400,
    });
  }

  const { data: job, error } = await supabase
    .from("jobs")
    .insert({
      user_id: user.id,
      status: "pending",
      pdf_storage_path: body.pdf_storage_path,
      target_duration_sec: duration,
      tone_hint: body.tone_hint ?? "balanced",
    })
    .select("id")
    .single();
  if (error || !job) {
    return new NextResponse(error?.message ?? "Failed to create job", { status: 500 });
  }

  try {
    await spawnPipeline(job.id);
  } catch (e) {
    // Surface a useful error but the job row already exists; user can retry.
    await supabase
      .from("jobs")
      .update({ status: "failed", error_message: `Spawn failed: ${(e as Error).message}` })
      .eq("id", job.id);
    return new NextResponse((e as Error).message, { status: 502 });
  }

  return NextResponse.json({ id: job.id });
}
