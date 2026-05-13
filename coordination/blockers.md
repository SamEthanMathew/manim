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

All blockers above are external dependencies, not engineering. The codebase is ready.
