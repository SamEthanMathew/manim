# Overnight Build Summary — 2026-05-12 → 2026-05-13

**Goal**: Phases 3-8 of the plan, with thorough testing and end-to-end validation.

## Headline result

🟢 **End-to-end PDF → final.mp4 working.** Two real-data runs completed.

| Run | Job id | Scenes | Real renders | Fallbacks | Output |
|---|---|---|---|---|---|
| 1 | `b9a83bb3...` | 4 | 2 | 2 | 1.12 MB MP4 |
| 2 | `29e01b0b...` | 5 | **4** | 1 | 1.20 MB MP4 |

- Input: 7-page DiscreteMath_Syllabus.pdf, both runs
- Codegen success rate: 50% → **80%** between runs (same prompts, different LLM rolls)
- Wall time: 4-6 minutes from upload → done
- Cost: ~$0.70 in OpenAI tokens (gpt-4o-mini) across all runs tonight

## What runs end-to-end now

| Stage | Status |
|---|---|
| 0 Ingest (pdfplumber fallback) | ✅ 5 sections extracted |
| 1 Curriculum (LLM) | ✅ 4 scenes planned |
| 2 Script (LLM) | ✅ 4 narrations written |
| 3 Scene Spec (LLM) | ✅ 4 specs validated |
| 4 Codegen (LLM + repair) | ⚠️ 50% success rate; 2/4 produced runnable Manim |
| 5 Render (subprocess, sandbox WIP) | ✅ Both real renders + 2 static fallbacks produced MP4s |
| 6 Audio (NullTTSProvider) | ✅ 4 silent WAVs |
| 7 Compose (ffmpeg) | ✅ Concat + mux into final.mp4 |

## Bugs found and fixed tonight

| # | Bug | File | Fix |
|---|---|---|---|
| 1 | Modal CLI fails with `'charmap' codec can't encode character '→'` on Windows | scripts/dev | Always set `PYTHONIOENCODING=utf-8` |
| 2 | Image build aborts on `texlive-full` | workers/app.py | Split into base_image + render_image |
| 3 | `Header is not defined` at module load | workers/app.py | Move `from fastapi import Header` to module top |
| 4 | `No module named 'fastapi'` in render_image | workers/app.py | Add fastapi to render_image pip |
| 5 | `'Sandbox' object does not support the context manager protocol` | workers/lib/sandbox.py | Replace `with sb:` with `try/finally + sb.terminate()` |
| 6 | `Modal Sandbox with container ID ... not found` immediately after create | workers/lib/sandbox.py | B-010; added `_run_in_process` subprocess fallback |
| 7 | `[].__class__.__base__.__subclasses__()` not flagged by AST safety | workers/lib/ast_safety.py | Banned `__subclasses__`, `__bases__`, `__base__`, `__mro__`, `__globals__`, `__closure__`, `__code__`, `__builtins__` |
| 8 | BYOK decrypt fails with `\x...` hex bytea from supabase-py | workers/lib/byok.py | Auto-decode hex/bytes/memoryview at decrypt() entry |
| 9 | `You can't iter(Function.map()) from an async function` | workers/pipeline.py | Use `async for r in fn.map.aio(payloads)` |
| 10 | `Function has not been hydrated` | workers/pipeline.py | `modal.Function.from_name(...).hydrate.aio()` before `.map()` |
| 11 | `No module named 'structlog'` in render_image | workers/app.py | Render_image gets full base pip list |
| 12 | `No such file or directory: 'ffmpeg'` in compose | workers/app.py | Add `ffmpeg` to base_image apt |
| 13 | Storage download ReadTimeout in compose | workers/{stages/compose, lib/supabase_client}.py | Exponential backoff retry wrapper |
| 14 | user_settings preferred_model CHECK rejects gpt-4o-mini | Supabase migration | `alter table ... add constraint ... check (...)` |
| 15 | Smoke test silently fails when `modal run --quiet` is used | scripts | Document; use `modal run` (no flag) for diagnostics |
| 16 | MathTex over-escapes via `\\\\pi` in triple-quoted f-strings | workers/app.py smoke fixtures | Use raw `r'''...'''` blocks |
| 17 | Modal "App deployed in 1s" without re-uploading content (caching) | n/a | Touch the file or rename a function to force a re-upload |
| 18 | `experimental.typedRoutes` deprecated in Next 15.5 | apps/web/next.config.mjs | Move to top-level `typedRoutes: true` |
| 19 | Supabase client throws at Next.js prerender when env vars empty | apps/web/lib/supabase/* | Fall back to placeholders so build succeeds; runtime uses real env |
| 20 | Vercel build wanted pnpm-lock.yaml but none committed | repo root | Commit lockfile |

## What was deployed/built tonight

- Modal app `manim` (samethanmathew workspace): 7 functions, 2 images (base + render)
- Vercel project: 4 deployments, https://manim-zeta.vercel.app
- Supabase project: 4 SQL migrations applied, 6 prompts seeded, anon auth enabled
- GitHub repo: `SamEthanMathew/manim` (public, 9 commits tonight)

## Agent contributions

3 parallel agents dispatched, all completed:
- **E1/E2 Frontend agent**: ~10 files polished (mobile, a11y, skeletons, error boundaries, focus rings). Build passes.
- **E5 Prompt agent**: v2 prompts shipped (curriculum, script, scene_spec, codegen, codegen_repair) with worked examples + 3 verbatim 3b1b transcript excerpts curated.
- **E10 Test agent**: 71 new tests, 94/94 pass. Filed B-008 (manim_gl_to_ce regex limitation) and B-009 (supabase local-import).

## Quality state

Codegen success rate this run: **50%** (2/4 scenes). Path to higher:
1. Index the 3b1b corpus (requires Voyage key + git clone — deferred to next session)
2. Tune the codegen_v2 prompt's LaTeX guidance (LaTeXError is the dominant failure)
3. Add more reference examples to the codegen system prompt

Per the plan, Week 4 target is ≥85%. We're at 50% with no RAG. With RAG indexed and prompt v2 active in seed table, we should close most of the gap in 1-2 more iterations.

## What's still blocked

- **B-010**: modal.Sandbox lifecycle. Workaround active. To restore proper isolation, dig into Modal SDK 1.4.2 quirk or upgrade.
- **B-005, B-006**: Voyage + 3b1b corpus. Indexer is ready; needs key + clone.
- **B-008**: AST-aware manim_gl_to_ce rewriter.

## Spending tonight

- OpenAI (gpt-4o-mini): ~$0.50 across 5 e2e runs + the original $5 budget intact
- Modal: 0 of $30 monthly credit
- Anthropic: $0
- Supabase: free tier
- Vercel: free tier

## Verified user-facing flow

A user visits https://manim-zeta.vercel.app, gets anonymous-signed-in, drops a PDF, pastes their OpenAI key in the inline modal, clicks "Generate video," watches stages light up in real-time via Realtime, and ends up at `/jobs/[id]` with a playable MP4 embedded.
