"""Hand-written SceneSpec + reference Manim code pairs.

These fixtures exist for two reasons:
  1. Validate the render pipeline without burning LLM tokens on codegen
  2. Serve as the golden baseline for measuring codegen quality (compare
     LLM-generated code's render outcome against the reference's)

Each fixture has a SceneSpec that, when correctly translated, should produce
the reference Manim code in scene_code.
"""
from __future__ import annotations

from dataclasses import dataclass

from workers.lib.schemas import (
    Action,
    ActionKind,
    AxesElement,
    CircleElement,
    GraphElement,
    GroupElement,
    MathTexElement,
    Position,
    SceneSpec,
    TextElement,
    VectorElement,
)


@dataclass
class RenderFixture:
    """A hand-paired SceneSpec + reference Manim code."""
    name: str
    description: str
    spec: SceneSpec
    reference_code: str


# ─── F1: Euler's identity, the simplest possible MathTex render ────────────────

f1_eulers_identity = RenderFixture(
    name="eulers_identity",
    description="Single MathTex equation, written then faded. Minimum viable render.",
    spec=SceneSpec(
        scene_id="f1",
        duration_sec=4.0,
        background="#000000",
        elements=[
            MathTexElement(id="eq", latex=r"e^{i\pi} + 1 = 0",
                           position=Position(x=0, y=0), scale=1.5),
        ],
        timeline=[
            Action(at_t=0.0, duration_sec=1.5, action=ActionKind.WRITE, target_id="eq"),
            Action(at_t=1.5, duration_sec=1.0, action=ActionKind.WAIT, target_id=None),
            Action(at_t=2.5, duration_sec=1.0, action=ActionKind.FADE_OUT, target_id="eq"),
        ],
    ),
    reference_code='''
from manim import Scene, MathTex, Write, FadeOut

class Main(Scene):
    def construct(self):
        eq = MathTex(r"e^{i\\pi} + 1 = 0").scale(1.5)
        self.play(Write(eq), run_time=1.5)
        self.wait(1.0)
        self.play(FadeOut(eq), run_time=1.0)
''',
)


# ─── F2: Title text + math, sequential reveal ─────────────────────────────────

f2_title_and_equation = RenderFixture(
    name="title_and_equation",
    description="Title text fades in, then math appears below, then both fade out.",
    spec=SceneSpec(
        scene_id="f2",
        duration_sec=5.0,
        background="#000000",
        elements=[
            TextElement(id="title", text="Pythagorean theorem",
                        position=Position(x=0, y=2), scale=1.0, font=None),
            MathTexElement(id="eq", latex=r"a^2 + b^2 = c^2",
                           position=Position(x=0, y=0), scale=1.5),
        ],
        timeline=[
            Action(at_t=0.0, duration_sec=1.0, action=ActionKind.FADE_IN, target_id="title"),
            Action(at_t=1.0, duration_sec=1.5, action=ActionKind.WRITE, target_id="eq"),
            Action(at_t=2.5, duration_sec=1.0, action=ActionKind.WAIT, target_id=None),
            Action(at_t=3.5, duration_sec=0.75, action=ActionKind.FADE_OUT, target_id="title"),
            Action(at_t=4.25, duration_sec=0.75, action=ActionKind.FADE_OUT, target_id="eq"),
        ],
    ),
    reference_code='''
from manim import Scene, Text, MathTex, FadeIn, Write, FadeOut

class Main(Scene):
    def construct(self):
        title = Text("Pythagorean theorem").move_to([0, 2, 0])
        eq = MathTex(r"a^2 + b^2 = c^2").scale(1.5)
        self.play(FadeIn(title), run_time=1.0)
        self.play(Write(eq), run_time=1.5)
        self.wait(1.0)
        self.play(FadeOut(title), run_time=0.75)
        self.play(FadeOut(eq), run_time=0.75)
''',
)


# ─── F3: Axes + a parabola graph ───────────────────────────────────────────────

f3_parabola_graph = RenderFixture(
    name="parabola_graph",
    description="Axes appear, then a parabola is drawn on them.",
    spec=SceneSpec(
        scene_id="f3",
        duration_sec=4.0,
        background="#000000",
        elements=[
            AxesElement(id="axes", x_range=(-3.0, 3.0, 1.0), y_range=(0.0, 9.0, 1.0),
                        position=Position(x=0, y=-0.5), scale=0.7),
            GraphElement(id="parabola", function="x**2",
                         x_range=(-3.0, 3.0), axes_id="axes"),
        ],
        timeline=[
            Action(at_t=0.0, duration_sec=1.0, action=ActionKind.CREATE, target_id="axes"),
            Action(at_t=1.0, duration_sec=2.0, action=ActionKind.CREATE, target_id="parabola"),
            Action(at_t=3.0, duration_sec=1.0, action=ActionKind.WAIT, target_id=None),
        ],
    ),
    reference_code='''
from manim import Scene, Axes, Create

class Main(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3, 1], y_range=[0, 9, 1]).scale(0.7).shift([0, -0.5, 0])
        self.play(Create(axes), run_time=1.0)
        parabola = axes.plot(lambda x: x**2, x_range=[-3, 3])
        self.play(Create(parabola), run_time=2.0)
        self.wait(1.0)
''',
)


# ─── F4: Vector rotation with Indicate ─────────────────────────────────────────

f4_vector_indicate = RenderFixture(
    name="vector_indicate",
    description="A vector appears, then gets highlighted with Indicate.",
    spec=SceneSpec(
        scene_id="f4",
        duration_sec=4.0,
        background="#000000",
        elements=[
            VectorElement(id="v", components=[2.0, 1.0], color="#3498DB", anchor_id=None),
        ],
        timeline=[
            Action(at_t=0.0, duration_sec=1.0, action=ActionKind.CREATE, target_id="v"),
            Action(at_t=1.0, duration_sec=1.0, action=ActionKind.WAIT, target_id=None),
            Action(at_t=2.0, duration_sec=1.0, action=ActionKind.INDICATE, target_id="v",
                   params={"color": "#FFFF00", "scale_factor": 1.3}),
            Action(at_t=3.0, duration_sec=1.0, action=ActionKind.WAIT, target_id=None),
        ],
    ),
    reference_code='''
from manim import Scene, Vector, Create, Indicate, YELLOW

class Main(Scene):
    def construct(self):
        v = Vector([2, 1], color="#3498DB")
        self.play(Create(v), run_time=1.0)
        self.wait(1.0)
        self.play(Indicate(v, color="#FFFF00", scale_factor=1.3), run_time=1.0)
        self.wait(1.0)
''',
)


# ─── F5: Circle to square transform ────────────────────────────────────────────

f5_circle_to_square = RenderFixture(
    name="circle_morphs",
    description="Circle appears, then transforms into a different circle (via Transform).",
    spec=SceneSpec(
        scene_id="f5",
        duration_sec=4.0,
        background="#000000",
        elements=[
            CircleElement(id="c1", radius=1.0, position=Position(x=-2, y=0),
                          color="#3498DB", fill_opacity=0.3),
            CircleElement(id="c2", radius=1.5, position=Position(x=2, y=0),
                          color="#E74C3C", fill_opacity=0.5),
        ],
        timeline=[
            Action(at_t=0.0, duration_sec=1.0, action=ActionKind.CREATE, target_id="c1"),
            Action(at_t=1.0, duration_sec=1.0, action=ActionKind.WAIT, target_id=None),
            Action(at_t=2.0, duration_sec=1.5, action=ActionKind.TRANSFORM, target_id="c1",
                   params={"to_id": "c2"}),
            Action(at_t=3.5, duration_sec=0.5, action=ActionKind.WAIT, target_id=None),
        ],
    ),
    reference_code='''
from manim import Scene, Circle, Create, Transform

class Main(Scene):
    def construct(self):
        c1 = Circle(radius=1.0, color="#3498DB", fill_opacity=0.3).move_to([-2, 0, 0])
        c2 = Circle(radius=1.5, color="#E74C3C", fill_opacity=0.5).move_to([2, 0, 0])
        self.play(Create(c1), run_time=1.0)
        self.wait(1.0)
        self.play(Transform(c1, c2), run_time=1.5)
        self.wait(0.5)
''',
)


# ─── F6: Multi-element group (eigenvector scene preview) ───────────────────────

f6_eigenvector_preview = RenderFixture(
    name="eigenvector_preview",
    description="Axes + 2 vectors + label — closer to a real 3b1b scene.",
    spec=SceneSpec(
        scene_id="f6",
        duration_sec=6.0,
        background="#000000",
        elements=[
            AxesElement(id="axes", x_range=(-3.0, 3.0, 1.0), y_range=(-2.0, 2.0, 1.0),
                        position=Position(x=0, y=0), scale=0.6),
            VectorElement(id="v1", components=[2.0, 1.0], color="#FFFF00", anchor_id=None),
            VectorElement(id="v2", components=[1.0, -1.0], color="#3498DB", anchor_id=None),
            TextElement(id="label", text="eigenvectors",
                        position=Position(x=0, y=-2.5), scale=0.8, font=None),
        ],
        timeline=[
            Action(at_t=0.0, duration_sec=1.0, action=ActionKind.CREATE, target_id="axes"),
            Action(at_t=1.0, duration_sec=1.0, action=ActionKind.CREATE, target_id="v1"),
            Action(at_t=2.0, duration_sec=1.0, action=ActionKind.CREATE, target_id="v2"),
            Action(at_t=3.0, duration_sec=1.0, action=ActionKind.FADE_IN, target_id="label"),
            Action(at_t=4.0, duration_sec=2.0, action=ActionKind.WAIT, target_id=None),
        ],
    ),
    reference_code='''
from manim import Scene, Axes, Vector, Text, Create, FadeIn

class Main(Scene):
    def construct(self):
        axes = Axes(x_range=[-3, 3, 1], y_range=[-2, 2, 1]).scale(0.6)
        self.play(Create(axes), run_time=1.0)
        v1 = Vector([2, 1], color="#FFFF00")
        self.play(Create(v1), run_time=1.0)
        v2 = Vector([1, -1], color="#3498DB")
        self.play(Create(v2), run_time=1.0)
        label = Text("eigenvectors").scale(0.8).move_to([0, -2.5, 0])
        self.play(FadeIn(label), run_time=1.0)
        self.wait(2.0)
''',
)


ALL_FIXTURES: list[RenderFixture] = [
    f1_eulers_identity,
    f2_title_and_equation,
    f3_parabola_graph,
    f4_vector_indicate,
    f5_circle_to_square,
    f6_eigenvector_preview,
]
