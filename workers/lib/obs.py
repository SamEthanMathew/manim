"""Observability: Sentry + structured logging for Modal workers.

`init_observability()` is called from the top of each entry-point function
(run_pipeline, render_one_scene, trigger, render_smoke_*). It's idempotent —
safe to call repeatedly.

Logs use structlog with JSON output so Modal's stdout collector + Axiom
can index them. Every log line gets a `job_id` correlation key if one's set
in the context (use `set_job_context(job_id)`).
"""
from __future__ import annotations

import logging
import os
import sys
from contextvars import ContextVar
from typing import Any

import structlog

_initialized = False
_job_id_var: ContextVar[str | None] = ContextVar("job_id", default=None)
_scene_id_var: ContextVar[str | None] = ContextVar("scene_id", default=None)


def init_observability() -> None:
    """Idempotent setup of Sentry + structlog. Call at function entry."""
    global _initialized
    if _initialized:
        return

    # ─── Sentry (optional — only if DSN is set) ────────────────────────────
    sentry_dsn = os.getenv("SENTRY_DSN", "").strip()
    if sentry_dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(
                dsn=sentry_dsn,
                # Capture 100% of errors but only 5% of perf traces (free tier safe).
                traces_sample_rate=0.05,
                # Don't send PII; user job content might be sensitive.
                send_default_pii=False,
                environment=os.getenv("MODAL_ENVIRONMENT", "main"),
                # Tag every event with the service.
                release=os.getenv("GIT_SHA", "unknown"),
            )
        except Exception as e:
            print(f"sentry init failed: {e}", file=sys.stderr)

    # ─── structlog → JSON to stdout ────────────────────────────────────────
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            _inject_job_ctx,
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Make stdlib logging also use the structlog-configured formatter so
    # 3rd-party libs (httpx, supabase) emit JSON too.
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(logging.INFO)

    _initialized = True


def _inject_job_ctx(logger, name, event_dict: dict[str, Any]) -> dict[str, Any]:
    jid = _job_id_var.get()
    sid = _scene_id_var.get()
    if jid:
        event_dict.setdefault("job_id", jid)
    if sid:
        event_dict.setdefault("scene_id", sid)
    return event_dict


def set_job_context(job_id: str | None, scene_id: str | None = None) -> None:
    """Set the job_id (and optionally scene_id) for all logs in this task."""
    if job_id is not None:
        _job_id_var.set(job_id)
        try:
            import sentry_sdk
            sentry_sdk.set_tag("job_id", job_id)
        except Exception:
            pass
    if scene_id is not None:
        _scene_id_var.set(scene_id)
        try:
            import sentry_sdk
            sentry_sdk.set_tag("scene_id", scene_id)
        except Exception:
            pass


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Convenience accessor — auto-inits if not already done."""
    init_observability()
    return structlog.get_logger(name)


def capture_exception(exc: BaseException, **extra: Any) -> None:
    """Forward exceptions to Sentry if configured; always log them."""
    log = get_logger("error")
    log.error("exception", error_class=type(exc).__name__, message=str(exc), **extra)
    try:
        import sentry_sdk
        with sentry_sdk.push_scope() as scope:
            for k, v in extra.items():
                scope.set_extra(k, v)
            sentry_sdk.capture_exception(exc)
    except Exception:
        pass
