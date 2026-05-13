"""Stage 5 — Render.

Per-scene render loop. Invoked from app.render_one_scene (Modal fan-out).

Loop:
  for attempt in 1..MAX_ATTEMPTS:
      code = codegen.generate_code(spec, attempt, prior_error)
      result = sandbox.run(code)
      if result.ok and ffprobe(mp4).valid:
          return RenderedScene
      prior_error = result.traceback
  static_slide_fallback(spec, narration) -> RenderedScene(is_fallback=True)
"""
from __future__ import annotations

import asyncio
import logging
import tempfile
from datetime import datetime
from pathlib import Path

from workers.lib.config import UserApiKeys, WorkerConfig
from workers.lib.errors import CodegenError, RenderError
from workers.lib.schemas import (
    JobEventKind,
    RenderedScene,
    SceneSpec,
    ScriptScene,
)

log = logging.getLogger(__name__)


def render_scene_sync(payload: dict) -> dict:
    """Sync entry point for Modal's .map(). Runs the full per-scene chain:
    Stage 3 (spec gen) -> Stage 4 (codegen) -> Stage 5 (render).
    Returns a RenderedScene dict.
    """
    return asyncio.run(_render_scene_async(payload))


async def _render_scene_async(payload: dict) -> dict:
    from workers.app import render_image as base_image  # heavy image for sandbox
    from workers.lib.byok import decrypt
    from workers.lib.config import UserApiKeys, WorkerConfig
    from workers.lib.sandbox import run_manim_scene
    from workers.lib.supabase_client import (
        emit_event,
        fetch_user_settings,
        make_client,
        upload_video,
        upsert_scene,
    )
    from workers.stages.codegen import generate_code
    from workers.stages.scene_spec import run_scene_spec

    cfg = WorkerConfig.from_env()
    client = make_client(cfg)

    job_id: str = payload["job_id"]
    user_id: str = payload["user_id"]
    scene_index: int = payload["scene_index"]
    script_scene = ScriptScene.model_validate(payload["script_scene"])
    tone_hint: str = payload.get("tone_hint", "balanced")

    settings = fetch_user_settings(client, user_id) or {}
    openai_enc = settings.get("openai_api_key_encrypted")
    anth_enc = settings.get("anthropic_api_key_encrypted")
    keys = UserApiKeys(
        openai=decrypt(cfg.byok_encryption_key, openai_enc) if openai_enc else None,
        anthropic=decrypt(cfg.byok_encryption_key, anth_enc) if anth_enc else None,
        preferred_model=settings.get("preferred_model", "gpt-4o"),
    )

    ctx = _PerSceneContext(
        cfg=cfg, supabase=client,
        job_id=job_id, user_id=user_id,
        user_keys=keys, tone_hint=tone_hint,
    )

    # Stage 3 — Scene Spec
    spec: SceneSpec = await run_scene_spec(ctx, script_scene)
    await upsert_scene(client, job_id, scene_index, spec.scene_id,
                       spec=spec.model_dump(), status="spec_generated")

    # Stage 4 + 5 — Codegen + Render loop
    prior_code: str | None = None
    prior_error: str | None = None

    for attempt in range(1, cfg.render_attempts + 1):
        await emit_event(client, job_id, "codegen", JobEventKind.PROGRESS,
                         {"scene_id": spec.scene_id, "attempt": attempt})
        try:
            gen = await generate_code(ctx, spec, attempt=attempt,
                                      prior_code=prior_code, prior_error=prior_error)
        except CodegenError as e:
            log.warning("Codegen failed on attempt %d: %s", attempt, e)
            prior_error = str(e)
            continue

        await upsert_scene(client, job_id, scene_index, spec.scene_id,
                           status="code_generated", attempts=attempt)

        try:
            result = run_manim_scene(cfg, gen.python_source, sandbox_image=base_image)
        except Exception as e:
            log.warning("Sandbox failed on attempt %d: %s", attempt, e)
            prior_code = gen.python_source
            prior_error = str(e)
            await emit_event(client, job_id, "render", JobEventKind.RETRY,
                             {"scene_id": spec.scene_id, "attempt": attempt, "error_class": "SandboxError"})
            continue

        if result.ok and result.mp4_bytes:
            video_path = upload_video(client, job_id, f"scenes/{spec.scene_id}.mp4", result.mp4_bytes)
            await upsert_scene(client, job_id, scene_index, spec.scene_id,
                               video_path=video_path, status="rendered",
                               attempts=attempt, is_fallback=False,
                               duration_sec=spec.duration_sec)
            await emit_event(client, job_id, "render", JobEventKind.COMPLETED,
                             {"scene_id": spec.scene_id, "attempt": attempt, "path": video_path})
            return RenderedScene(
                scene_id=spec.scene_id,
                mp4_storage_path=video_path,
                duration_sec=spec.duration_sec,
                resolution=(854, 480),  # -ql output; will re-render at -qh in compose if needed
                is_fallback=False,
                render_attempts=attempt,
            ).model_dump()

        # Render failed — feed traceback into next attempt
        prior_code = gen.python_source
        prior_error = result.traceback or result.stderr
        await emit_event(client, job_id, "render", JobEventKind.RETRY, {
            "scene_id": spec.scene_id,
            "attempt": attempt,
            "error_class": result.error_class,
        })

    # All attempts failed — fall back to a static slide
    fallback_path = await _render_static_slide_fallback(client, job_id, spec, script_scene)
    await upsert_scene(client, job_id, scene_index, spec.scene_id,
                       video_path=fallback_path, status="fallback",
                       attempts=cfg.render_attempts, is_fallback=True,
                       duration_sec=spec.duration_sec)
    await emit_event(client, job_id, "render", JobEventKind.PROGRESS,
                     {"scene_id": spec.scene_id, "outcome": "fallback"})
    return RenderedScene(
        scene_id=spec.scene_id,
        mp4_storage_path=fallback_path,
        duration_sec=spec.duration_sec,
        resolution=(854, 480),
        is_fallback=True,
        render_attempts=cfg.render_attempts,
    ).model_dump()


# ─── Static fallback ──────────────────────────────────────────────────────────


async def _render_static_slide_fallback(client, job_id: str, spec: SceneSpec,
                                        script: ScriptScene) -> str:
    """Render a simple static-slide MP4 from the narration.

    Implementation note: we generate a hard-coded ManimCE scene that renders
    the narration as a centered Text block. This runs in the same sandbox.
    """
    from workers.app import render_image as base_image  # heavy image for sandbox
    from workers.lib.sandbox import run_manim_scene
    from workers.lib.supabase_client import upload_video

    safe_narration = (script.narration_md
                      .replace("\\", "\\\\")
                      .replace('"', '\\"')
                      .replace("\n", " "))[:600]
    fallback_code = f'''
from manim import Scene, Text, FadeIn, FadeOut

class Main(Scene):
    def construct(self):
        t = Text("{safe_narration}", line_spacing=1.1, font_size=32).scale_to_fit_width(12)
        self.play(FadeIn(t), run_time=1.0)
        self.wait({max(0.5, spec.duration_sec - 2.0):.2f})
        self.play(FadeOut(t), run_time=1.0)
'''
    cfg = WorkerConfig.from_env()
    result = run_manim_scene(cfg, fallback_code, sandbox_image=base_image)
    if not result.ok or not result.mp4_bytes:
        # Even the fallback failed — surface a real error to the user.
        raise RenderError(
            f"Static-slide fallback failed for {spec.scene_id}: {result.error_class}",
            payload={"stderr": result.stderr[-1000:]},
        )
    return upload_video(client, job_id, f"scenes/{spec.scene_id}_fallback.mp4", result.mp4_bytes)


# ─── Inline lightweight context for per-scene work ────────────────────────────


class _PerSceneContext:
    """Lightweight per-scene context — mirrors PipelineContext shape but built
    inside the render fan-out worker.
    """

    def __init__(self, cfg: WorkerConfig, supabase, job_id: str, user_id: str,
                 user_keys: UserApiKeys, tone_hint: str):
        self.cfg = cfg
        self.supabase = supabase
        self.job_id = job_id
        self.user_id = user_id
        self.user_keys = user_keys
        self.tone_hint = tone_hint
        # not used at scene-level but referenced by some helpers
        self.target_duration_sec = 600
