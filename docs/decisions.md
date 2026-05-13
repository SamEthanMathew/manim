# Architectural Decision Records

Decisions that shape the system. Each ADR is dated, owns a status, and includes the alternatives considered. Future engineers: don't re-litigate without proposing a successor ADR.

---

## ADR-001 — Hosting: Vercel + Supabase + Modal

**Status**: Accepted (Week 0)
**Owner**: M2

### Decision

- **Frontend & API**: Vercel Hobby (Next.js 15)
- **Database, auth, storage, realtime**: Supabase (free tier)
- **Workers + sandbox**: Modal (free $30/mo credit)

### Context

Need to ship a production-grade showcase under a strict $0/month budget excluding LLM costs. Vercel's 60s function timeout means workers cannot live there. We need durable async compute somewhere.

### Alternatives considered

- AWS (EKS + RDS + S3): zero free credit available to this user. Operational burden too high for solo/small team.
- Fly.io + Railway: no free tier suitable for GPU/long-running workers anymore.
- Cloudflare Workers + D1: D1 lacks pgvector; would have to bolt on a separate vector DB.
- Self-host on a single VPS: blows up at any concurrency; no scale-to-zero.

### Consequences

- Storage cap at 1GB free — aggressive lifecycle policies needed (7d artifacts, 30d videos).
- Single Modal account = single billing point of failure. Move to org account before paid tier.
- Vercel function timeout means **all long work MUST live in Modal**; Vercel only orchestrates.

---

## ADR-002 — Manim flavor: Community Edition, not ManimGL

**Status**: Accepted (Week 0)
**Owner**: E7

### Decision

Use [ManimCE](https://docs.manim.community/) for all rendering. Convert 3b1b's ManimGL idioms at corpus-index time via `workers/corpus/manim_gl_to_ce.py`.

### Context

3b1b/videos uses ManimGL (Grant's personal fork). ManimGL is harder to install, has thinner docs, and breaks more often. ManimCE is pip-installable, well-documented, and has an active community.

### Alternatives considered

- ManimGL: matches 3b1b code exactly; rejected for fragility.
- Both: doubles Docker image size and test surface; rejected.

### Consequences

- Some 3b1b scene patterns won't translate cleanly (custom shaders, OpenGL specifics). Static-slide fallback handles these.
- Translation map must be maintained as ManimCE evolves — E7's responsibility.

---

## ADR-003 — Sandbox: Modal Sandboxes, not gVisor

**Status**: Accepted (Week 0)
**Owner**: E7

### Decision

Use `modal.Sandbox` for executing LLM-generated Manim code. `block_network=True`, CPU/RAM/timeout caps, scratch tmpfs mount.

### Context

LLM-generated Python must run in isolation. We considered building gVisor + custom Docker images on our own infrastructure, but Modal's `Sandbox` primitive provides equivalent isolation without infra ownership.

### Alternatives considered

- gVisor + custom containers on Fly.io: more flexible, more work to build/maintain, more attack surface to audit.
- Firecracker microVMs: heavier setup; overkill for our threat model.
- No sandbox, just AST static analysis: insufficient; a determined adversarial prompt could bypass AST checks via dynamic constructs.

### Consequences

- Defense-in-depth: AST allowlist before sandbox, sandbox enforces at runtime.
- Tied to Modal — if we move off Modal, this needs replacement.
- Network-blocked sandbox means Manim downloads (LaTeX packages, fonts) must be pre-installed in the image.

---

## ADR-004 — Auth model: BYOK for LLM keys

**Status**: Accepted (Week 0)
**Owner**: M1

### Decision

Users supply their own OpenAI / Anthropic API key in `/settings`. Keys encrypted at rest with `pgcrypto` AES-GCM using `BYOK_ENCRYPTION_KEY` server secret. We never bill for LLM tokens.

### Context

LLM costs ~$2-3 per video. At any meaningful free-tier signup volume, this is the dominant cost. We have no billing infrastructure in v1 and no $$ to give away.

### Alternatives considered

- Give away N free videos per signup on our keys: $3/signup × any growth = bankruptcy.
- Demo-only (no real uploads): kills the showcase value.
- Paid from day 1: adds Stripe + KYC overhead, blocks public-beta plan.

### Consequences

- Onboarding friction: user must obtain an OpenAI key before first use.
- Mitigation: pre-rendered demo PDFs (3 of them) accessible without any signup.
- BYOK encryption key rotation procedure documented in runbook.
- When we add paid tier, BYOK stays as an option for power users.

---

## ADR-005 — Queue: Postgres + Modal direct spawn, no Redis

**Status**: Accepted (Week 0)
**Owner**: E4

### Decision

No Redis. The `jobs` table is the source of truth for job state. Vercel API routes call `modal.Function.spawn()` directly. Modal handles its own queueing internally.

### Context

Adding Redis means a third infra dependency to provision, monitor, and pay for. At our scale (target <100 concurrent jobs in v1), Modal's built-in dispatching is sufficient.

### Alternatives considered

- Redis + RQ/Celery: standard pattern, more flexibility, more ops.
- Temporal: best-in-class for workflow orchestration, overkill for v1.
- Postgres LISTEN/NOTIFY: viable but adds complexity vs direct spawn.

### Consequences

- Revisit when we hit either:
  - >50 concurrent jobs (Modal queue depth becomes opaque)
  - Need for cross-stage saga compensation (Temporal becomes worth it)
- Job retry / resume is handled in `workers/pipeline.py` via stage idempotency on `(job_id, scene_id)`.

---

## ADR-006 — PDF ingest: Nougat primary, pdfplumber fallback

**Status**: Accepted (Week 0)
**Owner**: E8

### Decision

Stage 0 ingest pipeline:
1. **Primary**: Nougat (`facebook/nougat-base`) for math-aware extraction with LaTeX equations.
2. **Fallback**: existing `src/text_extractor/extraction.py` (pdfplumber + custom `StructureDetector`/`HierarchyBuilder`) when Nougat fails, errors, or detects no equations.
3. **Hard reject**: scanned PDFs (no embedded text), encrypted PDFs that `qpdf --decrypt` cannot unlock, non-English (v1).

### Context

Naive PDF text extraction destroys equations. Nougat is the open-weight state-of-the-art for academic documents. But Nougat is slow on CPU (90s per PDF) and can hallucinate on documents outside its training distribution (handwritten, non-academic).

The existing `src/text_extractor/` code is already-working `pdfplumber`-based extraction with custom heading detection. Salvaged as fallback rather than rewritten.

### Alternatives considered

- Mathpix API: best accuracy, costs money per page. Could revisit for paid tier.
- pdfplumber only: existing code, but equations come out as gibberish.
- Marker / GROBID: less established for math; deferred for evaluation.

### Consequences

- First sanitization step: `qpdf --decrypt --linearize` strips embedded JS / suspicious objects before either path runs.
- Stage 0 emits a `quality_score` so downstream stages know whether to trust equation extraction.
- E8 owns the choice logic (`when is fallback triggered`); decision criteria documented in `workers/stages/ingest.py`.

---

## ADR-007 — RAG corpus: 3b1b/videos under fair use, transformed via translation map

**Status**: Accepted (Week 0)
**Owner**: M2

### Decision

Index the public `3Blue1Brown/videos` GitHub repository for RAG retrieval. Retrieved scenes are used as **few-shot examples in the codegen prompt** — the LLM sees them as reference patterns, not as code to copy verbatim. We never republish Grant's actual rendered videos.

### Context

3b1b/videos is MIT-licensed code on a public GitHub repo (the videos themselves are © Grant Sanderson). Code-level retrieval falls within fair use; rendered video re-use would not.

### Alternatives considered

- Don't use 3b1b corpus: codegen quality drops significantly; the whole pedagogy lift comes from these examples.
- Train a model on 3b1b scenes: requires real ML pipeline; out of scope for v1.

### Consequences

- Codegen prompt explicitly instructs the LLM to **transform patterns**, not copy.
- ManimGL→CE translation in `workers/corpus/manim_gl_to_ce.py` means retrieved scenes are syntactically different from Grant's originals before they even reach the prompt.
- If 3b1b objects, we can either: (a) remove their code from the corpus, or (b) partner officially. Both are addressable.
- Document fair-use position in launch FAQ.

---

## Change Process

A new ADR:
1. Pick the next `ADR-NNN`.
2. Status: Proposed → Accepted | Superseded by ADR-XXX | Rejected.
3. Author opens RFC PR with this file modified.
4. M2 is required reviewer for `Accepted` transitions.
5. Superseding ADRs link to the predecessor; predecessor's status flips to `Superseded`.
