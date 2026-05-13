# manim

**PDF -> 3blue1brown-style Manim video, end-to-end.**

Upload a PDF. We extract the math, plan a curriculum, write a 3b1b-style script, generate Manim code per scene (RAG'd against the real 3b1b repo), render it in a sandboxed environment, and stitch the output into a silent MP4. Audio (ElevenLabs) plugs in via a deferred adapter interface.

---

## Status

**v1 in development (Weeks 0-1).** See [`plan.md`](./plan.md) for the full 10-week build plan.

Working today: legacy `pdfplumber`-based extractor in `src/text_extractor/` (used as fallback for non-math PDFs). New pipeline being built in `modal/`.

---

## Architecture

```
Vercel (frontend + API)  ──>  Supabase (DB + auth + storage + realtime)
        │
        └── spawn() ──>  Modal (workers + sandboxed render)
```

- **Frontend & API**: Next.js 15 on Vercel
- **Database, auth, storage, realtime**: Supabase
- **Pipeline workers**: Modal Functions, with `modal.Sandbox` for untrusted code execution
- **Auth model**: BYOK — users supply their own OpenAI/Anthropic API keys (encrypted at rest)

Full architecture in [`docs/architecture.md`](./docs/architecture.md).
Decisions log in [`docs/decisions.md`](./docs/decisions.md).
Schema contracts in [`docs/contracts.md`](./docs/contracts.md).

---

## Repo Layout

```
apps/web/          Next.js frontend + API routes (Vercel)
modal/             Pipeline workers (Modal)
  stages/          One file per pipeline stage (ingest -> compose)
  corpus/          3b1b/videos AST walker + RAG retriever
  prompts/         Versioned LLM prompts
  lib/             Schemas, sandbox wrapper, AST safety
packages/shared/   TS types generated from Pydantic schemas
supabase/          SQL migrations + RLS policies
docs/              Authoritative schemas, ADRs, runbook
coordination/      Agent status files, sprint dashboards
tests/             Golden PDFs, integration suite, eval harness
scripts/           Dev setup, corpus reindex, deploy
src/               Legacy extractor (used as ingest fallback)
```

---

## Local Dev

```bash
./scripts/dev-setup.sh           # installs deps, scaffolds .env.local
pnpm --filter @manim/web dev     # frontend at localhost:3000
cd modal && modal serve app.py   # workers in dev mode
```

Requires: Node 20+, pnpm, uv, Modal CLI, Supabase CLI (optional for local DB).

---

## Pipeline Stages

| # | Stage | Input | Output |
|---|-------|-------|--------|
| 0 | Ingest      | PDF                  | `IngestedDocument` |
| 1 | Curriculum  | `IngestedDocument`   | `CurriculumPlan`   |
| 2 | Script      | `CurriculumPlan`     | `Script`           |
| 3 | Scene Spec  | `Script.scene`       | `SceneSpec`        |
| 4 | Codegen     | `SceneSpec` + RAG    | Manim Python code  |
| 5 | Render      | Code                 | MP4 (per scene)    |
| 6 | Audio       | `Script.scene`       | silent WAV (v1)    |
| 7 | Compose     | per-scene MP4 + WAV  | Final MP4          |

---

## License

TBD — pending decision on commercial vs source-available.
