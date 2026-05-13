"""Modal Sandbox wrapper for executing LLM-generated Manim code.

Hardening (defense in depth):
  - AST allowlist check (modal.lib.ast_safety) BEFORE sandbox spawn.
  - block_network=True — no egress.
  - CPU=4, memory=8 GiB, timeout=render_timeout_sec.
  - Read-only baseline; scratch tmpfs at /scene.
  - Non-root user inside the sandbox image (set in image definition).

Returns a SandboxResult that carries enough information to either
upload the produced MP4 or feed the traceback back into codegen-repair.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import modal

from workers.lib.ast_safety import check as ast_check
from workers.lib.config import WorkerConfig
from workers.lib.errors import SandboxViolation

log = logging.getLogger(__name__)

SANDBOX_SCENE_PATH = "/scene/scene.py"
SANDBOX_MEDIA_DIR = "/scene/media"


@dataclass
class SandboxResult:
    ok: bool
    mp4_bytes: bytes | None
    stdout: str
    stderr: str
    exit_code: int
    duration_sec: float
    error_class: str | None = None    # SyntaxError|ImportError|ManimError|LaTeXError|TimeoutError|Other
    traceback: str | None = None


def run_manim_scene(
    cfg: WorkerConfig,
    code: str,
    *,
    sandbox_image: modal.Image,
    scene_class: str = "Main",
) -> SandboxResult:
    """Run a Manim scene file.

    AST safety gate runs first regardless of mode. Mode is selected by
    env var `RENDER_USE_SANDBOX`:
      - "1": modal.Sandbox (proper isolation). Currently has a lifecycle
             issue tracked in B-010; sandbox dies before exec.
      - "0" (default): subprocess.run inside the worker container.
             Weaker isolation but functional.
    """
    import os
    safety = ast_check(code)
    if not safety.ok:
        raise SandboxViolation(
            f"AST safety check failed: {safety.violations}",
            payload={"violations": safety.violations},
        )

    import time
    started = time.time()

    use_sandbox = os.getenv("RENDER_USE_SANDBOX", "0") == "1"
    if not use_sandbox:
        return _run_in_process(code, scene_class, cfg.render_timeout_sec, started)

    sb = modal.Sandbox.create(
        image=sandbox_image,
        block_network=True,
        cpu=4.0,
        memory=8192,
        timeout=cfg.render_timeout_sec,
    )

    try:
        # Write the code
        sb.exec("mkdir", "-p", "/scene").wait()
        proc = sb.exec("tee", SANDBOX_SCENE_PATH)
        proc.stdin.write(code)
        proc.stdin.write_eof()
        proc.wait()

        # Render
        # manim -ql = quality low (480p15) — fast iteration. Bump to -qm or -qh at compose time
        # if we want higher final res; first pass is always low.
        render = sb.exec(
            "python", "-m", "manim",
            "-ql",
            "--media_dir", SANDBOX_MEDIA_DIR,
            "--disable_caching",
            SANDBOX_SCENE_PATH,
            scene_class,
        )
        stdout = render.stdout.read()
        stderr = render.stderr.read()
        exit_code = render.wait()

        duration = time.time() - started

        if exit_code != 0:
            return SandboxResult(
                ok=False,
                mp4_bytes=None,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                duration_sec=duration,
                error_class=_classify_error(stderr),
                traceback=_extract_traceback(stderr),
            )

        # Locate the produced mp4. Manim writes to media/videos/scene/480p15/Main.mp4
        find = sb.exec("find", SANDBOX_MEDIA_DIR, "-name", "*.mp4", "-type", "f")
        mp4_paths = find.stdout.read().strip().splitlines()
        find.wait()

        if not mp4_paths:
            return SandboxResult(
                ok=False,
                mp4_bytes=None,
                stdout=stdout,
                stderr=stderr,
                exit_code=exit_code,
                duration_sec=duration,
                error_class="Other",
                traceback="Render completed with exit 0 but no MP4 produced.",
            )

        # Read the mp4 bytes back through the sandbox. Modal Sandbox exposes
        # process IO as text; we ask for raw bytes via Sandbox's filesystem API.
        try:
            with sb.open(mp4_paths[0], "rb") as f:
                mp4_bytes = f.read()
        except Exception:
            # Fallback to base64 via cat if .open() isn't available in this SDK version.
            b64 = sb.exec("base64", "-w0", mp4_paths[0])
            import base64 as _b64
            mp4_bytes = _b64.b64decode(b64.stdout.read())
            b64.wait()

        return SandboxResult(
            ok=True,
            mp4_bytes=mp4_bytes,
            stdout=stdout,
            stderr=stderr,
            exit_code=0,
            duration_sec=duration,
        )
    finally:
        try:
            sb.terminate()
        except Exception:
            pass


def _classify_error(stderr: str) -> str:
    s = stderr.lower()
    if "syntaxerror" in s:
        return "SyntaxError"
    if "importerror" in s or "modulenotfounderror" in s:
        return "ImportError"
    if "latex error" in s or "miktex" in s or "tex" in s and "error" in s:
        return "LaTeXError"
    if "timeout" in s:
        return "TimeoutError"
    if "manim" in s or "scene" in s:
        return "ManimError"
    return "Other"


def _extract_traceback(stderr: str) -> str:
    """Return the last 50 lines of stderr — enough for codegen repair."""
    lines = stderr.strip().splitlines()
    return "\n".join(lines[-50:])


def _run_in_process(
    code: str,
    scene_class: str,
    timeout_sec: int,
    started: float,
) -> SandboxResult:
    """Render Manim via subprocess inside the current worker container.

    Used while modal.Sandbox is broken (B-010). The function MUST be invoked
    from inside a Modal function whose `image` includes Manim + LaTeX (i.e.
    render_image). AST safety check has already passed by the time we're here.
    """
    import subprocess
    import tempfile
    import time
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        scene_path = tmp_path / "scene.py"
        scene_path.write_text(code, encoding="utf-8")

        try:
            result = subprocess.run(
                [
                    "python", "-m", "manim",
                    "-ql",
                    "--media_dir", str(tmp_path / "media"),
                    "--disable_caching",
                    str(scene_path),
                    scene_class,
                ],
                capture_output=True,
                text=True,
                cwd=str(tmp_path),
                timeout=timeout_sec,
            )
        except subprocess.TimeoutExpired:
            return SandboxResult(
                ok=False, mp4_bytes=None, stdout="", stderr="render timed out",
                exit_code=-1, duration_sec=time.time() - started,
                error_class="TimeoutError",
                traceback=f"manim render exceeded {timeout_sec}s",
            )

        duration = time.time() - started

        if result.returncode != 0:
            return SandboxResult(
                ok=False, mp4_bytes=None, stdout=result.stdout, stderr=result.stderr,
                exit_code=result.returncode, duration_sec=duration,
                error_class=_classify_error(result.stderr),
                traceback=_extract_traceback(result.stderr),
            )

        mp4s = list((tmp_path / "media").rglob("*.mp4"))
        if not mp4s:
            return SandboxResult(
                ok=False, mp4_bytes=None,
                stdout=result.stdout, stderr=result.stderr,
                exit_code=result.returncode, duration_sec=duration,
                error_class="Other",
                traceback="Render exit 0 but no MP4 produced.",
            )

        # Prefer the *largest* mp4 — Manim emits per-animation partials and
        # one consolidated scene file. The consolidated one is always larger.
        chosen = max(mp4s, key=lambda p: p.stat().st_size)
        mp4_bytes = chosen.read_bytes()

        return SandboxResult(
            ok=True, mp4_bytes=mp4_bytes,
            stdout=result.stdout, stderr=result.stderr,
            exit_code=0, duration_sec=duration,
        )
