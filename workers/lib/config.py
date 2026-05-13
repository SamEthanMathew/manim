"""Runtime config for Modal workers — pulled from env at function entry."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class WorkerConfig:
    supabase_url: str
    supabase_service_key: str
    byok_encryption_key: str
    sentry_dsn: str | None
    axiom_token: str | None
    axiom_dataset: str
    max_concurrent_scenes: int = 4
    render_attempts: int = 5
    render_timeout_sec: int = 300

    @classmethod
    def from_env(cls) -> WorkerConfig:
        # Required keys; if missing, we want a loud failure, not silent default.
        required = ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "BYOK_ENCRYPTION_KEY")
        missing = [k for k in required if not os.getenv(k)]
        if missing:
            raise RuntimeError(f"Missing required env vars: {missing}")

        return cls(
            supabase_url=os.environ["SUPABASE_URL"],
            supabase_service_key=os.environ["SUPABASE_SERVICE_ROLE_KEY"],
            byok_encryption_key=os.environ["BYOK_ENCRYPTION_KEY"],
            sentry_dsn=os.getenv("SENTRY_DSN"),
            axiom_token=os.getenv("AXIOM_TOKEN"),
            axiom_dataset=os.getenv("AXIOM_DATASET", "manim"),
            max_concurrent_scenes=int(os.getenv("MAX_CONCURRENT_SCENES", "4")),
            render_attempts=int(os.getenv("RENDER_ATTEMPTS", "5")),
            render_timeout_sec=int(os.getenv("RENDER_TIMEOUT_SEC", "300")),
        )


@dataclass(frozen=True)
class UserApiKeys:
    """Decrypted, in-memory only. Never persisted, never logged."""
    openai: str | None
    anthropic: str | None
    preferred_model: str
