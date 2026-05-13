# Week 1 Kickoff — Foundations

**Goal**: Live deployed site with auth + PDF upload. Modal worker triggered. Render slice working on hand-written Manim code.

**Status as of plan execution (Phase 1+2)**: Scaffolding for ALL Week 1 tasks completed in code form. Production validation steps deferred until user provides cloud credentials.

## Per-agent assignments

### E1 — Frontend (App)

**Task**: Next.js 15 scaffold; Supabase Auth UI; dashboard, upload, job-detail, settings pages; Tailwind config.

**Status**: ✅ Scaffolded
- `apps/web/app/page.tsx` — landing (also covers E2)
- `apps/web/app/sign-in/page.tsx` — magic link + Google
- `apps/web/app/dashboard/page.tsx` — job list
- `apps/web/app/upload/page.tsx` — PDF upload form
- `apps/web/app/jobs/[id]/page.tsx` — live Realtime job detail
- `apps/web/app/settings/page.tsx` — BYOK + prefs
- `apps/web/lib/supabase/{browser,server,admin}.ts`

**Outstanding (validation deferred)**:
- Deploy to Vercel and validate Realtime subscription works end-to-end.
- Confirm Google OAuth redirect URLs in Supabase Auth dashboard.

### E2 — Frontend (Marketing + Demo)

**Task**: Landing page + `/demo/*` routes; design polish.

**Status**: ✅ Scaffolded
- Landing in `app/page.tsx` (merged with E1's work)
- `app/demo/[slug]/page.tsx` with 3 demo slugs (eigenvectors, sorting, fourier)

**Outstanding**:
- Replace placeholder demo videos with real renders once pipeline runs end-to-end (Week 5–6 deliverable).
- Designer pass after a real video is produced.

### E3 — Backend / API

**Task**: Supabase migrations 0001–0004, RLS policies, server-side clients, BYOK encryption, Vercel route handlers.

**Status**: ✅ Scaffolded
- `supabase/migrations/0001_initial.sql` — all tables
- `supabase/migrations/0002_rls_policies.sql` — RLS
- `supabase/migrations/0003_storage_buckets.sql` — buckets
- `supabase/migrations/0004_rag_match_function.sql` — pgvector ANN RPC
- `apps/web/lib/byok.ts` — AES-GCM encryption
- `apps/web/app/api/jobs/route.ts` — job creation + Modal spawn
- `apps/web/app/api/jobs/[id]/approve/route.ts` — approval gate
- `apps/web/app/api/settings/route.ts` — BYOK + prefs CRUD

**Outstanding**:
- Apply migrations to live Supabase project once provisioned.
- Verify RLS policies on a multi-user setup (E10 helps red-team).

### E4 — Pipeline Orchestrator

**Task**: Modal `app.py` + `pipeline.py` skeleton with all 7 stages stubbed, state machine, fan-out logic.

**Status**: ✅ Scaffolded
- `workers/app.py` — App definition + `run_pipeline` + `render_one_scene`
- `workers/pipeline.py` — Pipeline orchestrator with state machine
- `workers/lib/{config,errors,supabase_client,byok,llm}.py` — supporting libs

**Outstanding**:
- Verify `modal deploy` works once user provides Modal tokens.
- End-to-end smoke test with the stub stages.

### E5 — ML / Prompts

**Task**: 3b1b style guide + Stage 1–3 prompts v0.

**Status**: ✅ Scaffolded
- `workers/prompts/style_guide.md`
- `workers/prompts/curriculum_v1.md`
- `workers/prompts/script_v1.md`
- `workers/prompts/scene_spec_v1.md`
- `workers/prompts/codegen_v1.md` + `codegen_repair_v1.md`

**Outstanding**:
- Tune against 5 golden PDFs (Week 4 task).
- Curate 3–5 real 3b1b transcript excerpts and append to `style_guide.md` once selected.

### E6 — RAG / Codegen

**Task**: 3b1b corpus AST walker + ManimGL→CE translation map + retriever.

**Status**: ✅ Scaffolded
- `workers/corpus/indexer.py` — AST walker + enrichment + Supabase upsert
- `workers/corpus/manim_gl_to_ce.py` — top-20 idiom translation map
- `workers/corpus/retriever.py` — pgvector ANN query
- `supabase/migrations/0004_rag_match_function.sql` — SQL RPC

**Outstanding**:
- Run indexer against a local clone of `3b1b/videos` (Week 2 task once Voyage key is provisioned).
- Expand `manim_gl_to_ce.py` rules as audits reveal misses.

### E7 — Render / Sandbox

**Task**: Modal Sandbox wrapper + AST safety + render loop with retry + static fallback.

**Status**: ✅ Scaffolded
- `workers/lib/sandbox.py` — Modal Sandbox wrapper
- `workers/lib/ast_safety.py` — allowlist-based AST check
- `workers/stages/render.py` — per-scene render loop with retry + fallback

**Outstanding**:
- Validate Sandbox behavior on Modal once tokens provisioned (Week 1 spike).
- Red-team adversarial code (Week 3 + Week 6 + Week 9).

### E8 — Ingest

**Task**: Stage 0 — Nougat + fallback to legacy pdfplumber extractor.

**Status**: ✅ Scaffolded
- `workers/stages/ingest.py` — pipeline: qpdf sanitize → Nougat → pdfplumber fallback
- Reuses `src/text_extractor/extraction.py` as fallback path

**Outstanding**:
- Replace `_ingest_with_nougat` `NotImplementedError` with real Nougat invocation (Week 1 spike to verify image bundles Nougat correctly).

### E9 — Audio / Compose

**Task**: TTSProvider Protocol + NullTTSProvider + ffmpeg compose stage.

**Status**: ✅ Scaffolded
- `workers/stages/audio.py` — Protocol + NullTTSProvider + placeholder ElevenLabs/OpenAI providers
- `workers/stages/compose.py` — ffmpeg mux + concat + SRT caption generation

**Outstanding**:
- Verify ffmpeg invocations against real per-scene MP4s once render produces them.

### E10 — Platform / QA

**Task**: GitHub Actions CI, pre-commit, secrets management plan.

**Status**: ✅ Scaffolded
- `.github/workflows/{ci,nightly_eval,deploy}.yml`
- `.pre-commit-config.yaml`
- `scripts/dev-setup.sh`

**Outstanding**:
- Add GitHub Actions secrets (`MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`, etc.) once user provides them.
- Wire Sentry SDK calls into the three surfaces (Vercel route handlers, Modal pipeline, frontend).

## Friday Integration Test (Week 1 exit criteria)

Once user provides cloud credentials and migrations are applied:
- Sign-in flow works end-to-end on deployed URL.
- PDF upload creates a `jobs` row visible in Supabase dashboard.
- Manual `modal run workers/app.py --job-id <id>` triggers stub pipeline.
- Stub events visible streaming to `/jobs/[id]` page via Realtime.

## What's blocking real Week 1 exit

User must supply:
1. `SUPABASE_URL` + `SUPABASE_ANON_KEY` + `SUPABASE_SERVICE_ROLE_KEY`
2. Modal account + tokens (`MODAL_TOKEN_ID`, `MODAL_TOKEN_SECRET`)
3. Vercel project linked to GitHub repo
4. Optional but recommended: Sentry DSN, Axiom token, dev-only Voyage key for corpus indexing
5. Generate `BYOK_ENCRYPTION_KEY` (`python -c "import secrets; print(secrets.token_urlsafe(32))"`)
