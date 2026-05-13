"""Tests for the ManimGL -> ManimCE idiom translator."""
from __future__ import annotations

from workers.corpus.manim_gl_to_ce import translate


def test_textmobject_to_tex():
    src = "t = TextMobject('hello')"
    assert "Tex(" in translate(src) and "TextMobject" not in translate(src)


def test_texmobject_to_mathtex():
    src = "t = TexMobject(r'\\\\sum_i x_i')"
    assert "MathTex(" in translate(src) and "TexMobject" not in translate(src)


def test_runtime_renamed():
    src = "self.play(FadeIn(t), runtime=1.0)"
    assert "run_time=" in translate(src)


def test_manimlib_import_rewritten():
    src = "from manimlib import *"
    assert translate(src) == "from manim import *"


def test_graphscene_subclass_replaced():
    src = "class Demo(GraphScene):\n    pass"
    assert "class Demo(Scene)" in translate(src)
