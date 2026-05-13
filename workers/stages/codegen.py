"""Stage 4 — Codegen.

SceneSpec + retrieved 3b1b examples -> Manim Python source code.

Uses RAG over the indexed 3b1b corpus + ManimCE API reference snippets.
The prompt explicitly directs the LLM to TRANSFORM patterns, not copy verbatim.

Caching: hash(SceneSpec) -> code (skip the LLM call if seen before).
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

from workers.lib.errors import CodegenError
from workers.lib.schemas import GeneratedScene, SceneSpec

log = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "codegen_v1.md"
REPAIR_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "codegen_repair_v1.md"


def spec_hash(spec: SceneSpec) -> str:
    """Stable hash for cache lookup."""
    return hashlib.sha256(spec.model_dump_json(exclude={"scene_id"}).encode()).hexdigest()[:16]


async def generate_code(ctx, spec: SceneSpec, *, attempt: int = 1,
                        prior_code: str | None = None,
                        prior_error: str | None = None) -> GeneratedScene:
    """Generate Manim code for a scene spec.

    On retry, prior_code + prior_error are echoed back via the repair prompt.
    """
    from workers.corpus.retriever import retrieve_similar
    from workers.lib.llm import text_completion

    # Skip RAG on repair attempts — we want focused error-fix, not new context.
    if attempt == 1:
        examples = retrieve_similar(ctx.supabase, spec, top_k=5)
        prompt = _build_initial_prompt(spec, examples)
        system = PROMPT_PATH.read_text(encoding="utf-8")
    else:
        prompt = _build_repair_prompt(spec, prior_code or "", prior_error or "")
        system = REPAIR_PROMPT_PATH.read_text(encoding="utf-8")

    try:
        code = await text_completion(
            ctx=ctx,
            system=system,
            user=prompt,
            stop=None,
        )
    except Exception as e:
        raise CodegenError(f"Codegen LLM call failed: {e}") from e

    code = _strip_code_fences(code)
    imports = _extract_imports(code)

    return GeneratedScene(
        scene_id=spec.scene_id,
        python_source=code,
        imports=imports,
        llm_model=ctx.user_keys.preferred_model,
        llm_attempt=attempt,
        generated_at=datetime.utcnow(),
    )


def _build_initial_prompt(spec: SceneSpec, examples: list[dict]) -> str:
    examples_block = "\n\n---\n\n".join(
        f"### Example from {ex['source']} ({ex.get('scene_name', 'unnamed')})\n"
        f"Description: {ex.get('description', '')}\n```python\n{ex['code']}\n```"
        for ex in examples
    )

    return f"""SceneSpec (target):
```json
{spec.model_dump_json(indent=2)}
```

Reference examples (use as inspiration for patterns; do not copy verbatim):
{examples_block}

Produce a single Python file defining `class Main(Scene):` that, when run with
`manim -ql`, renders the scene described by the SceneSpec.

Constraints:
  - ManimCE syntax (NOT ManimGL).
  - Allowed imports only: manim, numpy, math, random, itertools, functools, typing.
  - No file I/O, no os/subprocess/sys, no network.
  - `Main.construct(self)` must produce visual content matching the spec's
    elements + timeline.

Return ONLY the Python source — no markdown fences, no commentary.
"""


def _build_repair_prompt(spec: SceneSpec, prior_code: str, prior_error: str) -> str:
    return f"""Previous attempt at this SceneSpec produced an error.

SceneSpec:
```json
{spec.model_dump_json(indent=2)}
```

Previous code:
```python
{prior_code}
```

Error (last 50 lines of traceback):
```
{prior_error}
```

Produce a corrected version of the Manim file. Same constraints as before:
ManimCE, allowlisted imports only, no I/O, define class Main(Scene).

Return ONLY the corrected Python source. No fences, no commentary.
"""


def _strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        # remove first line (```python or ```) and trailing ```
        s = "\n".join(s.splitlines()[1:])
        if s.rstrip().endswith("```"):
            s = s.rstrip()[:-3]
    return s.strip()


def _extract_imports(source: str) -> list[str]:
    import ast
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            out.append(node.module)
    return out
