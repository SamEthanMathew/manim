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
    """Run a Manim scene file in an isolated sandbox.

    Steps:
      1. Static AST check — reject early if banned imports or dynamic exec.
      2. Spawn sandbox with network blocked.
      3. Write code to /scene/scene.py.
      4. Run manim -ql.
      5. Read produced MP4 from /scene/media/.
      6. Return SandboxResult.
    """
    safety = ast_check(code)
    if not safety.ok:
        raise SandboxViolation(
            f"AST safety check failed: {safety.violations}",
            payload={"violations": safety.violations},
        )

    import time
    started = time.time()

    with modal.Sandbox.create(
        image=sandbox_image,
        block_network=True,
        cpu=4.0,
        memory=8192,
        timeout=cfg.render_timeout_sec,
    ) as sb:
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

        # Read the mp4 bytes back through the sandbox.
        # Modal Sandbox exec supports stdout streaming; cat to get bytes.
        cat = sb.exec("cat", mp4_paths[0])
        mp4_bytes = cat.stdout.read().encode("latin-1") if isinstance(cat.stdout.read(), str) else cat.stdout.read()
        cat.wait()

        return SandboxResult(
            ok=True,
            mp4_bytes=mp4_bytes,
            stdout=stdout,
            stderr=stderr,
            exit_code=0,
            duration_sec=duration,
        )


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
