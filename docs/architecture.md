# System Architecture

This document is the high-level architecture map. Detailed schemas are in [contracts.md](./contracts.md). Locked tech decisions are in [decisions.md](./decisions.md). Top-level plan is in [`plan.md`](../plan.md).

## Pipeline overview

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────────┐
│  Vercel         │──1──▶│  Supabase        │◀──3──│  Modal              │
│  (Next.js)      │      │  Postgres+vector │      │  (workers + sandbox)│
│  - FE + API     │◀──4──│  Storage         │──2──▶│                     │
└─────────────────┘      │  Auth + Realtime │      └─────────────────────┘
                         └──────────────────┘
  1 = create job + upload PDF + spawn pipeline
  2 = decrypt BYOK + read PDF + write artifacts
  3 = artifact paths, videos, scene rows
  4 = Realtime push to /jobs/[id]
```

## Components

### Frontend (`apps/web/`)
- Next.js 15 App Router on Vercel Hobby.
- Pages: marketing landing, `/sign-in`, `/dashboard`, `/upload`, `/jobs/[id]`, `/settings`, `/demo/[slug]`.
- API route handlers: `/api/jobs`, `/api/jobs/[id]/approve`, `/api/settings`.
- Supabase clients: browser (anon), server (user-scoped via SSR cookies), admin (service role, server-only).
- BYOK encryption (AES-256-GCM, Node `crypto`) before write to `user_settings`.

### Database (`supabase/`)
Tables (see [contracts.md](./contracts.md) for full schemas):
- `user_settings` — encrypted BYOK keys + preferences.
- `jobs` — one row per job, lifecycle status, final video pointer.
- `job_events` — append-only audit log, Realtime publication source.
- `scenes` — per-scene state during fan-out.
- `prompts` — versioned prompt registry.
- `rag_documents` — pgvector-indexed 3b1b corpus + Manim docs.
- `usage_records` — cost telemetry.

RLS policies enforce user-scoped reads. Modal workers use the service-role key to bypass RLS for writes.

### Workers (`modal/`)
Single Modal app, two top-level functions:
- `run_pipeline(job_id)` — full pipeline orchestrator. Reads job, decrypts BYOK keys, runs Stages 0→7. Writes events to Realtime.
- `render_one_scene(payload)` — per-scene fan-out. Internally invokes `modal.Sandbox` for code execution.

Image bundles: Python 3.12, ManimCE, texlive-full, ffmpeg, qpdf, Nougat.

### Pipeline stages

| # | Stage | File | Input → Output |
|---|-------|------|----------------|
| 0 | Ingest      | `workers/stages/ingest.py` | PDF → `IngestedDocument` |
| 1 | Curriculum  | `workers/stages/curriculum.py` | → `CurriculumPlan` |
| 2 | Script      | `workers/stages/script.py` | → `Script` |
| 3 | Scene Spec  | `workers/stages/scene_spec.py` | → `SceneSpec` (per scene) |
| 4 | Codegen     | `workers/stages/codegen.py` | → `GeneratedScene` (Python source) |
| 5 | Render      | `workers/stages/render.py` | → `RenderedScene` (MP4) |
| 6 | Audio       | `workers/stages/audio.py` | → `AudioOutput` (silent in v1) |
| 7 | Compose     | `workers/stages/compose.py` | → `FinalVideo` (stitched MP4 + SRT) |

### RAG corpus (`workers/corpus/`)
- `indexer.py` — clones `3b1b/videos`, AST-walks `Scene` subclasses, translates ManimGL→CE, embeds via Voyage `voyage-3`, upserts to `rag_documents`.
- `retriever.py` — embed-query + pgvector ANN match for Stage 4 codegen.
- `manim_gl_to_ce.py` — top-20 idiom translation rules.

### Sandbox (`workers/lib/`)
- `ast_safety.py` — allowlist-based static check; reject before sandbox spawn.
- `sandbox.py` — `modal.Sandbox` wrapper: `block_network=True`, CPU/mem caps, timeout, scratch tmpfs at `/scene`.

### Audio interface (`workers/stages/audio.py`)
- `TTSProvider` Protocol — every TTS implementation satisfies this.
- `NullTTSProvider` — v1 default; emits silent WAV sized to estimated duration.
- `ElevenLabsTTSProvider`, `OpenAITTSProvider` — placeholders for future. The pipeline always calls `await provider.synthesize(...)`; swap by config, no code changes.

## Data flow (worked example)

1. User uploads `linear_algebra_ch4.pdf` on `/upload`.
2. Browser writes file to Supabase Storage at `<user_id>/<uuid>.pdf`.
3. Browser POSTs `/api/jobs` with `pdf_storage_path`.
4. Vercel handler validates BYOK + page count, inserts `jobs` row (status `pending`), calls Modal web endpoint `spawnPipeline(job_id)`.
5. Modal `run_pipeline(job_id)`:
   a. Fetches job + decrypts user's BYOK keys.
   b. Stage 0: downloads PDF, sanitizes via qpdf, runs Nougat → `IngestedDocument`.
   c. Stage 1: LLM call with `curriculum_v1.md` → `CurriculumPlan`.
   d. Stage 2: per-scene LLM call with `script_v1.md` → `Script`.
   e. Auto-approve (v1; approval gate in UI for later).
   f. `render_one_scene.map(scenes)`: fan-out for each scene → Stage 3 → Stage 4 (with RAG) → Stage 5 (sandbox render). Retries on failure. Static-slide fallback if 5 attempts exhausted.
   g. Stage 6: silent WAV per scene via `NullTTSProvider`.
   h. Stage 7: ffmpeg concat + SRT → `final.mp4` uploaded to `videos/<job_id>/final.mp4`.
6. Frontend subscribed to `job_events` via Realtime sees live stage transitions.
7. On `status='done'`, `/jobs/[id]` shows the final MP4 player.

## Observability

- **Logs**: Modal stdout → Axiom.
- **Metrics**: Prometheus endpoint per worker; Grafana Cloud free tier (deferred).
- **Errors**: Sentry on FE + workers.
- **Per-job timeline**: read `job_events` from frontend (this is the user-facing observability tool).
- **Cost telemetry**: `usage_records` table; admin dashboard reads from it.

## Security model

- All user-scoped writes go through RLS.
- BYOK keys encrypted at rest with AES-256-GCM; server-only key (`BYOK_ENCRYPTION_KEY`) in Modal/Vercel secrets.
- LLM-generated code passes AST allowlist check, then runs in network-blocked Modal Sandbox with resource caps.
- Storage buckets are private; access via signed URLs only.
- Service-role key never reaches the browser.

## Limits (v1)

- Max 50 pages per PDF
- Max 5–15 minute target video length
- Max 1 active job per user
- Max 3 jobs/day per user
- Storage retention: PDFs 30d, artifacts 7d, videos 30d (free tier)

## Where things scale next

When we outgrow v1:
- Move artifact storage to R2 (cheaper, free egress).
- Introduce Temporal if we need cross-stage saga compensation or >50 concurrent jobs.
- Pay for GPU on Modal for Nougat (drops Stage 0 from ~90s to ~15s).
- Run paid TTS (replace `NullTTSProvider` with `ElevenLabsTTSProvider`).
