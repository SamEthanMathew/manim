# Week 0 Kickoff — Org Setup

**Status**: COMPLETED 2026-05-12 by Claude orchestration seat (E1 stand-in via direct file writes — no agents spawned, as Phase 1+2 scaffolding work was more efficient to do directly with full context).

**Goal of Week 0**: All infrastructure provisioned, repo scaffolded, schemas drafted. Every agent can deploy.

## Tasks

| ID | Owner | Task | Status | Output |
|----|-------|------|--------|--------|
| W0.1 | M1 | Create GitHub org `manim`, branch protection | Deferred (needs user API/auth) | n/a |
| W0.2 | M1 | Provision Vercel project linked to repo | Deferred (needs user API/auth) | n/a |
| W0.3 | M1 | Provision Supabase project | Deferred (needs user API/auth) | n/a |
| W0.4 | M1 | Provision Modal workspace + secrets | Deferred (needs user API/auth) | n/a |
| W0.5 | M1 | Provision Sentry / Axiom / LLM keys | Deferred (needs user API/auth) | n/a |
| W0.6 | M2 | Author `docs/contracts.md` | ✅ | [docs/contracts.md](../docs/contracts.md) |
| W0.7 | M2 | Scaffold `workers/lib/schemas.py` mirror | ✅ | [workers/lib/schemas.py](../workers/lib/schemas.py) + [packages/shared/schemas.ts](../packages/shared/schemas.ts) |
| W0.8 | M2 | Write `docs/decisions.md` ADRs 001-006 | ✅ | [docs/decisions.md](../docs/decisions.md) |
| W0.9 | M1 | Onboarding doc + `scripts/dev-setup.sh` | ✅ | [scripts/dev-setup.sh](../scripts/dev-setup.sh) |
| W0.10 | M1 | Repo scaffold (all top-level dirs) | ✅ | apps/web, modal/, packages/shared/, supabase/, docs/, coordination/, tests/, scripts/, .github/ |

## Outstanding (user input needed)

The following blocks Week 1 production deployment but does NOT block code development:

- **GitHub org creation** — needs user to create `github.com/<user>/manim`.
- **Vercel project** — needs user to link repo at vercel.com.
- **Supabase project** — needs user to create at supabase.com + capture `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`.
- **Modal account** — needs user to sign up + run `modal token set` locally + capture tokens for CI.
- **Sentry, Axiom** — optional, can defer to Week 2.

Once user provides these, M1 (or the human operator) finishes W0.1–W0.5 by populating environment variables.

## Exit criteria

- ✅ All Week 0 code-only tasks done.
- ⏸️ Production provisioning awaiting user API access.
