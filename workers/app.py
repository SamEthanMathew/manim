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
    )
    .add_local_dir("workers", remote_path="/root/workers")
    .add_local_dir("src", remote_path="/root/src")
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

# Imports that only need to resolve inside the container (not on local CLI).
with image.imports():
    from fastapi import Header

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
    # Local import so the module is only loaded inside the Modal container.
    from workers.pipeline import Pipeline

    return await Pipeline.run(job_id)


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
    from workers.stages.render import render_scene_sync

    return render_scene_sync(scene_payload)


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


# ─── Local dev entry point ────────────────────────────────────────────────────


@app.local_entrypoint()
def main(job_id: str = "test-job"):
    """For `modal run modal/app.py --job-id <uuid>`."""
    result = asyncio.run(run_pipeline.local(job_id))
    print(result)
