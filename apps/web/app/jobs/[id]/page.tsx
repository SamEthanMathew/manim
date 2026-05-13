"use client";
import { use, useEffect, useState } from "react";
import { createSupabaseBrowserClient } from "@/lib/supabase/browser";
import type { Job, JobEvent } from "@manim/shared";

export const dynamic = "force-dynamic";

const STAGES = [
  "ingest",
  "curriculum",
  "script",
  "scene_spec",
  "codegen",
  "render",
  "audio",
  "compose",
];

export default function JobDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const supabase = createSupabaseBrowserClient();
  const [job, setJob] = useState<Job | null>(null);
  const [events, setEvents] = useState<JobEvent[]>([]);
  const [showWaiting, setShowWaiting] = useState(false);

  // Set the page title based on the job id.
  useEffect(() => {
    document.title = `Job ${id.slice(0, 8)} — manim`;
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const { data: jobRow } = await supabase
        .from("jobs")
        .select("*")
        .eq("id", id)
        .single();
      if (!cancelled) setJob(jobRow as unknown as Job | null);

      const { data: eventRows } = await supabase
        .from("job_events")
        .select("*")
        .eq("job_id", id)
        .order("created_at");
      if (!cancelled) setEvents((eventRows ?? []) as unknown as JobEvent[]);
    })();

    const channel = supabase
      .channel(`job-${id}`)
      .on(
        "postgres_changes",
        { event: "INSERT", schema: "public", table: "job_events", filter: `job_id=eq.${id}` },
        (payload) => setEvents((prev) => [...prev, payload.new as unknown as JobEvent]),
      )
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "jobs", filter: `id=eq.${id}` },
        (payload) => setJob(payload.new as unknown as Job),
      )
      .subscribe();

    return () => {
      cancelled = true;
      void supabase.removeChannel(channel);
    };
  }, [id, supabase]);

  // After a short delay with no events, surface a "waiting for events" message
  // so the empty event log doesn't feel broken.
  useEffect(() => {
    if (events.length > 0) {
      setShowWaiting(false);
      return;
    }
    const t = setTimeout(() => setShowWaiting(true), 3000);
    return () => clearTimeout(t);
  }, [events.length]);

  if (!job) {
    return <JobDetailSkeleton />;
  }

  return (
    <main className="min-h-screen px-4 sm:px-6 py-8 sm:py-12 max-w-4xl mx-auto">
      <header className="mb-6 sm:mb-8">
        <div className="text-xs font-mono text-gray-400 mb-1 break-all">{job.id}</div>
        <h1 className="text-xl sm:text-2xl font-semibold break-words">
          {job.pdf_storage_path.split("/").pop()}
        </h1>
        <p className="text-sm text-gray-300 mt-1">
          Status: <span className="text-white">{job.status}</span>
        </p>
      </header>

      <section className="mb-10 sm:mb-12">
        <h2 className="text-sm uppercase tracking-wide text-gray-300 mb-3">Pipeline</h2>
        <ol className="space-y-1">
          {STAGES.map((stage) => {
            const stageEvents = events.filter((e) => e.stage === stage);
            const completed = stageEvents.some((e) => e.kind === "completed");
            const started = stageEvents.some((e) => e.kind === "started");
            const errored = stageEvents.some((e) => e.kind === "error");
            const state = errored
              ? "error"
              : completed
              ? "completed"
              : started
              ? "in-progress"
              : "pending";

            return (
              <li
                key={stage}
                className="flex flex-wrap gap-2 items-center justify-between p-3 border border-gray-800 rounded"
              >
                <span className="capitalize text-sm sm:text-base">{stage}</span>
                <StagePill state={state} />
              </li>
            );
          })}
        </ol>
      </section>

      {job.final_video_path && (
        <section>
          <h2 className="text-sm uppercase tracking-wide text-gray-300 mb-3">Result</h2>
          <video
            controls
            className="w-full rounded border border-gray-800"
            src={`${process.env.NEXT_PUBLIC_SUPABASE_URL}/storage/v1/object/public/videos/${job.final_video_path}`}
          />
        </section>
      )}

      <section className="mt-10 sm:mt-12">
        <h2 className="text-sm uppercase tracking-wide text-gray-300 mb-3">
          Event log ({events.length})
        </h2>
        {events.length === 0 ? (
          <p
            aria-live="polite"
            className="text-sm text-gray-400 border border-dashed border-gray-800 rounded p-4"
          >
            {showWaiting ? "Waiting for events…" : "Connecting…"}
          </p>
        ) : (
          <ul className="font-mono text-xs space-y-1 max-h-64 overflow-auto overflow-x-auto">
            {events.map((e) => (
              <li key={e.id} className="text-gray-300 break-all">
                <span className="text-gray-500">
                  {new Date(e.created_at).toLocaleTimeString()}
                </span>{" "}
                <span className="text-accent-blue">{e.stage}</span>.<span>{e.kind}</span>{" "}
                <span className="text-gray-400">{JSON.stringify(e.payload)}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}

function StagePill({ state }: { state: "pending" | "in-progress" | "completed" | "error" }) {
  const styles = {
    pending: "bg-gray-800 text-gray-300",
    "in-progress": "bg-accent-blue text-white animate-pulse",
    completed: "bg-accent-green text-black",
    error: "bg-accent-red text-white",
  };
  return (
    <span className={`text-xs px-2 py-0.5 rounded ${styles[state]}`}>{state}</span>
  );
}

function JobDetailSkeleton() {
  return (
    <main
      aria-busy="true"
      aria-label="Loading job"
      className="min-h-screen px-4 sm:px-6 py-8 sm:py-12 max-w-4xl mx-auto animate-pulse"
    >
      <div className="mb-6 sm:mb-8 space-y-2">
        <div className="h-3 w-40 bg-gray-800 rounded" />
        <div className="h-7 w-2/3 bg-gray-800 rounded" />
        <div className="h-4 w-32 bg-gray-800 rounded" />
      </div>
      <div className="space-y-1">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-12 bg-gray-900 border border-gray-800 rounded" />
        ))}
      </div>
    </main>
  );
}
