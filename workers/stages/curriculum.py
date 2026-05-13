"""Stage 1 — Curriculum.

Takes an IngestedDocument and produces a CurriculumPlan that REORDERS for pedagogy.
The planner's job: pick concrete hooks per concept (concrete -> abstract),
chain prerequisites correctly, and budget time to fit target_duration_sec.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from workers.lib.errors import CurriculumError
from workers.lib.schemas import CurriculumPlan, IngestedDocument

log = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "curriculum_v2.md"


async def run_curriculum(ctx, ingested: IngestedDocument) -> CurriculumPlan:
    from workers.lib.llm import structured_completion

    prompt = _build_prompt(ingested, ctx.target_duration_sec, ctx.tone_hint)

    try:
        plan = await structured_completion(
            ctx=ctx,
            system=PROMPT_PATH.read_text(encoding="utf-8"),
            user=prompt,
            schema=CurriculumPlan,
            max_attempts=3,
        )
    except Exception as e:
        raise CurriculumError(f"Curriculum LLM call failed: {e}") from e

    return plan


def _build_prompt(doc: IngestedDocument, target_sec: int, tone: str) -> str:
    sections_summary = "\n".join(
        f"- [{s.id}] L{s.level} {s.title}: {_truncate(s.prose_md, 240)}"
        for s in doc.sections
    )
    return f"""Document title: {doc.title}
Detected subject: {doc.metadata.detected_subject}
Total pages: {doc.metadata.page_count}
Target video duration: {target_sec} seconds
Tone hint: {tone}

Sections (from the PDF, in original order):
{sections_summary}

Task: Produce a CurriculumPlan that REORDERS for pedagogy, not document order.
For each concept, pick a concrete hook (puzzle, example, or surprise) before
the formal definition. Build prerequisites. Budget time to fit the target.

Respond with JSON matching the CurriculumPlan schema.
"""


def _truncate(s: str, n: int) -> str:
    s = s.strip().replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"
