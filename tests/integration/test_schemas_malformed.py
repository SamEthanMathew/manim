"""Malformed-input tests for every top-level schema.

Guarantees:
  - extra="forbid" rejects unknown fields
  - missing required fields are rejected
  - ge=0 / gt=0 numeric bounds are enforced
  - hard caps (e.g., page_count <= 50) are enforced

Each schema has the same shape of assertions so future schema additions can
follow the established template.
"""
from __future__ import annotations

from datetime import datetime

import pytest
from pydantic import ValidationError

from workers.lib.schemas import (
    ActionKind,
    AudioOutput,
    CurriculumPlan,
    Concept,
    DocumentMetadata,
    FinalVideo,
    GeneratedScene,
    IngestedDocument,
    MathTexElement,
    NarrationInput,
    PacingHints,
    Position,
    RenderedScene,
    SceneOutline,
    SceneSpec,
    Script,
    ScriptScene,
    Section,
    Subject,
    VisualCue,
)


# ─── Inline fixture builders ─────────────────────────────────────────────────


def _valid_metadata_kwargs() -> dict:
    return {
        "page_count": 5,
        "language": "en",
        "detected_subject": Subject.MATH,
        "source_filename": "x.pdf",
        "ingested_at": datetime(2026, 5, 12, 12, 0, 0),
    }


def _valid_ingested_kwargs() -> dict:
    return {
        "title": "T",
        "sections": [Section(id="s0", level=1, title="t")],
        "metadata": DocumentMetadata(**_valid_metadata_kwargs()),
    }


def _valid_curriculum_kwargs() -> dict:
    return {
        "learning_objectives": ["a"],
        "concept_dag": [Concept(concept_id="c1", name="N")],
        "scene_outline": [
            SceneOutline(
                scene_id="scene-0",
                concept_id="c1",
                hook="h",
                beat_summary="b",
                estimated_sec=10,
            ),
        ],
    }


def _valid_script_kwargs() -> dict:
    return {
        "scenes": [
            ScriptScene(scene_id="scene-0", narration_md="x", estimated_duration_sec=5)
        ]
    }


def _valid_scene_spec_kwargs() -> dict:
    return {
        "scene_id": "scene-0",
        "duration_sec": 10,
        "background": "#000000",
        "elements": [MathTexElement(id="m", latex="x")],
        "timeline": [],
    }


def _valid_generated_scene_kwargs() -> dict:
    return {
        "scene_id": "scene-0",
        "python_source": "x = 1",
        "imports": [],
        "llm_model": "gpt-4o",
        "llm_attempt": 1,
        "generated_at": datetime(2026, 5, 12, 12, 0, 0),
    }


def _valid_rendered_scene_kwargs() -> dict:
    return {
        "scene_id": "scene-0",
        "mp4_storage_path": "p/x.mp4",
        "duration_sec": 10,
    }


def _valid_audio_kwargs() -> dict:
    return {
        "scene_id": "scene-0",
        "audio_storage_path": "audio/scene-0.wav",
        "duration_sec": 5,
    }


def _valid_final_video_kwargs() -> dict:
    return {
        "job_id": "j-1",
        "mp4_storage_path": "p/x.mp4",
        "duration_sec": 120,
        "scene_count": 3,
        "fallback_scene_count": 0,
    }


# ─── IngestedDocument ────────────────────────────────────────────────────────


def test_ingested_document_extra_field_rejected():
    kwargs = _valid_ingested_kwargs()
    kwargs["bogus_field"] = True
    with pytest.raises(ValidationError):
        IngestedDocument(**kwargs)


def test_ingested_document_missing_required_field_rejected():
    kwargs = _valid_ingested_kwargs()
    del kwargs["title"]
    with pytest.raises(ValidationError):
        IngestedDocument(**kwargs)


def test_ingested_document_page_count_over_cap_rejected():
    meta = _valid_metadata_kwargs()
    meta["page_count"] = 51
    with pytest.raises(ValidationError):
        DocumentMetadata(**meta)


def test_ingested_document_page_count_zero_rejected():
    meta = _valid_metadata_kwargs()
    meta["page_count"] = 0
    with pytest.raises(ValidationError):
        DocumentMetadata(**meta)


def test_section_level_out_of_bounds_rejected():
    with pytest.raises(ValidationError):
        Section(id="s", level=7, title="t")
    with pytest.raises(ValidationError):
        Section(id="s", level=0, title="t")


# ─── CurriculumPlan ──────────────────────────────────────────────────────────


def test_curriculum_extra_field_rejected():
    kwargs = _valid_curriculum_kwargs()
    kwargs["surprise"] = 1
    with pytest.raises(ValidationError):
        CurriculumPlan(**kwargs)


def test_curriculum_missing_required_rejected():
    kwargs = _valid_curriculum_kwargs()
    del kwargs["learning_objectives"]
    with pytest.raises(ValidationError):
        CurriculumPlan(**kwargs)


def test_curriculum_target_duration_below_cap_rejected():
    kwargs = _valid_curriculum_kwargs()
    kwargs["target_duration_sec"] = 30  # below ge=60
    with pytest.raises(ValidationError):
        CurriculumPlan(**kwargs)


def test_curriculum_target_duration_above_cap_rejected():
    kwargs = _valid_curriculum_kwargs()
    kwargs["target_duration_sec"] = 5000  # above le=1800
    with pytest.raises(ValidationError):
        CurriculumPlan(**kwargs)


def test_scene_outline_negative_estimated_sec_rejected():
    with pytest.raises(ValidationError):
        SceneOutline(
            scene_id="scene-0",
            concept_id="c",
            hook="h",
            beat_summary="b",
            estimated_sec=-1,
        )


# ─── Script ──────────────────────────────────────────────────────────────────


def test_script_extra_field_rejected():
    kwargs = _valid_script_kwargs()
    kwargs["other"] = "x"
    with pytest.raises(ValidationError):
        Script(**kwargs)


def test_script_missing_required_rejected():
    with pytest.raises(ValidationError):
        Script()  # type: ignore[call-arg]


def test_script_scene_negative_estimated_duration_rejected():
    with pytest.raises(ValidationError):
        ScriptScene(
            scene_id="scene-0",
            narration_md="x",
            estimated_duration_sec=-0.1,
        )


def test_visual_cue_negative_word_index_rejected():
    with pytest.raises(ValidationError):
        VisualCue(at_word_index=-1, description="x")


# ─── SceneSpec ───────────────────────────────────────────────────────────────


def test_scene_spec_extra_field_rejected():
    kwargs = _valid_scene_spec_kwargs()
    kwargs["bonus"] = True
    with pytest.raises(ValidationError):
        SceneSpec(**kwargs)


def test_scene_spec_missing_required_rejected():
    kwargs = _valid_scene_spec_kwargs()
    del kwargs["scene_id"]
    with pytest.raises(ValidationError):
        SceneSpec(**kwargs)


def test_scene_spec_negative_duration_rejected():
    kwargs = _valid_scene_spec_kwargs()
    kwargs["duration_sec"] = -1
    with pytest.raises(ValidationError):
        SceneSpec(**kwargs)


def test_scene_spec_invalid_background_color_rejected():
    kwargs = _valid_scene_spec_kwargs()
    kwargs["background"] = "not-a-color"
    with pytest.raises(ValidationError):
        SceneSpec(**kwargs)


# ─── GeneratedScene ──────────────────────────────────────────────────────────


def test_generated_scene_extra_field_rejected():
    kwargs = _valid_generated_scene_kwargs()
    kwargs["secret"] = 1
    with pytest.raises(ValidationError):
        GeneratedScene(**kwargs)


def test_generated_scene_missing_required_rejected():
    kwargs = _valid_generated_scene_kwargs()
    del kwargs["python_source"]
    with pytest.raises(ValidationError):
        GeneratedScene(**kwargs)


def test_generated_scene_attempt_must_be_at_least_one():
    kwargs = _valid_generated_scene_kwargs()
    kwargs["llm_attempt"] = 0
    with pytest.raises(ValidationError):
        GeneratedScene(**kwargs)


# ─── RenderedScene ───────────────────────────────────────────────────────────


def test_rendered_scene_extra_field_rejected():
    kwargs = _valid_rendered_scene_kwargs()
    kwargs["debug"] = "noisy"
    with pytest.raises(ValidationError):
        RenderedScene(**kwargs)


def test_rendered_scene_missing_required_rejected():
    kwargs = _valid_rendered_scene_kwargs()
    del kwargs["mp4_storage_path"]
    with pytest.raises(ValidationError):
        RenderedScene(**kwargs)


def test_rendered_scene_negative_duration_rejected():
    kwargs = _valid_rendered_scene_kwargs()
    kwargs["duration_sec"] = -0.001
    with pytest.raises(ValidationError):
        RenderedScene(**kwargs)


def test_rendered_scene_attempts_below_one_rejected():
    kwargs = _valid_rendered_scene_kwargs()
    kwargs["render_attempts"] = 0
    with pytest.raises(ValidationError):
        RenderedScene(**kwargs)


# ─── AudioOutput ─────────────────────────────────────────────────────────────


def test_audio_output_extra_field_rejected():
    kwargs = _valid_audio_kwargs()
    kwargs["channels"] = 2
    with pytest.raises(ValidationError):
        AudioOutput(**kwargs)


def test_audio_output_missing_required_rejected():
    kwargs = _valid_audio_kwargs()
    del kwargs["audio_storage_path"]
    with pytest.raises(ValidationError):
        AudioOutput(**kwargs)


def test_audio_output_negative_duration_rejected():
    kwargs = _valid_audio_kwargs()
    kwargs["duration_sec"] = -1.0
    with pytest.raises(ValidationError):
        AudioOutput(**kwargs)


def test_audio_output_unknown_provider_rejected():
    kwargs = _valid_audio_kwargs()
    kwargs["provider"] = "festival"  # not in Literal
    with pytest.raises(ValidationError):
        AudioOutput(**kwargs)


# ─── FinalVideo ──────────────────────────────────────────────────────────────


def test_final_video_extra_field_rejected():
    kwargs = _valid_final_video_kwargs()
    kwargs["trailer_path"] = "x"
    with pytest.raises(ValidationError):
        FinalVideo(**kwargs)


def test_final_video_missing_required_rejected():
    kwargs = _valid_final_video_kwargs()
    del kwargs["mp4_storage_path"]
    with pytest.raises(ValidationError):
        FinalVideo(**kwargs)


def test_final_video_scene_count_below_one_rejected():
    kwargs = _valid_final_video_kwargs()
    kwargs["scene_count"] = 0
    with pytest.raises(ValidationError):
        FinalVideo(**kwargs)


def test_final_video_negative_fallback_count_rejected():
    kwargs = _valid_final_video_kwargs()
    kwargs["fallback_scene_count"] = -1
    with pytest.raises(ValidationError):
        FinalVideo(**kwargs)


# ─── Shared sub-models ───────────────────────────────────────────────────────


def test_position_rejects_extra_fields():
    with pytest.raises(ValidationError):
        Position(x=0, y=0, w=1)  # type: ignore[call-arg]


def test_pacing_hints_negative_duration_rejected():
    with pytest.raises(ValidationError):
        PacingHints(estimated_duration_sec=-1.0)


def test_narration_input_missing_pacing_rejected():
    with pytest.raises(ValidationError):
        NarrationInput(text="hi")  # type: ignore[call-arg]
