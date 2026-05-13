"""Modal application entry point.

Defines:
  - The Modal app + image
  - Secret bindings
  - Top-level functions invoked by the Vercel API
  - Per-scene fan-out function (`render_one_scene`)

Deploy:  modal deploy workers/app.py
Dev:     modal serve  workers/app.py
"""
from __future__ import annotations

import asyncio

import modal
from fastapi import Header  # used in the trigger endpoint signature

# ─── Images ───────────────────────────────────────────────────────────────────
#
# Two images:
#  - base_image: minimal — for trigger endpoint, orchestrator, LLM stages.
#    Builds in ~60s. Used by run_pipeline + render_one_scene's outer wrapper.
#  - render_image: base + LaTeX + Manim + ffmpeg. Heavy (~1.5GB). Built lazily
#    on first invocation of the Sandbox; doesn't block initial deploy.
#
# This split exists because Modal's free-tier image builder times out on the
# combined texlive+Manim+pip-PyTorch install. Splitting unblocks deploys.

base_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install(
        "qpdf",                  # PDF sanitization (small, fast)
        "git",                   # corpus indexer clones 3b1b
    )
    .pip_install(
        "pydantic>=2.7.0",
        "supabase>=2.7.0",
        "openai>=1.40.0",
        "anthropic>=0.34.0",
        "voyageai>=0.2.0",
        "tenacity>=8.2.0",
        "structlog>=24.1.0",
        "cryptography>=42.0.0",
        "pdfplumber>=0.11.0",
        "fastapi[standard]>=0.115.0",
        "sentry-sdk>=2.0.0",
    )
    .add_local_dir("workers", remote_path="/root/workers")
    .add_local_dir("src", remote_path="/root/src")
    .add_local_dir("tests", remote_path="/root/tests")
)

# Heavier image used inside modal.Sandbox for actual Manim rendering.
# Defined here for visibility; the Sandbox primitive builds it on first use.
render_image = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install(
        "texlive",
        "texlive-latex-extra",
        "texlive-fonts-recommended",
        "texlive-science",
        "dvipng",
        "dvisvgm",
        "ffmpeg",
        "libcairo2-dev",
        "libpango1.0-dev",
        "pkg-config",
        "fonts-noto",
    )
    .pip_install(
        "manim>=0.18.0",
        "numpy>=1.26.0",
        "Pillow>=10.0.0",
    )
)

# Default image used by all @app.function decorations below.
image = base_image

# ─── App ──────────────────────────────────────────────────────────────────────

app = modal.App(
    name="manim",
    image=image,
    secrets=[
        modal.Secret.from_name("supabase"),         # SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
        modal.Secret.from_name("byok-encryption"),  # BYOK_ENCRYPTION_KEY
        modal.Secret.from_name("observability"),    # SENTRY_DSN, AXIOM_TOKEN, AXIOM_DATASET
        modal.Secret.from_name("trigger"),          # MODAL_TRIGGER_SECRET, VOYAGE_API_KEY
    ],
)


# ─── Top-level function: run a full job pipeline ──────────────────────────────


@app.function(
    timeout=3600,
    memory=4096,
    cpu=2,
)
async def run_pipeline(job_id: str) -> dict:
    """Entry point. Vercel API calls this with .spawn(job_id) on upload.

    The function does not receive API keys directly — it fetches the user's
    encrypted keys from the DB using the job_id -> user_id lookup, then
    decrypts using the server-side BYOK_ENCRYPTION_KEY secret.
    """
    from workers.lib.obs import init_observability, set_job_context, capture_exception
    from workers.pipeline import Pipeline

    init_observability()
    set_job_context(job_id=job_id)
    try:
        return await Pipeline.run(job_id)
    except Exception as e:
        capture_exception(e, job_id=job_id)
        raise


# ─── Per-scene fan-out function ───────────────────────────────────────────────


@app.function(
    timeout=900,
    memory=8192,
    cpu=4,
)
def render_one_scene(scene_payload: dict) -> dict:
    """Render a single scene. Invoked via `.map()` from the pipeline.

    Runs in its own container, parallel to other scenes. Internally uses
    `modal.Sandbox` to actually execute LLM-generated code.
    """
    from workers.lib.obs import init_observability, set_job_context, capture_exception
    from workers.stages.render import render_scene_sync

    init_observability()
    set_job_context(
        job_id=scene_payload.get("job_id"),
        scene_id=scene_payload.get("script_scene", {}).get("scene_id"),
    )
    try:
        return render_scene_sync(scene_payload)
    except Exception as e:
        capture_exception(e, scene_payload_summary={
            "job_id": scene_payload.get("job_id"),
            "scene_id": scene_payload.get("script_scene", {}).get("scene_id"),
            "scene_index": scene_payload.get("scene_index"),
        })
        raise


# ─── Web endpoint — Vercel API spawn target ───────────────────────────────────


@app.function(timeout=30)
@modal.fastapi_endpoint(method="POST", label="trigger")
def trigger(
    payload: dict,
    x_trigger_secret: str | None = Header(default=None, alias="x-trigger-secret"),
) -> dict:
    """HTTPS endpoint Vercel calls to spawn a pipeline.

    Authenticated by a shared secret header (`x-trigger-secret`) checked
    against MODAL_TRIGGER_SECRET. Symmetric trust: same secret lives in
    Vercel env (caller side) and Modal secrets (callee side).
    """
    import os

    expected = os.environ.get("MODAL_TRIGGER_SECRET")
    if not expected or x_trigger_secret != expected:
        return {"error": "unauthorized"}

    job_id = payload.get("job_id")
    if not job_id:
        return {"error": "missing job_id"}

    call = run_pipeline.spawn(job_id)
    return {"ok": True, "modal_call_id": call.object_id}


# ─── Render image smoke test ──────────────────────────────────────────────────
#
# Forces render_image to build at deploy time (otherwise it builds lazily on
# first sandbox spawn — which means the first real user upload waits ~10 min).
# Also gives us a direct way to verify a known-good Manim scene renders
# correctly without going through the LLM stages.


@app.function(image=render_image, timeout=600, memory=4096, cpu=2)
def render_smoke_test() -> dict:
    """Render a hand-written Manim scene end-to-end.

    Validates: image build, Manim install, LaTeX install, ffmpeg, file I/O.
    Returns metadata + a bool. Does NOT exercise sandbox isolation — that's
    a separate test in render_smoke_sandbox below.
    """
    import subprocess
    import tempfile
    from pathlib import Path

    scene_code = '''
from manim import Scene, MathTex, Create, FadeIn, FadeOut, Write

class Main(Scene):
    def construct(self):
        eq = MathTex(r"e^{i\\\\pi} + 1 = 0")
        self.play(Write(eq))
        self.wait(1.0)
        self.play(FadeOut(eq))
'''

    with tempfile.TemporaryDirectory() as tmp:
        scene_path = Path(tmp) / "scene.py"
        scene_path.write_text(scene_code)

        result = subprocess.run(
            [
                "python", "-m", "manim",
                "-ql",
                "--media_dir", tmp,
                "--disable_caching",
                str(scene_path),
                "Main",
            ],
            capture_output=True,
            text=True,
            cwd=tmp,
            timeout=300,
        )

        mp4s = list(Path(tmp).rglob("*.mp4"))
        ok = result.returncode == 0 and len(mp4s) > 0

        return {
            "ok": ok,
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-2000:],
            "stderr_tail": result.stderr[-2000:],
            "mp4_count": len(mp4s),
            "mp4_size_bytes": mp4s[0].stat().st_size if mp4s else 0,
        }


@app.function(image=base_image, timeout=900, memory=2048, cpu=2)
def render_smoke_sandbox() -> dict:
    """Same Manim scene, but run INSIDE modal.Sandbox.

    Validates the sandbox path that real renders take: AST safety, block_network,
    resource caps, mp4 retrieval through the sandbox boundary.
    """
    from workers.lib.config import WorkerConfig
    from workers.lib.sandbox import run_manim_scene

    scene_code = '''
from manim import Scene, MathTex, Write, FadeOut

class Main(Scene):
    def construct(self):
        eq = MathTex(r"e^{i\\\\pi} + 1 = 0")
        self.play(Write(eq))
        self.wait(1.0)
        self.play(FadeOut(eq))
'''

    cfg = WorkerConfig.from_env()
    result = run_manim_scene(cfg, scene_code, sandbox_image=render_image)

    return {
        "ok": result.ok,
        "exit_code": result.exit_code,
        "duration_sec": result.duration_sec,
        "error_class": result.error_class,
        "mp4_size": len(result.mp4_bytes) if result.mp4_bytes else 0,
        "stderr_tail": result.stderr[-2000:] if result.stderr else "",
    }


@app.function(image=base_image, timeout=900, memory=2048, cpu=2)
def render_fixture(fixture_name: str) -> dict:
    """Render a specific fixture from tests/render_fixtures/fixtures.py.

    Use to validate that the reference Manim code for a fixture renders
    cleanly through the sandbox path.
    """
    import sys
    sys.path.insert(0, "/root")
    from tests.render_fixtures.fixtures import ALL_FIXTURES
    from workers.lib.config import WorkerConfig
    from workers.lib.sandbox import run_manim_scene

    fixture = next((f for f in ALL_FIXTURES if f.name == fixture_name), None)
    if not fixture:
        return {
            "ok": False,
            "error": f"unknown fixture: {fixture_name}",
            "available": [f.name for f in ALL_FIXTURES],
        }

    cfg = WorkerConfig.from_env()
    result = run_manim_scene(cfg, fixture.reference_code, sandbox_image=render_image)

    return {
        "ok": result.ok,
        "fixture": fixture.name,
        "description": fixture.description,
        "exit_code": result.exit_code,
        "duration_sec": result.duration_sec,
        "error_class": result.error_class,
        "mp4_size": len(result.mp4_bytes) if result.mp4_bytes else 0,
        "stderr_tail": result.stderr[-2000:] if result.stderr else "",
    }


# ─── Local dev entry point ────────────────────────────────────────────────────


@app.local_entrypoint()
def main(job_id: str = "test-job"):
    """For `modal run workers/app.py --job-id <uuid>`."""
    result = asyncio.run(run_pipeline.local(job_id))
    print(result)
