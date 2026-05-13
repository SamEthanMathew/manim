"""AST safety check tests — these are the primary defense against generated
code escaping the sandbox.
"""
from __future__ import annotations

from workers.lib.ast_safety import check


def test_normal_manim_scene_passes():
    code = """
from manim import Scene, Text, FadeIn

class Main(Scene):
    def construct(self):
        t = Text("hello")
        self.play(FadeIn(t))
"""
    r = check(code)
    assert r.ok, r.violations


def test_os_import_fails():
    code = """
import os
from manim import Scene

class Main(Scene):
    def construct(self):
        os.system("rm -rf /")
"""
    r = check(code)
    assert not r.ok
    assert any("os" in v for v in r.violations)


def test_subprocess_fails():
    code = """
from subprocess import Popen
"""
    r = check(code)
    assert not r.ok


def test_eval_fails():
    code = """
from manim import Scene
eval("1+1")
"""
    r = check(code)
    assert not r.ok


def test_disallowed_module_fails():
    code = "import requests"
    r = check(code)
    assert not r.ok


def test_open_call_fails():
    code = """
from manim import Scene

class Main(Scene):
    def construct(self):
        f = open("/etc/passwd")
"""
    r = check(code)
    assert not r.ok


def test_dunder_import_fails():
    code = """
m = __import__("os")
"""
    r = check(code)
    assert not r.ok


def test_numpy_alias_allowed():
    code = """
import numpy as np
from manim import Scene

class Main(Scene):
    def construct(self):
        arr = np.array([1, 2, 3])
"""
    r = check(code)
    assert r.ok, r.violations


def test_syntax_error_fails():
    code = "this is not valid python +++"
    r = check(code)
    assert not r.ok
