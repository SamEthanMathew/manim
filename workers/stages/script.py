"""Stage 2 — Script.

Per-scene narration + visual cue descriptions. 3b1b-style: intuition-first,
visual metaphors before formalism. Visual cues are anchored to word indices
so we can re-time them when TTS lands.
"""
from __future__ import annotations

import logging
from pathlib import Path

from workers.lib.errors import ScriptError
from workers.lib.schemas import CurriculumPlan, IngestedDocument, Script, ScriptScene

log = logging.getLogger(__name__)

STYLE_PATH = Path(__file__).parent.parent / "prompts" / "style_guide.md"
PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "script_v2.md"


async def run_script(ctx, plan: CurriculumPlan, ingested: IngestedDocument) -> Script:
    from workers.lib.llm import structured_completion

    style = STYLE_PATH.read_text(encoding="utf-8")
    template = PROMPT_PATH.read_text(encoding="utf-8")

    scenes: list[ScriptScene] = []
    for outline in plan.scene_outline:
        # Find supporting source material from the ingested doc.
        # In v1, we pass the whole doc-context lightly truncated; in Week 6 we'll
        # implement targeted retrieval by concept_id.
        source_context = _select_source_context(ingested, outline.concept_id)

        prompt = template.format(
            scene_id=outline.scene_id,
            concept_name=next((c.name for c in plan.concept_dag
                               if c.concept_id == outline.concept_id), outline.concept_id),
            hook=outline.hook,
            beat_summary=outline.beat_summary,
            estimated_sec=outline.estimated_sec,
            tone_hint=ctx.tone_hint,
            source_context=source_context,
        )

        try:
            scene = await structured_completion(
                ctx=ctx,
                system=style,
                user=prompt,
                schema=ScriptScene,
                max_attempts=3,
            )
        except Exception as e:
            raise ScriptError(f"Script LLM call failed for scene {outline.scene_id}: {e}") from e

        # Force the scene_id to match what curriculum decided (don't trust LLM).
        scene.scene_id = outline.scene_id
        scenes.append(scene)

    return Script(scenes=scenes)


def _select_source_context(doc: IngestedDocument, concept_id: str, max_chars: int = 1500) -> str:
    """Pick relevant chunks of the ingested doc. v1 = naive substring match."""
    needles = concept_id.lower().replace("_", " ").split()
    matched = []
    for s in doc.sections:
        score = sum(1 for n in needles if n in (s.title + " " + s.prose_md).lower())
        if score > 0:
            matched.append((score, s))

    matched.sort(key=lambda x: -x[0])
    out: list[str] = []
    char_count = 0
    for _, s in matched[:5]:
        chunk = f"### {s.title}\n{s.prose_md}"
        if char_count + len(chunk) > max_chars:
            chunk = chunk[: max_chars - char_count]
        out.append(chunk)
        char_count += len(chunk)
        if char_count >= max_chars:
            break

    return "\n\n".join(out) if out else "(no specific section matched)"
