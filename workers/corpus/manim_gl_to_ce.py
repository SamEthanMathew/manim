"""ManimGL -> ManimCE translation map.

3b1b's repo uses ManimGL (Grant's personal fork). Our render stack is ManimCE.
This module rewrites the most common syntactic differences at index time, so
the LLM sees ManimCE-compatible reference snippets.

Coverage targets the top-20 idioms by frequency. Not exhaustive; the LLM is
robust to remaining differences. Track misses in Week 6 audits.
"""
from __future__ import annotations

import re

# Each (pattern, replacement) is applied in order. Order matters for some
# rewrites (e.g., Tex -> MathTex before TextMobject).
RULES: list[tuple[re.Pattern[str], str]] = [
    # Imports
    (re.compile(r"\bfrom manimlib import \*\b"), "from manim import *"),
    (re.compile(r"\bfrom manimlib\b"), "from manim"),
    (re.compile(r"\bimport manimlib\b"), "import manim"),

    # Class renames
    (re.compile(r"\bTextMobject\b"), "Tex"),
    (re.compile(r"\bTexMobject\b"), "MathTex"),
    (re.compile(r"\bOldTex\b"), "Tex"),
    (re.compile(r"\bSingleStringTex\b"), "MathTex"),

    # play arg name `runtime` -> `run_time` (CE uses run_time)
    (re.compile(r"runtime\s*=\s*"), "run_time="),

    # GraphScene patterns -> Axes-based equivalents (LLM handles the rest)
    (re.compile(r"\bclass\s+(\w+)\s*\(\s*GraphScene\s*\)"), r"class \1(Scene)"),

    # Common color renames where CE uses different constants
    (re.compile(r"\bBLUE_E\b"), "BLUE_E"),  # exists in both; placeholder for symmetry
    (re.compile(r"\bRED_E\b"), "RED_E"),
    (re.compile(r"\bGREEN_SCREEN\b"), "GREEN"),

    # Camera / config differences are usually scene-level; the LLM can handle.
    # Remove ManimGL-only camera class hints that don't exist in CE:
    (re.compile(r"\b(ThreeDCamera|MovingCamera|MultiCamera)\b"), "Camera"),

    # Tex/MathTex constructor: ManimGL allows positional bare strings; CE same.
    # No rewrite needed.

    # Wait: CE uses self.wait(t); ManimGL accepts the same. No-op.
]


def translate(code: str) -> str:
    """Apply all rules in order. Return rewritten source."""
    out = code
    for pattern, replacement in RULES:
        out = pattern.sub(replacement, out)
    return out


__all__ = ["translate"]
