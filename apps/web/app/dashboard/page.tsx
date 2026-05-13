import Link from "next/link";
import { redirect } from "next/navigation";
import { createSupabaseServerClient } from "@/lib/supabase/server";

export const dynamic = "force-dynamic";

export default async function DashboardPage() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/sign-in");

  const { data: jobs } = await supabase
    .from("jobs")
    .select("id, status, pdf_storage_path, created_at, final_video_path")
    .order("created_at", { ascending: false })
    .limit(50);

  return (
    <main className="min-h-screen px-6 py-12 max-w-5xl mx-auto">
      <header className="flex items-center justify-between mb-12">
        <h1 className="text-2xl font-semibold">Your jobs</h1>
        <div className="flex gap-3">
          <Link
            href="/settings"
            className="px-4 py-2 text-sm border border-gray-700 rounded-md hover:bg-gray-800"
          >
            Settings
          </Link>
          <Link
            href="/upload"
            className="px-4 py-2 text-sm bg-accent-blue rounded-md hover:opacity-90"
          >
            + New video
          </Link>
        </div>
      </header>

      {!jobs || jobs.length === 0 ? (
        <EmptyState />
      ) : (
        <ul className="space-y-2">
          {jobs.map((j) => (
            <li key={j.id}>
              <Link
                href={`/jobs/${j.id}`}
                className="block p-4 border border-gray-800 rounded-md hover:border-gray-700 hover:bg-gray-900"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-mono text-xs text-gray-500">{j.id.slice(0, 8)}</div>
                    <div className="text-sm text-gray-300">
                      {j.pdf_storage_path.split("/").pop()}
                    </div>
                  </div>
                  <StatusBadge status={j.status} />
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

function EmptyState() {
  return (
    <div className="text-center py-24 border border-dashed border-gray-800 rounded-lg">
      <p className="text-gray-400 mb-4">No jobs yet.</p>
      <Link
        href="/upload"
        className="px-4 py-2 bg-accent-blue rounded-md text-sm hover:opacity-90"
      >
        Upload your first PDF
      </Link>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    pending: "bg-gray-700",
    ingesting: "bg-accent-blue",
    scripting: "bg-accent-blue",
    awaiting_approval: "bg-accent-yellow text-black",
    rendering: "bg-accent-blue",
    composing: "bg-accent-blue",
    done: "bg-accent-green",
    failed: "bg-accent-red",
    cancelled: "bg-gray-600",
  };
  return (
    <span className={`text-xs px-2 py-1 rounded ${colors[status] || "bg-gray-700"}`}>
      {status}
    </span>
  );
}
