# Active Blockers

| ID | Description | Blocks | Owner to resolve | ETA |
|----|-------------|--------|------------------|-----|
| B-001 | Supabase project not provisioned (no URL/keys) | E1, E3 deploy validation | User | After this Phase 1+2 commit |
| B-002 | Modal account not provisioned (no tokens) | E4, E7, E8 deploy validation | User | After this Phase 1+2 commit |
| B-003 | Vercel project not linked to repo | E1, E2 deploy | User | After this Phase 1+2 commit |
| B-004 | BYOK_ENCRYPTION_KEY not generated | API route /api/settings rejects requests until set | User (1 line of Python) | After this Phase 1+2 commit |
| B-005 | LLM API key (for dev evals, NOT user BYOK) — needed by E6 corpus indexer | Corpus indexing | User | After this Phase 1+2 commit |
| B-006 | Voyage API key (for embeddings) | Corpus indexing | User | After this Phase 1+2 commit |
| B-007 | No clone of `3Blue1Brown/videos` repo locally | E6 corpus indexer can't run | E6 / user (one `git clone`) | Week 2 Day 1 |
| B-008 | `workers.corpus.manim_gl_to_ce.translate()` rewrites imports inside string literals and docstrings (flat regex pass, not AST-aware) | LLM may see rewritten reference snippets that contain corrupted prose in docstrings | E10 noted, owner = whoever owns corpus indexer | When AST-aware rewriter is needed |
| B-009 | `workers` package can't be imported locally without `supabase` installed (test collection of `workers/tests/test_audio_stub.py` fails with `ImportError: cannot import name 'Client' from 'supabase'`). Preexisting; not caused by E10 changes | Local `pytest` from repo root halts on collection unless supabase is installed or that file is skipped | E5/E7 (whoever owns deps) | When CI image has supabase installed by default |

All blockers above are external dependencies, not engineering. The codebase is ready.

## Bug findings logged by E10 (not fixed per scope)

- **B-008** — flat-regex translation in `manim_gl_to_ce.translate()`. Test `test_import_string_inside_string_literal_is_still_rewritten_known_limitation` documents this. To fix: switch to `ast`-based rewriter or a `tokenize`-aware sweep that skips `STRING` and `COMMENT` tokens.
- **B-009** — local `supabase` import error. Workaround already in `workers/tests/test_pipeline_state.py` (sys.modules pre-stub). Long-term fix: ship a thin internal `supabase_client` stub or install the real `supabase` package in dev `requirements.txt`.
