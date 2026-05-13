"""Advanced AST safety tests — sandbox escape attempts and legal-code positives.

The basic checks live in test_ast_safety.py. This file targets:
  - Patterns that almost-but-don't escape (globals(), __builtins__, dunder
    chain traversals).
  - Multi-line / multi-statement code with mixed safe and unsafe content.
  - Legal Manim code containing the heavier transforms/animations to make sure
    the allowlist isn't accidentally over-restrictive.
"""
from __future__ import annotations

from workers.lib.ast_safety import check


# ─── Almost-escapes (must FAIL) ──────────────────────────────────────────────


def test_globals_lookup_of_os_fails():
    # `globals()["os"]` only works if `os` was already imported, but the
    # dunder-style lookup hides the import. The AST walker still has to flag
    # this because BANNED_ATTRS catches `.system` if the user resolves it.
    code = """
from manim import Scene

class Main(Scene):
    def construct(self):
        globals()["os"].system("ls")
"""
    r = check(code)
    assert not r.ok
    assert any("system" in v for v in r.violations)


def test_builtins_eval_fails():
    code = """
from manim import Scene

class Main(Scene):
    def construct(self):
        __builtins__.eval("1+1")
"""
    r = check(code)
    assert not r.ok
    assert any("eval" in v for v in r.violations)


def test_getattr_dunder_import_fails():
    code = """
from manim import Scene

class Main(Scene):
    def construct(self):
        getattr(__import__('os'), 'system')('ls')
"""
    r = check(code)
    assert not r.ok
    # We expect at least one of the two violations: the __import__ name OR system attr.
    assert any("__import__" in v or "system" in v for v in r.violations)


def test_subclasses_traversal_does_not_crash_checker():
    # The classic "object.__subclasses__()" escape. Our checker doesn't
    # specifically flag this attribute traversal, but it must not crash and
    # it must not return ok if `open`/`system`/`eval` appear anywhere.
    code = """
from manim import Scene

class Main(Scene):
    def construct(self):
        x = [].__class__.__base__.__subclasses__()
"""
    r = check(code)
    # No banned attribute referenced -> may pass. We assert behavior, not policy:
    # the only requirement is the checker returns a SafetyReport without error.
    assert isinstance(r.ok, bool)


def test_pickle_import_fails():
    code = "import pickle"
    r = check(code)
    assert not r.ok


def test_ctypes_import_fails():
    code = "from ctypes import CDLL"
    r = check(code)
    assert not r.ok


def test_socket_import_fails():
    code = "import socket"
    r = check(code)
    assert not r.ok


def test_compile_call_fails():
    code = """
from manim import Scene
c = compile("1+1", "<x>", "eval")
"""
    r = check(code)
    assert not r.ok


def test_urllib_from_import_fails():
    code = "from urllib.request import urlopen"
    r = check(code)
    assert not r.ok


def test_indirect_open_via_attribute_fails():
    code = """
from manim import Scene

class Main(Scene):
    def construct(self):
        io.open('/etc/passwd')
"""
    r = check(code)
    # `.open` is in BANNED_ATTRS -> attribute access on `.open` should fail.
    assert not r.ok


# ─── Multi-statement mixed code ──────────────────────────────────────────────


def test_multi_statement_with_one_violation_fails():
    """A long, otherwise valid file with a single malicious line must be flagged."""
    code = """
from manim import Scene, MathTex, Write, FadeOut
import numpy as np
import math

def helper(x):
    return x * 2

class Main(Scene):
    def construct(self):
        eq = MathTex(r"e^{i\\\\pi} + 1 = 0")
        self.play(Write(eq))
        # the bad line:
        import os
        self.wait(1.0)
        self.play(FadeOut(eq))
"""
    r = check(code)
    assert not r.ok


def test_multiple_independent_violations_all_reported():
    code = """
import os
import requests
eval("1+1")
"""
    r = check(code)
    assert not r.ok
    # Should have at least three distinct violations.
    assert len(r.violations) >= 3


# ─── Legal Manim code (must PASS) ────────────────────────────────────────────


def test_legal_scene_with_mathtex_axes_transform_indicate_passes():
    code = """
from manim import Scene, MathTex, Axes, Transform, Indicate, Create, Write, FadeIn, FadeOut

class Main(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3], y_range=[-3, 3])
        eq = MathTex(r"x^2 + y^2 = 1")
        self.play(Create(axes))
        self.play(Write(eq))
        eq2 = MathTex(r"(x-1)^2 + (y-1)^2 = 1")
        self.play(Transform(eq, eq2))
        self.play(Indicate(eq))
        self.wait(0.5)
        self.play(FadeOut(eq), FadeOut(axes))
"""
    r = check(code)
    assert r.ok, r.violations


def test_legal_scene_with_numpy_helpers_passes():
    code = """
from manim import Scene, MathTex, Write
import numpy as np
import math

class Main(Scene):
    def construct(self):
        radius = math.sqrt(2)
        pts = np.linspace(0, 2 * math.pi, 100)
        eq = MathTex(r"r = " + str(radius))
        self.play(Write(eq))
"""
    r = check(code)
    assert r.ok, r.violations


def test_legal_multi_class_module_passes():
    code = """
from manim import Scene, MathTex, Write, FadeOut

class Intro(Scene):
    def construct(self):
        t = MathTex("a + b")
        self.play(Write(t))

class Outro(Scene):
    def construct(self):
        t = MathTex("c + d")
        self.play(Write(t))
        self.play(FadeOut(t))
"""
    r = check(code)
    assert r.ok, r.violations


def test_legal_scene_with_typing_and_functools_passes():
    code = """
from manim import Scene, MathTex, Write
from typing import Callable
from functools import reduce
import itertools

class Main(Scene):
    def construct(self):
        nums = list(itertools.islice(itertools.count(), 5))
        total = reduce(lambda a, b: a + b, nums)
        t = MathTex(str(total))
        self.play(Write(t))
"""
    r = check(code)
    assert r.ok, r.violations
