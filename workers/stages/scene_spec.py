"""Stage 3 — Scene Spec.

Converts a fuzzy ScriptScene (English narration + visual cue descriptions)
into a strictly-typed SceneSpec that the codegen stage can target.

Retry up to 3 times on Pydantic validation failure, with validation errors
echoed back into the prompt.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError

from workers.lib.errors import SceneSpecError
from workers.lib.schemas import SceneSpec, ScriptScene

log = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "scene_spec_v1.md"


async def run_scene_spec(ctx, scene: ScriptScene) -> SceneSpec:
    from workers.lib.llm import structured_completion

    template = PROMPT_PATH.read_text(encoding="utf-8")
    cues = "\n".join(f"- @ word {c.at_word_index}: {c.description}" for c in scene.visual_cues)

    prompt = template.format(
        scene_id=scene.scene_id,
        narration=scene.narration_md,
        visual_cues=cues or "(no specific cues — design freely)",
        estimated_duration_sec=scene.estimated_duration_sec,
    )

    try:
        spec = await structured_completion(
            ctx=ctx,
            system="You convert English visual descriptions into strict Manim scene specs.",
            user=prompt,
            schema=SceneSpec,
            max_attempts=3,
        )
    except ValidationError as e:
        raise SceneSpecError(f"Could not validate SceneSpec for {scene.scene_id}: {e}") from e
    except Exception as e:
        raise SceneSpecError(f"Scene spec LLM call failed: {e}") from e

    # Force scene_id to match what the script set.
    spec.scene_id = scene.scene_id
    return spec
