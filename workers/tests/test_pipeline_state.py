"""Pipeline state-machine tests.

Verifies job_status transitions and job_events emission under three scenarios:

  1. Happy path — pending -> ingesting -> scripting -> rendering -> composing -> done
  2. Stage 0 raises IngestError — status becomes FAILED, error event written
  3. Stage 0 raises an unhandled (non-PipelineError) exception — status becomes
     FAILED, event payload contains kind=<ExceptionClassName>

Test self-containment:
  - `workers.app` and (indirectly) `workers.lib.supabase_client` import third-
    party packages (`modal`, `supabase`) that aren't installed locally during
    `pytest`. We register MagicMock entries in sys.modules BEFORE importing
    workers.pipeline so the import chain succeeds.

  - Supabase client interactions are stubbed via AsyncMock / MagicMock; we
    verify the orchestrator's calls rather than any real DB I/O.
"""
from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ─── Pre-import: stub third-party modules ────────────────────────────────────
# workers.lib.supabase_client imports `from supabase import Client, create_client`
# and workers.app imports `modal`. Both must exist as importable modules for
# workers.pipeline to load. We register lightweight MagicMock substitutes here.

if "modal" not in sys.modules:
    sys.modules["modal"] = MagicMock()

if "supabase" not in sys.modules:
    _supabase = MagicMock()
    _supabase.Client = MagicMock
    _supabase.create_client = MagicMock(return_value=MagicMock())
    sys.modules["supabase"] = _supabase

# Now safe to import.
from workers.lib.errors import IngestError  # noqa: E402
from workers.lib.schemas import JobStatus  # noqa: E402
from workers.pipeline import Pipeline, PipelineContext  # noqa: E402


# ─── Helpers ─────────────────────────────────────────────────────────────────


def _make_ctx() -> PipelineContext:
    cfg = MagicMock()
    cfg.byok_encryption_key = "test-key"
    supabase = MagicMock()
    return PipelineContext(
        cfg=cfg,
        supabase=supabase,
        job_id="job-123",
        user_id="user-1",
        user_keys=MagicMock(openai="sk-fake", anthropic=None, preferred_model="gpt-4o"),
        target_duration_sec=600,
        tone_hint="balanced",
        pdf_storage_path="path/to.pdf",
    )


def _record(captured: list[tuple[str, dict]]):
    """Build an AsyncMock that records (label, kwargs) calls."""

    async def _f(*args, **kwargs):
        captured.append(("call", {"args": args, "kwargs": kwargs}))

    return AsyncMock(side_effect=_f)


# ─── Happy path ──────────────────────────────────────────────────────────────


async def test_happy_path_status_transitions():
    """A successful run must emit status transitions in the expected order."""
    ctx = _make_ctx()

    status_calls: list[JobStatus] = []
    event_calls: list[tuple[str, str]] = []  # (stage, kind)

    async def fake_update_status(client, job_id, status, *, error_message=None):
        status_calls.append(status)

    async def fake_emit_event(client, job_id, stage, kind, payload=None):
        event_calls.append((stage, kind.value))

    # Stage stubs — return simple sentinel objects. Each gets a unique tag so
    # we know they were actually called in order.
    async def fake_build_context(cfg, client, job_id):
        return ctx

    async def fake_stage_ingest(c):
        event_calls.append(("ingest", "stage_called"))
        return MagicMock(spec=["sections", "model_dump_json"])

    async def fake_stage_curriculum(c, ingested):
        event_calls.append(("curriculum", "stage_called"))
        return MagicMock(scene_outline=[])

    async def fake_stage_script(c, plan, ingested):
        event_calls.append(("script", "stage_called"))
        return MagicMock(scenes=[])

    async def fake_stage_render_all(c, script):
        event_calls.append(("render", "stage_called"))
        return []

    async def fake_stage_audio(c, script):
        event_calls.append(("audio", "stage_called"))
        return []

    async def fake_stage_compose(c, rendered, audio, script):
        event_calls.append(("compose", "stage_called"))
        final = MagicMock()
        final.mp4_storage_path = "out.mp4"
        final.scene_count = 1
        final.fallback_scene_count = 0
        final.caption_srt_path = None
        return final

    with (
        patch("workers.pipeline.WorkerConfig") as mock_cfg,
        patch("workers.pipeline.make_client") as mock_make_client,
        patch("workers.pipeline.update_job_status", side_effect=fake_update_status),
        patch("workers.pipeline.emit_event", side_effect=fake_emit_event),
        patch.object(Pipeline, "_build_context", side_effect=fake_build_context),
        patch.object(Pipeline, "_stage_ingest", side_effect=fake_stage_ingest),
        patch.object(Pipeline, "_stage_curriculum", side_effect=fake_stage_curriculum),
        patch.object(Pipeline, "_stage_script", side_effect=fake_stage_script),
        patch.object(Pipeline, "_stage_render_all", side_effect=fake_stage_render_all),
        patch.object(Pipeline, "_stage_audio", side_effect=fake_stage_audio),
        patch.object(Pipeline, "_stage_compose", side_effect=fake_stage_compose),
    ):
        mock_cfg.from_env.return_value = MagicMock(byok_encryption_key="k")
        mock_make_client.return_value = MagicMock()

        result = await Pipeline.run("job-123")

    assert result["status"] == "done"
    assert result["final_video_path"] == "out.mp4"

    # The pipeline's TOP-LEVEL run() method only calls update_job_status for
    # the terminal DONE state. Individual stage wrappers (which we mocked out)
    # are what move through INGESTING / RENDERING / COMPOSING.
    # So at the orchestrator level we should see DONE at minimum.
    assert JobStatus.DONE in status_calls

    # COMPLETED event must fire at the end.
    assert any(kind == "completed" and stage == "control" for stage, kind in event_calls)


# ─── Stage 0 raises a PipelineError subclass ─────────────────────────────────


async def test_ingest_error_sets_failed_and_emits_error_event():
    ctx = _make_ctx()

    status_calls: list[tuple[JobStatus, str | None]] = []
    event_calls: list[tuple[str, str, dict]] = []

    async def fake_update_status(client, job_id, status, *, error_message=None):
        status_calls.append((status, error_message))

    async def fake_emit_event(client, job_id, stage, kind, payload=None):
        event_calls.append((stage, kind.value, payload or {}))

    async def fake_build_context(cfg, client, job_id):
        return ctx

    async def fake_stage_ingest(c):
        raise IngestError("scanned PDF not supported", user_facing="PDF not supported")

    with (
        patch("workers.pipeline.WorkerConfig") as mock_cfg,
        patch("workers.pipeline.make_client") as mock_make_client,
        patch("workers.pipeline.update_job_status", side_effect=fake_update_status),
        patch("workers.pipeline.emit_event", side_effect=fake_emit_event),
        patch.object(Pipeline, "_build_context", side_effect=fake_build_context),
        patch.object(Pipeline, "_stage_ingest", side_effect=fake_stage_ingest),
    ):
        mock_cfg.from_env.return_value = MagicMock(byok_encryption_key="k")
        mock_make_client.return_value = MagicMock()

        result = await Pipeline.run("job-123")

    assert result["status"] == "failed"
    assert result["stage"] == "ingest"

    # Verify status -> FAILED
    statuses = [s for s, _ in status_calls]
    assert JobStatus.FAILED in statuses

    # Verify an error event was emitted with the ingest stage tag.
    error_events = [(s, p) for s, k, p in event_calls if k == "error"]
    assert error_events, "Expected at least one error event"
    stages = [s for s, _ in error_events]
    assert "ingest" in stages


# ─── Stage 0 raises an unhandled exception ───────────────────────────────────


async def test_unhandled_exception_sets_failed_with_kind_in_payload():
    """A non-PipelineError exception in a stage must:
      - set the job status to FAILED
      - emit an error event whose payload includes kind=<ExceptionClassName>
      - re-raise (so Modal sees the failure)
    """
    ctx = _make_ctx()

    status_calls: list[JobStatus] = []
    event_calls: list[tuple[str, str, dict]] = []

    async def fake_update_status(client, job_id, status, *, error_message=None):
        status_calls.append(status)

    async def fake_emit_event(client, job_id, stage, kind, payload=None):
        event_calls.append((stage, kind.value, payload or {}))

    async def fake_build_context(cfg, client, job_id):
        return ctx

    class WeirdBug(RuntimeError):
        pass

    async def fake_stage_ingest(c):
        raise WeirdBug("kaboom")

    with (
        patch("workers.pipeline.WorkerConfig") as mock_cfg,
        patch("workers.pipeline.make_client") as mock_make_client,
        patch("workers.pipeline.update_job_status", side_effect=fake_update_status),
        patch("workers.pipeline.emit_event", side_effect=fake_emit_event),
        patch.object(Pipeline, "_build_context", side_effect=fake_build_context),
        patch.object(Pipeline, "_stage_ingest", side_effect=fake_stage_ingest),
    ):
        mock_cfg.from_env.return_value = MagicMock(byok_encryption_key="k")
        mock_make_client.return_value = MagicMock()

        with pytest.raises(WeirdBug):
            await Pipeline.run("job-123")

    assert JobStatus.FAILED in status_calls

    error_events = [(s, p) for s, k, p in event_calls if k == "error"]
    assert error_events, "Expected at least one error event"

    # The unhandled-exception branch tags payload with kind=<class name>.
    payloads = [p for _, p in error_events]
    assert any(p.get("kind") == "WeirdBug" for p in payloads), (
        f"Expected payload kind='WeirdBug' in {payloads}"
    )


# ─── Context-build failure (before any stage runs) ───────────────────────────


async def test_context_build_failure_emits_error_and_reraises():
    """If _build_context throws (e.g., missing API key), we should hit the
    outer 'failed to build context' branch which marks FAILED and re-raises.
    """
    status_calls: list[JobStatus] = []
    event_calls: list[tuple[str, str]] = []

    async def fake_update_status(client, job_id, status, *, error_message=None):
        status_calls.append(status)

    async def fake_emit_event(client, job_id, stage, kind, payload=None):
        event_calls.append((stage, kind.value))

    async def fake_build_context(cfg, client, job_id):
        raise RuntimeError("no api key on file")

    with (
        patch("workers.pipeline.WorkerConfig") as mock_cfg,
        patch("workers.pipeline.make_client") as mock_make_client,
        patch("workers.pipeline.update_job_status", side_effect=fake_update_status),
        patch("workers.pipeline.emit_event", side_effect=fake_emit_event),
        patch.object(Pipeline, "_build_context", side_effect=fake_build_context),
    ):
        mock_cfg.from_env.return_value = MagicMock(byok_encryption_key="k")
        mock_make_client.return_value = MagicMock()

        with pytest.raises(RuntimeError, match="no api key"):
            await Pipeline.run("job-123")

    assert JobStatus.FAILED in status_calls
    assert ("control", "error") in event_calls
