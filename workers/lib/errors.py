"""Structured pipeline errors. All raised exceptions in stages should be one of these."""
from __future__ import annotations


class PipelineError(Exception):
    """Base for any pipeline-stage failure. Carries enough info for job_events."""

    stage: str = "unknown"
    user_facing: str = "An error occurred."

    def __init__(self, message: str, *, user_facing: str | None = None, payload: dict | None = None):
        super().__init__(message)
        self.payload = payload or {}
        if user_facing:
            self.user_facing = user_facing


class IngestError(PipelineError):
    stage = "ingest"
    user_facing = "We couldn't process your PDF."


class UnsupportedPDFError(IngestError):
    user_facing = "This PDF is not supported (likely scanned, encrypted, or non-English)."


class CurriculumError(PipelineError):
    stage = "curriculum"
    user_facing = "We couldn't plan a curriculum for this document."


class ScriptError(PipelineError):
    stage = "script"
    user_facing = "Script generation failed."


class SceneSpecError(PipelineError):
    stage = "scene_spec"
    user_facing = "Could not generate scene specifications."


class CodegenError(PipelineError):
    stage = "codegen"
    user_facing = "Code generation for a scene failed."


class RenderError(PipelineError):
    stage = "render"
    user_facing = "Scene render failed."


class AudioError(PipelineError):
    stage = "audio"
    user_facing = "Audio generation failed."


class ComposeError(PipelineError):
    stage = "compose"
    user_facing = "Final video composition failed."


class SandboxViolation(RenderError):
    """Raised when generated code fails AST safety check or sandbox runtime check."""
    user_facing = "Generated code failed safety checks."


class LLMRateLimitError(PipelineError):
    """User's LLM provider rate-limited us. Surface clearly so they can retry."""
    user_facing = "Your LLM provider rate-limited the request. Please try again later."
