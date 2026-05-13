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


# ─── Additional idioms ────────────────────────────────────────────────────────


def test_deep_manimlib_import_path_rewritten():
    """3b1b code commonly does `from manimlib.scene.scene import Scene`.
    The translator should rewrite the `manimlib` prefix to `manim`.
    """
    src = "from manimlib.scene.scene import Scene"
    out = translate(src)
    assert "manimlib" not in out
    assert out.startswith("from manim")


def test_mixed_legacy_and_new_constructs_both_translated():
    """A snippet that mixes a deep import path, a TextMobject, a TexMobject,
    and a runtime kwarg should have all four rewritten in one pass.
    """
    src = (
        "from manimlib.imports import *\n"
        "class Demo(GraphScene):\n"
        "    def construct(self):\n"
        "        t = TextMobject('hi')\n"
        "        eq = TexMobject(r'x^2')\n"
        "        self.play(FadeIn(eq), runtime=2.0)\n"
    )
    out = translate(src)
    assert "manimlib" not in out
    assert "GraphScene" not in out
    assert "TextMobject" not in out
    assert "TexMobject" not in out
    assert "runtime=" not in out
    assert "run_time=" in out


def test_import_manimlib_module_rewritten():
    src = "import manimlib"
    out = translate(src)
    assert out == "import manim"


def test_threed_camera_rewritten_to_camera():
    src = "cam = ThreeDCamera()\nmc = MovingCamera()\nmulti = MultiCamera()"
    out = translate(src)
    assert "ThreeDCamera" not in out
    assert "MovingCamera" not in out
    assert "MultiCamera" not in out
    assert out.count("Camera()") == 3


def test_green_screen_constant_rewritten():
    src = "c = GREEN_SCREEN"
    out = translate(src)
    assert "GREEN_SCREEN" not in out
    assert "GREEN" in out


# ─── Known limitations (string/comment safety) ───────────────────────────────


def test_bare_manimlib_in_comment_or_string_is_preserved():
    """The current rules only rewrite `manimlib` in import contexts
    (`from manimlib...`, `import manimlib`). A bare mention of the word
    `manimlib` in a comment or string literal is left alone.
    """
    src = '# This references manimlib in a comment\nmsg = "the manimlib repo is great"'
    out = translate(src)
    assert out == src, "Bare 'manimlib' tokens should be untouched"


def test_import_string_inside_string_literal_is_still_rewritten_known_limitation():
    """Known limitation: the translator is a flat regex pass and does not
    distinguish source code from string literals. An `import manimlib`
    inside a docstring or string literal WILL be rewritten.

    Documented in coordination/blockers.md (B-008). Not fixed here.
    """
    src = 'doc = """example: from manimlib import *"""'
    out = translate(src)
    # The rule fires inside the string literal — surfacing the known limitation.
    assert "from manim import *" in out
    assert "from manimlib" not in out
