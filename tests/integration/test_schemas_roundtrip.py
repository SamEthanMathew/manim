"""Schema round-trip tests — ensure JSON serializes/deserializes losslessly.

These tests guard the contract in docs/contracts.md. If they fail, M2 must
review the change.
"""
from __future__ import annotations

import json
from datetime import datetime

import pytest

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


def test_ingested_document_roundtrip():
    doc = IngestedDocument(
        title="Eigenvalues",
        sections=[
            Section(id="sec-0", level=1, title="Intro", prose_md="Hello $x^2$.",
                    equations=["x^2"], figures=[]),
        ],
        metadata=DocumentMetadata(
            page_count=10,
            language="en",
            detected_subject=Subject.MATH,
            source_filename="test.pdf",
            ingested_at=datetime(2026, 5, 12, 12, 0, 0),
        ),
    )
    j = doc.model_dump_json()
    re = IngestedDocument.model_validate_json(j)
    assert re == doc


def test_curriculum_unique_scene_ids():
    with pytest.raises(ValueError, match="duplicate"):
        CurriculumPlan(
            target_duration_sec=600,
            learning_objectives=["understand"],
            concept_dag=[Concept(concept_id="x", name="X")],
            scene_outline=[
                SceneOutline(scene_id="scene-0", concept_id="x", hook="h", beat_summary="b",
                             estimated_sec=30),
                SceneOutline(scene_id="scene-0", concept_id="x", hook="h", beat_summary="b",
                             estimated_sec=30),
            ],
        )


def test_visual_cues_must_be_strictly_increasing():
    with pytest.raises(ValueError, match="strictly increasing"):
        ScriptScene(
            scene_id="scene-0",
            narration_md="hello world",
            visual_cues=[
                VisualCue(at_word_index=5, description="a"),
                VisualCue(at_word_index=3, description="b"),
            ],
            estimated_duration_sec=10,
        )


def test_scene_spec_wait_action_must_have_null_target():
    from workers.lib.schemas import Action

    with pytest.raises(ValueError, match="Wait action"):
        SceneSpec(
            scene_id="scene-0",
            duration_sec=10,
            elements=[],
            timeline=[
                Action(at_t=0, duration_sec=1, action=ActionKind.WAIT, target_id="x", params={}),
            ],
        )


def test_scene_spec_non_wait_requires_target():
    from workers.lib.schemas import Action

    with pytest.raises(ValueError, match="requires target_id"):
        SceneSpec(
            scene_id="scene-0",
            duration_sec=10,
            elements=[],
            timeline=[
                Action(at_t=0, duration_sec=1, action=ActionKind.CREATE, target_id=None, params={}),
            ],
        )


def test_element_discriminated_union():
    spec = SceneSpec(
        scene_id="scene-0",
        duration_sec=10,
        background="#000000",
        elements=[
            MathTexElement(id="m1", latex=r"\sum_i x_i", position=Position(x=0, y=0)),
        ],
        timeline=[],
    )
    j = spec.model_dump_json()
    re = SceneSpec.model_validate_json(j)
    assert re.elements[0].type == "MathTex"
    assert isinstance(re.elements[0], MathTexElement)


def test_final_video_minimal():
    fv = FinalVideo(
        job_id="abc",
        mp4_storage_path="path/to.mp4",
        duration_sec=120,
        scene_count=3,
        fallback_scene_count=0,
    )
    assert fv.has_audio is False
    assert fv.caption_srt_path is None
