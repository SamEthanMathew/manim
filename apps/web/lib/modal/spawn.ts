/**
 * Calls Modal's run_pipeline function over Modal's REST API.
 *
 * In Modal, .spawn() can be invoked over HTTPS via the modal Python SDK
 * or via a web endpoint. For our Vercel API routes, we POST to a Modal
 * web endpoint that wraps `run_pipeline.spawn(job_id)`.
 *
 * Setup steps (E10, Week 1):
 *   - In modal/app.py, decorate a function with @app.web_endpoint(method="POST").
 *   - That endpoint takes {job_id} and calls `run_pipeline.spawn(job_id)`.
 *   - The URL is set as MODAL_PIPELINE_ENDPOINT in Vercel env.
 *   - The endpoint accepts a shared secret header (MODAL_TRIGGER_SECRET).
 */

export async function spawnPipeline(jobId: string): Promise<void> {
  const url = process.env.MODAL_PIPELINE_ENDPOINT;
  const secret = process.env.MODAL_TRIGGER_SECRET;
  if (!url || !secret) {
    throw new Error("MODAL_PIPELINE_ENDPOINT or MODAL_TRIGGER_SECRET not configured");
  }

  const res = await fetch(url, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-trigger-secret": secret,
    },
    body: JSON.stringify({ job_id: jobId }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Modal spawn failed: ${res.status} ${text}`);
  }
}
