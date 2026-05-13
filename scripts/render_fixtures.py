"""Render the hand-written fixtures through the sandbox pipeline.

Use this to validate the render path without spending LLM money. It runs
each fixture's reference Manim code (NOT LLM output) through `run_manim_scene`
and reports per-fixture pass/fail.

Run:
  modal run workers/app.py::render_fixtures_entry  (not yet defined)
or locally with Modal calling render_smoke_test repeatedly.

For now this is a documentation/staging script — actual fixture rendering
will be wired in via the Modal CLI once the render_image deploy succeeds.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.render_fixtures.fixtures import ALL_FIXTURES  # noqa: E402


def main() -> int:
    print(f"Loaded {len(ALL_FIXTURES)} fixtures:")
    for f in ALL_FIXTURES:
        print(f"  - {f.name}: {len(f.spec.elements)} elements, {len(f.spec.timeline)} actions")
        print(f"      {f.description}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
