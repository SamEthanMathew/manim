# Quality Dashboard

**Maintained by**: M2 (Architect)

This document is the source of truth for the team's quality bar over time. M2 updates it after each Friday integration sync.

## North-Star Metrics (target by Week 8)

| Metric | Target | Current |
|--------|--------|---------|
| Render success rate (no fallback) | ≥ 85% on golden PDFs | not measured yet |
| Codegen success rate at attempt 3 | ≥ 85% | not measured yet |
| End-to-end success rate (with fallback) | ≥ 99% | not measured yet |
| p95 PDF -> playable video | < 25 min | not measured yet |
| Cost per video (infra, BYOK excluded) | < $0.80 | not measured yet |
| AST safety check false-positive rate | < 5% | not measured yet |
| Pedagogical score (vision LLM rubric, 1-10) | ≥ 7 avg | not measured yet |

## Eval cadence

- **Nightly** (`.github/workflows/nightly_eval.yml`): full pipeline on 5–10 golden PDFs once they exist.
- **Per-PR**: schema + unit tests + render success on 5 hand-written specs (Week 3 onwards).
- **Weekly Friday**: M1 + M2 manually review one fresh random PDF run.

## Open quality threats

1. **No real measurements yet** — entire system is scaffolded but not exercised. M2's first integration test (Week 1 Friday equivalent) will produce the first row of real numbers.
2. **Sandbox real behavior unknown** — Modal Sandbox API behavior (especially around reading/writing the produced MP4) is assumed to work as documented; needs validation in Week 1.
3. **Codegen baseline unknown** — without a single LLM call against real specs, we don't know if 75% by Week 3 is plausible.

## Recent changes

| Date | Change | By | Effect |
|------|--------|----|--------|
| 2026-05-12 | Initial scaffolding committed | Claude orchestration | Code-complete for Phase 1+2 |
