import { NextResponse } from "next/server";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export async function POST(_req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) return new NextResponse("Unauthorized", { status: 401 });

  const { data: job } = await supabase
    .from("jobs")
    .select("id, user_id, status")
    .eq("id", id)
    .single();
  if (!job || job.user_id !== user.id) return new NextResponse("Not found", { status: 404 });
  if (job.status !== "awaiting_approval") {
    return new NextResponse(`Job is in status ${job.status}; cannot approve`, { status: 409 });
  }

  await supabase
    .from("jobs")
    .update({ approved: true, approved_at: new Date().toISOString(), status: "rendering" })
    .eq("id", id);

  return NextResponse.json({ ok: true });
}
