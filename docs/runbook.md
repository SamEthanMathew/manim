# Runbook

**Owner**: E10 (Platform / QA)

Top failure modes + how to resolve. Updated weekly as new failure modes are discovered.

## How to read

Each entry has: **symptom** -> **diagnose** -> **fix** -> **prevent**.

---

## 1. User: "My job is stuck on 'pending'"

**Symptom**: A `jobs` row sits at `status='pending'` for >2 minutes after upload.

**Diagnose**:
- Did the Vercel API route call `spawnPipeline(jobId)` succeed? Check Sentry for errors in `/api/jobs` POST.
- Did Modal receive the spawn? `modal app stats manim` should show recent invocations of `run_pipeline`.

**Fix**:
- If spawn failed: investigate `MODAL_PIPELINE_ENDPOINT` env var on Vercel; re-issue `modal token set`; redeploy.
- If Modal received but stuck: check Modal logs (`modal app logs manim`) for unhandled exceptions in `run_pipeline`.

**Prevent**: SLO monitoring on `jobs.created_at` vs `jobs.updated_at` — alert if delta > 5 min and status still pending.

---

## 2. Job fails with "No LLM API key configured"

**Symptom**: Job goes `pending` -> `failed` immediately. `error_message` mentions missing BYOK key.

**Fix**: User must add an OpenAI or Anthropic key in `/settings`. They likely skipped that step.

**Prevent**: API `/api/jobs` POST already pre-validates this — if you see it surfacing post-spawn, something raced (e.g., user deleted their key between upload and spawn). Add an end-of-Stage-0 re-check.

---

## 3. Render keeps falling back to static slide

**Symptom**: `jobs.fallback_scene_count` >= `scene_count / 2`. Every scene goes through 5 attempts and ends in fallback.

**Diagnose**:
- Look at `job_events` rows with `kind='retry'` for the affected scenes. Check `payload.error_class`.
  - Cluster of `SyntaxError`: codegen prompt is producing malformed code. Re-check `codegen_v1.md` rules.
  - Cluster of `ImportError`: a banned import is being requested. Check AST allowlist + add the import or update `manim_gl_to_ce.py`.
  - Cluster of `LaTeXError`: LaTeX in `MathTex(...)` is malformed. Sandbox image may be missing a package.
  - Cluster of `TimeoutError`: scene is too complex. Reduce element count in scene spec prompt.

**Fix**: Address the dominant error class. File a prompt-tuning ticket for E5/E6.

**Prevent**: Track per-error-class retry rates in the quality dashboard. Spike alerts trigger investigation.

---

## 4. Sandbox escape attempt

**Symptom**: AST safety check is raising `SandboxViolation` repeatedly for the same user's jobs. Or, worse: a render produces an MP4 but Sentry shows unexpected outbound network attempts from the sandbox container.

**Diagnose**: This is a security event, not a quality event. Immediately:
1. Disable the user's account (`auth.admin.deleteUser` via Supabase).
2. Pull their last 24h of jobs and inspect prompts + generated code.
3. Check Modal sandbox audit logs for actual breakouts.

**Fix**:
- If only AST checks tripping (good — caught early): no system change needed.
- If anything reached the sandbox runtime: tighten allowlist further, file a CVE-grade issue, rotate `BYOK_ENCRYPTION_KEY`, audit Modal Sandbox image.

**Prevent**: Quarterly external red-team. Add suspicious-prompt detection to upload pipeline.

---

## 5. Costs spiking

**Symptom**: Daily `usage_records` aggregation shows >$5/day on dev OpenAI key (corpus indexing key).

**Diagnose**: Likely the corpus re-indexer is running too often or on too many docs. Check `scripts/reindex_corpus.py` cron logs.

**Fix**: Tighten cron schedule; cache embeddings by content hash; reduce corpus surface.

**Prevent**: Hard cap on dev key spend at OpenAI dashboard ($20/mo).

---

## 6. Supabase storage at 80% of 1GB

**Symptom**: Supabase dashboard storage usage alert.

**Diagnose**: Cleanup cron isn't running, or there's a runaway job producing huge artifacts.

**Fix**:
- Manually trigger `scripts/cleanup.py` (deletes pdfs > 30d, artifacts > 7d, videos > 30d).
- Investigate any single job > 500MB — probably indicates fan-out failure where rendered scenes weren't cleaned up.

**Prevent**: Cron at 02:00 UTC daily. Per-job artifact size guard in `workers/lib/supabase_client.upload_video`.

---

## 7. CI failing on Pyright

**Symptom**: GitHub Actions `python > Pyright` step fails.

**Common causes**:
- New schema added without `__all__` export → import errors elsewhere.
- Missing return-type annotation in a public function.
- Pydantic v2 surfaces type errors we ignored in v1.

**Fix**: Run `cd modal && uv run pyright` locally; fix surfaced errors; re-push.

**Prevent**: Pre-commit hook runs pyright on changed files.

---

## 8. Vercel build failing

**Symptom**: GitHub Actions `web > Build` step fails.

**Common causes**:
- Missing env var in CI (`NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`).
- TS strict mode catches a regression.
- A `@manim/shared` schema field renamed without updating the TS mirror.

**Fix**: CI uses placeholder env vars for builds — if you see an env error, the placeholder isn't enough. Ensure no code uses `process.env.X!` for env vars that aren't placeholdable.

---

## On-call rotation (informal, v1)

Primary on-call rotation (weekday next-business-day response):
- Even weeks: E4, E7
- Odd weeks: E8, E10

Pager for: production data loss, security event, all-jobs-failing for >15 min.

---

## Postmortem template

Every incident with user impact gets a postmortem at `docs/postmortems/YYYY-MM-DD-<title>.md`. Owner: whoever was on-call. Reviewer: M1 + M2. Format:

1. Summary (1 paragraph)
2. Impact (users affected, duration)
3. Timeline (UTC timestamps)
4. Root cause
5. What went well
6. What went poorly
7. Action items (with owners + dates)

---

## Operational gotchas (Phase 3-4 build, learned 2026-05-13)

### Modal deploy on Windows: console encoding

**Symptom**: `modal deploy workers/app.py` fails with `'charmap' codec can't encode character '→'`.

**Cause**: Modal's CLI streams Unicode arrows in build progress; Windows default code page (cp1252) can't encode them.

**Fix**: Always prefix with `PYTHONIOENCODING=utf-8 PYTHONUTF8=1`. The `scripts/dev-setup.sh` should set these. CI sets them in `.github/workflows/deploy.yml`.

### Modal deploy timeout on heavy images

**Symptom**: Build aborts mid-apt-install with "Image build for im-... terminated due to external shut-down."

**Cause**: Modal's free-tier image builder has resource limits; texlive-full + manim + nougat-ocr in one image overruns them. We split into `base_image` (slim, ~200MB) and `render_image` (heavy, ~1.5GB) — see `workers/app.py` ADR-006.

**Fix**: Never add `texlive-full`. Use the curated `texlive` + `texlive-latex-extra` + `texlive-fonts-recommended` + `texlive-science` set. Nougat is deferred until we can afford a separate image variant.

### Modal CLI requires repo-root cwd

**Symptom**: `modal deploy workers/app.py` fails with `FileNotFoundError: 'C:\\Users\\samet\\Manim-MCP\\apps\\web\\workers/app.py'`.

**Cause**: Modal resolves the script path relative to the current working directory. Earlier `cd apps/web` from a build step left the shell in the wrong place.

**Fix**: Always run modal commands from the repo root. The `cwd` should be `C:\Users\samet\Manim-MCP`. If unsure, run `pwd` first.

### `modal run --quiet` swallows function return value

**Symptom**: Running `modal run --quiet workers/app.py::render_smoke_test` returns 0 exit code but no output, even though the function returned a dict.

**Cause**: `--quiet` suppresses everything including function return prints.

**Fix**: For smoke tests, use plain `modal run` (no `--quiet`). For production deploys where you don't want the chatty build output, `--quiet` is fine.

### Next.js build: env vars not available at build time

**Symptom**: `pnpm build` for `apps/web` fails with `@supabase/ssr: Your project's URL and API key are required to create a Supabase client!`

**Cause**: Next.js prerender pass instantiates the Supabase client at module load. If `process.env.NEXT_PUBLIC_SUPABASE_URL` is empty (typical for local builds without `apps/web/.env.local`), the client throws.

**Fix**: `lib/supabase/{browser,server}.ts` fall back to placeholder values when env vars are missing. The placeholders are never reached at runtime because Vercel populates the env vars correctly there.

### Anonymous sign-ins must be enabled in Supabase

**Symptom**: Homepage shows "This site can't create a session for you."

**Cause**: `signInAnonymously()` returns an error if the toggle is off in Supabase Auth → Providers.

**Fix**: Dashboard only — there's no SQL/MCP path. Enable at `/dashboard/project/<ref>/auth/providers`, scroll to **Anonymous Sign-ins**, toggle ON.

### Render image builds lazily on first sandbox spawn

**Symptom**: First real PDF render takes 5-10 minutes longer than expected; the user sees "rendering scene 1/N" for ages.

**Cause**: `render_image` (heavy LaTeX) is not attached to a deploy-time function. It builds on first `modal.Sandbox.create()` call.

**Fix (already applied)**: `render_smoke_test` and `render_smoke_sandbox` are decorated with `image=render_image`, which forces a build at deploy time. Make sure these stay in `workers/app.py`.

### Modal Sandbox: `--quiet` doesn't surface function `return` value either

Confirmed in testing 2026-05-13 — same as the `modal run --quiet` issue. Sandbox stdout is what surfaces.

---

## Tonight's verified findings (Weeks 3-4, 2026-05-13)

| What | Status |
|---|---|
| Base image deploys cleanly (~30s) | ✅ |
| Render image (texlive+manim) deploys (~5min) | ✅ |
| Modal trigger endpoint auth | ✅ |
| Supabase anonymous auth + RLS | ✅ |
| Frontend build green on Vercel | ✅ |
| 94 tests passing (`tests/`, `workers/tests/`) | ✅ |
| Sentry + structlog wired into entry points | ✅ |
| Prompts v2 with worked examples + 3b1b excerpts | ✅ |
| Render smoke test (LaTeX + Manim render in container) | see status |
| End-to-end with real PDF | pending — limited by $5 budget |

