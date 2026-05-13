"""Pydantic mirror of docs/contracts.md.

Single source of truth for inter-stage wire formats. Owned by M2 (Architect).

Schema changes follow the process in docs/contracts.md. Don't bypass.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

# ─── Common types ─────────────────────────────────────────────────────────────

Color = Annotated[str, Field(pattern=r"^#[0-9A-Fa-f]{6}$", description="Hex color")]
SceneId = Annotated[str, Field(min_length=1, max_length=64)]


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: float
    y: float
    z: float = 0.0


# ─── Stage 0 — IngestedDocument ───────────────────────────────────────────────


class Subject(str, Enum):
    MATH = "math"
    CS = "cs"
    PHYSICS = "physics"
    CHEMISTRY = "chemistry"
    BIOLOGY = "biology"
    OTHER = "other"


class Figure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    caption: str
    page: int = Field(ge=1)
    storage_path: str | None = None


class Section(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    level: int = Field(ge=1, le=6)
    title: str
    prose_md: str = ""
    equations: list[str] = []
    figures: list[Figure] = []


class DocumentMetadata(BaseModel):
    model_config = ConfigDict(extra="forbid")
    page_count: int = Field(ge=1, le=50, description="Hard cap 50 in v1")
    language: str = "en"
    detected_subject: Subject | None = None
    source_filename: str
    ingested_at: datetime


class IngestedDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    title: str
    sections: list[Section]
    metadata: DocumentMetadata


# ─── Stage 1 — CurriculumPlan ─────────────────────────────────────────────────


class Concept(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept_id: str
    name: str
    prerequisites: list[str] = []


class SceneOutline(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene_id: SceneId
    concept_id: str
    hook: str
    beat_summary: str
    estimated_sec: float = Field(ge=0)


class CurriculumPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    target_duration_sec: int = Field(ge=60, le=1800, default=600)
    learning_objectives: list[str]
    concept_dag: list[Concept]
    scene_outline: list[SceneOutline]

    @field_validator("scene_outline")
    @classmethod
    def unique_scene_ids(cls, v: list[SceneOutline]) -> list[SceneOutline]:
        ids = [s.scene_id for s in v]
        if len(ids) != len(set(ids)):
            raise ValueError("scene_outline contains duplicate scene_id")
        return v


# ─── Stage 2 — Script ─────────────────────────────────────────────────────────


class VisualCue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    at_word_index: int = Field(ge=0)
    description: str


class ScriptScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene_id: SceneId
    narration_md: str
    visual_cues: list[VisualCue] = []
    estimated_duration_sec: float = Field(ge=0)

    @field_validator("visual_cues")
    @classmethod
    def cues_strictly_increasing(cls, v: list[VisualCue]) -> list[VisualCue]:
        indices = [c.at_word_index for c in v]
        if indices != sorted(set(indices)):
            raise ValueError("visual_cues must be strictly increasing by at_word_index")
        return v


class Script(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    scenes: list[ScriptScene]


# ─── Stage 3 — SceneSpec ──────────────────────────────────────────────────────
#
# Elements are a discriminated union by `type`. Codegen depends on exhaustive
# handling of all variants — when you add a new one, also update:
#   - modal/stages/codegen.py element handlers
#   - modal/prompts/scene_spec_v1.md examples
#   - modal/prompts/codegen_v1.md examples


class _ElementBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    type: str


class MathTexElement(_ElementBase):
    type: Literal["MathTex"] = "MathTex"
    latex: str
    position: Position = Position(x=0, y=0)
    scale: float = 1.0


class TextElement(_ElementBase):
    type: Literal["Text"] = "Text"
    text: str
    position: Position = Position(x=0, y=0)
    scale: float = 1.0
    font: str | None = None


class AxesElement(_ElementBase):
    type: Literal["Axes"] = "Axes"
    x_range: tuple[float, float, float]
    y_range: tuple[float, float, float]
    position: Position = Position(x=0, y=0)
    scale: float = 1.0


class VectorElement(_ElementBase):
    type: Literal["Vector"] = "Vector"
    components: list[float]
    color: Color = "#FFFFFF"
    anchor_id: str | None = None


class GraphElement(_ElementBase):
    type: Literal["Graph"] = "Graph"
    function: str
    x_range: tuple[float, float]
    axes_id: str


class CircleElement(_ElementBase):
    type: Literal["Circle"] = "Circle"
    radius: float = Field(gt=0)
    position: Position = Position(x=0, y=0)
    color: Color = "#FFFFFF"
    fill_opacity: float = Field(ge=0, le=1, default=0.0)


class GroupElement(_ElementBase):
    type: Literal["Group"] = "Group"
    member_ids: list[str]


class ImageElement(_ElementBase):
    type: Literal["Image"] = "Image"
    storage_path: str
    position: Position = Position(x=0, y=0)
    scale: float = 1.0


Element = Annotated[
    MathTexElement
    | TextElement
    | AxesElement
    | VectorElement
    | GraphElement
    | CircleElement
    | GroupElement
    | ImageElement,
    Field(discriminator="type"),
]


class ActionKind(str, Enum):
    CREATE = "Create"
    FADE_IN = "FadeIn"
    FADE_OUT = "FadeOut"
    TRANSFORM = "Transform"
    INDICATE = "Indicate"
    WRITE = "Write"
    WAIT = "Wait"


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    at_t: float = Field(ge=0)
    duration_sec: float = Field(ge=0)
    action: ActionKind
    target_id: str | None = None
    params: dict = {}

    @field_validator("target_id")
    @classmethod
    def wait_has_no_target(cls, v: str | None, info) -> str | None:
        # Note: at this validator we don't have access to `action` until model_validator;
        # full cross-field check lives in SceneSpec.validate_actions below.
        return v


class SceneSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    scene_id: SceneId
    duration_sec: float = Field(ge=0)
    background: Color = "#000000"
    elements: list[Element] = []
    timeline: list[Action] = []

    @field_validator("elements")
    @classmethod
    def unique_element_ids(cls, v: list[Element]) -> list[Element]:
        ids = [e.id for e in v]
        if len(ids) != len(set(ids)):
            raise ValueError("elements contains duplicate id")
        return v

    @field_validator("timeline")
    @classmethod
    def actions_well_formed(cls, v: list[Action]) -> list[Action]:
        for a in v:
            if a.action == ActionKind.WAIT and a.target_id is not None:
                raise ValueError(f"Wait action must have target_id=null (got {a.target_id})")
            if a.action != ActionKind.WAIT and a.target_id is None:
                raise ValueError(f"{a.action.value} action requires target_id")
        return v


# ─── Stage 4 — GeneratedScene ─────────────────────────────────────────────────


class GeneratedScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    scene_id: SceneId
    python_source: str
    imports: list[str] = []
    llm_model: str
    llm_attempt: int = Field(ge=1)
    generated_at: datetime


# ─── Stage 5 — RenderedScene ──────────────────────────────────────────────────


class RenderedScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    scene_id: SceneId
    mp4_storage_path: str
    duration_sec: float = Field(ge=0)
    resolution: tuple[int, int] = (1920, 1080)
    is_fallback: bool = False
    render_attempts: int = Field(ge=1, default=1)


# ─── Stage 6 — Audio interface ────────────────────────────────────────────────


class PacingHints(BaseModel):
    model_config = ConfigDict(extra="forbid")
    estimated_duration_sec: float = Field(ge=0)
    pause_at_word_indices: list[int] = []
    emphasis_word_indices: list[int] = []


class NarrationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    voice_id: str | None = None
    pacing: PacingHints


class WordTiming(BaseModel):
    model_config = ConfigDict(extra="forbid")
    word: str
    start_sec: float = Field(ge=0)
    end_sec: float = Field(ge=0)


class AudioOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    scene_id: SceneId
    audio_storage_path: str
    duration_sec: float = Field(ge=0)
    word_timings: list[WordTiming] = []
    provider: Literal["null", "elevenlabs", "openai"] = "null"


class TTSProvider(Protocol):
    """All TTS implementations satisfy this protocol.

    The pipeline always calls TTSProvider.synthesize() — no conditionals.
    Swap NullTTSProvider for ElevenLabsTTSProvider via config; no other code changes.
    """

    async def synthesize(self, n: NarrationInput, scene_id: SceneId) -> AudioOutput: ...


# ─── Stage 7 — FinalVideo ─────────────────────────────────────────────────────


class FinalVideo(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    job_id: str
    mp4_storage_path: str
    duration_sec: float
    scene_count: int = Field(ge=1)
    fallback_scene_count: int = Field(ge=0)
    resolution: tuple[int, int] = (1920, 1080)
    has_audio: bool = False
    caption_srt_path: str | None = None


# ─── Job lifecycle (control-plane state, not strictly inter-stage) ────────────


class JobStatus(str, Enum):
    PENDING = "pending"
    INGESTING = "ingesting"
    SCRIPTING = "scripting"
    AWAITING_APPROVAL = "awaiting_approval"
    RENDERING = "rendering"
    COMPOSING = "composing"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobEventKind(str, Enum):
    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    ERROR = "error"
    RETRY = "retry"


__all__ = [
    # Stage 0
    "IngestedDocument",
    "Section",
    "Figure",
    "DocumentMetadata",
    "Subject",
    # Stage 1
    "CurriculumPlan",
    "Concept",
    "SceneOutline",
    # Stage 2
    "Script",
    "ScriptScene",
    "VisualCue",
    # Stage 3
    "SceneSpec",
    "Element",
    "MathTexElement",
    "TextElement",
    "AxesElement",
    "VectorElement",
    "GraphElement",
    "CircleElement",
    "GroupElement",
    "ImageElement",
    "Action",
    "ActionKind",
    "Position",
    # Stage 4
    "GeneratedScene",
    # Stage 5
    "RenderedScene",
    # Stage 6
    "TTSProvider",
    "NarrationInput",
    "AudioOutput",
    "PacingHints",
    "WordTiming",
    # Stage 7
    "FinalVideo",
    # Common
    "Color",
    "SceneId",
    "JobStatus",
    "JobEventKind",
]
