"""Service-role Supabase client for Modal workers.

Bypasses RLS. Used to write job_events, scenes, artifacts.
NEVER expose this client to user-facing code.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID

from supabase import Client, create_client

from workers.lib.config import WorkerConfig
from workers.lib.schemas import JobEventKind, JobStatus


def make_client(cfg: WorkerConfig) -> Client:
    """Service-role client. RLS bypassed."""
    return create_client(cfg.supabase_url, cfg.supabase_service_key)


# ─── Job state helpers ─────────────────────────────────────────────────────────


async def update_job_status(
    client: Client,
    job_id: str | UUID,
    status: JobStatus,
    *,
    error_message: str | None = None,
) -> None:
    update: dict[str, Any] = {"status": status.value}
    if status == JobStatus.DONE:
        update["completed_at"] = datetime.utcnow().isoformat()
    if error_message:
        update["error_message"] = error_message
    client.table("jobs").update(update).eq("id", str(job_id)).execute()


async def emit_event(
    client: Client,
    job_id: str | UUID,
    stage: str,
    kind: JobEventKind,
    payload: dict[str, Any] | None = None,
) -> None:
    """Append a row to job_events. This is the source of truth for Realtime UI."""
    client.table("job_events").insert({
        "job_id": str(job_id),
        "stage": stage,
        "kind": kind.value,
        "payload": payload or {},
    }).execute()


# ─── Artifact helpers ──────────────────────────────────────────────────────────


def upload_artifact(
    client: Client,
    job_id: str | UUID,
    name: str,
    content: bytes | str,
    *,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload an artifact and return its storage path. Bucket = 'artifacts'."""
    path = f"{job_id}/{name}"
    body = content.encode("utf-8") if isinstance(content, str) else content
    client.storage.from_("artifacts").upload(
        path,
        body,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    return path


def upload_video(
    client: Client,
    job_id: str | UUID,
    name: str,
    content: bytes,
) -> str:
    path = f"{job_id}/{name}"
    client.storage.from_("videos").upload(
        path,
        content,
        file_options={"content-type": "video/mp4", "upsert": "true"},
    )
    return path


def download_artifact(client: Client, path: str) -> bytes:
    return client.storage.from_("artifacts").download(path)


def download_pdf(client: Client, path: str) -> bytes:
    return client.storage.from_("pdfs").download(path)


# ─── Scene state ───────────────────────────────────────────────────────────────


async def upsert_scene(
    client: Client,
    job_id: str | UUID,
    scene_index: int,
    scene_id: str,
    **fields: Any,
) -> None:
    client.table("scenes").upsert({
        "job_id": str(job_id),
        "scene_index": scene_index,
        "scene_id": scene_id,
        **fields,
    }, on_conflict="job_id,scene_index").execute()


def fetch_job(client: Client, job_id: str | UUID) -> dict[str, Any] | None:
    rows = client.table("jobs").select("*").eq("id", str(job_id)).execute()
    return rows.data[0] if rows.data else None


def fetch_user_settings(client: Client, user_id: str) -> dict[str, Any] | None:
    rows = client.table("user_settings").select("*").eq("user_id", user_id).execute()
    return rows.data[0] if rows.data else None


# ─── Usage records (cost telemetry) ────────────────────────────────────────────


def record_usage(
    client: Client,
    *,
    user_id: str | None,
    job_id: str | UUID | None,
    kind: str,
    units: float,
    provider: str | None = None,
    model: str | None = None,
    cost_usd: float | None = None,
) -> None:
    client.table("usage_records").insert({
        "user_id": user_id,
        "job_id": str(job_id) if job_id else None,
        "kind": kind,
        "provider": provider,
        "model": model,
        "units": units,
        "cost_usd": cost_usd,
    }).execute()
