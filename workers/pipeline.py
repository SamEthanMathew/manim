"""Pipeline orchestrator.

Drives a job through all 7 stages. Each stage is idempotent on (job_id,
scene_id where applicable). Resumability is achieved by checking artifact
presence before re-running a stage.

State transitions:
  pending -> ingesting -> scripting -> awaiting_approval -> rendering -> composing -> done
                                                                                   |-> failed
                                                                                   |-> cancelled
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from workers.lib.byok import decrypt
from workers.lib.config import UserApiKeys, WorkerConfig
from workers.lib.errors import PipelineError
from workers.lib.schemas import (
    AudioOutput,
    CurriculumPlan,
    FinalVideo,
    IngestedDocument,
    JobEventKind,
    JobStatus,
    RenderedScene,
    Script,
)
from workers.lib.supabase_client import (
    emit_event,
    fetch_job,
    fetch_user_settings,
    make_client,
    record_usage,
    update_job_status,
    upload_artifact,
)

log = logging.getLogger(__name__)


@dataclass
class PipelineContext:
    """Carries config + clients + per-job identifiers. Passed to each stage."""

    cfg: WorkerConfig
    supabase: Any  # supabase Client
    job_id: str
    user_id: str
    user_keys: UserApiKeys
    target_duration_sec: int
    tone_hint: str
    pdf_storage_path: str


class Pipeline:
    """Runs a job end-to-end. Each stage method is intentionally small —
    real work lives in modal/stages/*.py.
    """

    @staticmethod
    async def run(job_id: str) -> dict[str, Any]:
        cfg = WorkerConfig.from_env()
        client = make_client(cfg)

        try:
            ctx = await Pipeline._build_context(cfg, client, job_id)
        except Exception as e:
            log.exception("Failed to build pipeline context")
            await update_job_status(client, job_id, JobStatus.FAILED, error_message=str(e))
            await emit_event(client, job_id, "control", JobEventKind.ERROR, {"message": str(e)})
            raise

        try:
            await emit_event(client, job_id, "control", JobEventKind.STARTED, {})

            # Stage 0
            ingested = await Pipeline._stage_ingest(ctx)

            # Stage 1
            plan = await Pipeline._stage_curriculum(ctx, ingested)

            # Stage 2
            script = await Pipeline._stage_script(ctx, plan, ingested)

            # Approval gate — for v1 we auto-approve. Reviewer UI plugs in here
            # by setting jobs.status = 'awaiting_approval' and waiting on a
            # webhook from Vercel.
            await emit_event(ctx.supabase, ctx.job_id, "control", JobEventKind.PROGRESS,
                             {"checkpoint": "auto_approved"})

            # Stage 3 + 4 + 5 (fan-out per scene)
            rendered: list[RenderedScene] = await Pipeline._stage_render_all(ctx, script)

            # Stage 6 (silent in v1)
            audio: list[AudioOutput] = await Pipeline._stage_audio(ctx, script)

            # Stage 7
            final = await Pipeline._stage_compose(ctx, rendered, audio, script)

            await update_job_status(client, job_id, JobStatus.DONE)
            await emit_event(client, job_id, "control", JobEventKind.COMPLETED,
                             {"final_video_path": final.mp4_storage_path})

            client.table("jobs").update({
                "final_video_path": final.mp4_storage_path,
                "scene_count": final.scene_count,
                "fallback_scene_count": final.fallback_scene_count,
                "caption_srt_path": final.caption_srt_path,
            }).eq("id", job_id).execute()

            return {"status": "done", "final_video_path": final.mp4_storage_path}

        except PipelineError as e:
            log.error("Pipeline failure", extra={"stage": e.stage, "job_id": job_id})
            await update_job_status(client, job_id, JobStatus.FAILED, error_message=e.user_facing)
            await emit_event(client, job_id, e.stage, JobEventKind.ERROR,
                             {"message": str(e), "user_facing": e.user_facing, **e.payload})
            return {"status": "failed", "stage": e.stage, "message": str(e)}

        except Exception as e:
            log.exception("Unhandled pipeline error")
            await update_job_status(client, job_id, JobStatus.FAILED,
                                    error_message="Internal error. We've been notified.")
            await emit_event(client, job_id, "control", JobEventKind.ERROR,
                             {"message": str(e), "kind": type(e).__name__})
            raise

    # ─── Setup ─────────────────────────────────────────────────────────────

    @staticmethod
    async def _build_context(cfg: WorkerConfig, client: Any, job_id: str) -> PipelineContext:
        job = fetch_job(client, job_id)
        if not job:
            raise PipelineError(f"Job {job_id} not found")

        settings = fetch_user_settings(client, job["user_id"]) or {}
        openai_enc = settings.get("openai_api_key_encrypted")
        anth_enc = settings.get("anthropic_api_key_encrypted")

        keys = UserApiKeys(
            openai=decrypt(cfg.byok_encryption_key, openai_enc) if openai_enc else None,
            anthropic=decrypt(cfg.byok_encryption_key, anth_enc) if anth_enc else None,
            preferred_model=settings.get("preferred_model", "gpt-4o"),
        )

        if not keys.openai and not keys.anthropic:
            raise PipelineError(
                "No LLM API key configured. Set OpenAI or Anthropic key in /settings.",
                user_facing="Please add an OpenAI or Anthropic API key in Settings first.",
            )

        return PipelineContext(
            cfg=cfg,
            supabase=client,
            job_id=job_id,
            user_id=job["user_id"],
            user_keys=keys,
            target_duration_sec=job["target_duration_sec"],
            tone_hint=job.get("tone_hint", "balanced"),
            pdf_storage_path=job["pdf_storage_path"],
        )

    # ─── Stage wrappers ────────────────────────────────────────────────────
    # Each stage wrapper:
    #   1. Updates status -> emits started event
    #   2. Calls the real implementation from workers.stages.*
    #   3. Persists output artifact to Storage + scenes table
    #   4. Emits completed event
    #   5. Returns the parsed schema object

    @staticmethod
    async def _stage_ingest(ctx: PipelineContext) -> IngestedDocument:
        from workers.stages.ingest import run_ingest
        await update_job_status(ctx.supabase, ctx.job_id, JobStatus.INGESTING)
        await emit_event(ctx.supabase, ctx.job_id, "ingest", JobEventKind.STARTED, {})
        ingested = await run_ingest(ctx)
        path = upload_artifact(
            ctx.supabase, ctx.job_id, "ingested.json",
            ingested.model_dump_json(indent=2),
            content_type="application/json",
        )
        await emit_event(ctx.supabase, ctx.job_id, "ingest", JobEventKind.COMPLETED,
                         {"artifact_path": path, "section_count": len(ingested.sections)})
        return ingested

    @staticmethod
    async def _stage_curriculum(ctx: PipelineContext, ingested: IngestedDocument) -> CurriculumPlan:
        from workers.stages.curriculum import run_curriculum
        await update_job_status(ctx.supabase, ctx.job_id, JobStatus.SCRIPTING)
        await emit_event(ctx.supabase, ctx.job_id, "curriculum", JobEventKind.STARTED, {})
        plan = await run_curriculum(ctx, ingested)
        upload_artifact(
            ctx.supabase, ctx.job_id, "curriculum.json",
            plan.model_dump_json(indent=2),
            content_type="application/json",
        )
        await emit_event(ctx.supabase, ctx.job_id, "curriculum", JobEventKind.COMPLETED,
                         {"scene_count": len(plan.scene_outline)})
        return plan

    @staticmethod
    async def _stage_script(ctx: PipelineContext, plan: CurriculumPlan,
                            ingested: IngestedDocument) -> Script:
        from workers.stages.script import run_script
        await emit_event(ctx.supabase, ctx.job_id, "script", JobEventKind.STARTED, {})
        script = await run_script(ctx, plan, ingested)
        upload_artifact(
            ctx.supabase, ctx.job_id, "script.json",
            script.model_dump_json(indent=2),
            content_type="application/json",
        )
        await emit_event(ctx.supabase, ctx.job_id, "script", JobEventKind.COMPLETED,
                         {"scene_count": len(script.scenes)})
        return script

    @staticmethod
    async def _stage_render_all(ctx: PipelineContext, script: Script) -> list[RenderedScene]:
        """Stages 3 + 4 + 5 fan-out per scene.

        For each ScriptScene:
          - Run scene-spec gen (LLM)
          - Run codegen (LLM + RAG)
          - Render in sandbox
        Fan-out via Modal `.map()`.
        """
        from workers.app import render_one_scene  # local import to avoid cycle
        await update_job_status(ctx.supabase, ctx.job_id, JobStatus.RENDERING)
        await emit_event(ctx.supabase, ctx.job_id, "render", JobEventKind.STARTED,
                         {"scenes": len(script.scenes)})

        # Build payload per scene. Each contains everything `render_one_scene`
        # needs to run Stages 3->4->5 for that scene in isolation.
        payloads = [
            {
                "job_id": ctx.job_id,
                "user_id": ctx.user_id,
                "scene_index": i,
                "script_scene": s.model_dump(),
                "tone_hint": ctx.tone_hint,
            }
            for i, s in enumerate(script.scenes)
        ]

        # In v1, run in parallel with bounded concurrency.
        results = list(render_one_scene.map(payloads))
        rendered = [RenderedScene.model_validate(r) for r in results]

        await emit_event(ctx.supabase, ctx.job_id, "render", JobEventKind.COMPLETED, {
            "rendered": sum(1 for r in rendered if not r.is_fallback),
            "fallback": sum(1 for r in rendered if r.is_fallback),
        })
        return rendered

    @staticmethod
    async def _stage_audio(ctx: PipelineContext, script: Script) -> list[AudioOutput]:
        from workers.stages.audio import run_audio
        await emit_event(ctx.supabase, ctx.job_id, "audio", JobEventKind.STARTED, {})
        outputs = await run_audio(ctx, script)
        await emit_event(ctx.supabase, ctx.job_id, "audio", JobEventKind.COMPLETED,
                         {"count": len(outputs)})
        return outputs

    @staticmethod
    async def _stage_compose(ctx: PipelineContext,
                             rendered: list[RenderedScene],
                             audio: list[AudioOutput],
                             script: Script) -> FinalVideo:
        from workers.stages.compose import run_compose
        await update_job_status(ctx.supabase, ctx.job_id, JobStatus.COMPOSING)
        await emit_event(ctx.supabase, ctx.job_id, "compose", JobEventKind.STARTED, {})
        final = await run_compose(ctx, rendered, audio, script)
        await emit_event(ctx.supabase, ctx.job_id, "compose", JobEventKind.COMPLETED,
                         {"path": final.mp4_storage_path})
        return final
