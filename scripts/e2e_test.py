"""End-to-end smoke test of the manim pipeline.

Creates a synthetic test user, encrypts a BYOK key, inserts a fake PDF
into storage, creates a job, calls the Modal trigger, and watches what
happens via Supabase event polling.

Usage:
  python scripts/e2e_test.py \
      --pdf path/to/small.pdf \
      --openai-key sk-proj-... \
      [--duration 300] [--tone balanced] \
      [--watch-seconds 600]

Env vars required (from .env.local):
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, SUPABASE_DB_PASSWORD,
  BYOK_ENCRYPTION_KEY, MODAL_PIPELINE_ENDPOINT, MODAL_TRIGGER_SECRET.

Costs: each run hits the LLM. Budget per run depends on PDF size.
Approximate: $0.30-1.50 for a 5-min target video.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from pathlib import Path

import psycopg
import requests
from dotenv import load_dotenv

# Local import — make sure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))
from workers.lib.byok import encrypt  # noqa: E402

load_dotenv(Path(__file__).parent.parent / ".env.local")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--pdf", required=True, help="Path to a small PDF")
    p.add_argument("--openai-key", required=True, help="OpenAI API key for this run")
    p.add_argument("--duration", type=int, default=300, help="Target duration (sec)")
    p.add_argument("--tone", default="balanced")
    p.add_argument("--watch-seconds", type=int, default=600)
    p.add_argument("--user-label", default="e2e-test")
    args = p.parse_args()

    supabase_url = os.environ.get("SUPABASE_URL") or os.environ["NEXT_PUBLIC_SUPABASE_URL"]
    service_key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    db_password = os.environ["SUPABASE_DB_PASSWORD"]
    byok_key = os.environ["BYOK_ENCRYPTION_KEY"]
    modal_endpoint = os.environ["MODAL_PIPELINE_ENDPOINT"]
    trigger_secret = os.environ["MODAL_TRIGGER_SECRET"]

    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f"PDF not found: {pdf_path}")
        return 1
    pdf_size = pdf_path.stat().st_size
    if pdf_size > 20 * 1024 * 1024:
        print(f"PDF too large ({pdf_size} bytes; storage limit 20MB).")
        return 1

    user_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    project_ref = supabase_url.split("//")[1].split(".")[0]
    dsn = f"postgresql://postgres:{db_password}@db.{project_ref}.supabase.co:5432/postgres"

    # ─── 1. Create synthetic auth user + encrypted BYOK ───────────────────────
    print(f"[1/5] Creating test user {user_id[:8]}...")
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into auth.users (id, instance_id, aud, role, email, encrypted_password,
                                    email_confirmed_at, created_at, updated_at,
                                    raw_app_meta_data, raw_user_meta_data,
                                    is_super_admin, is_sso_user, is_anonymous)
            values (%s, '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated',
                    %s, '', now(), now(), now(), '{}', '{}', false, false, false)
            """,
            (user_id, f"{args.user_label}-{user_id[:8]}@example.com"),
        )
        encrypted_key = encrypt(byok_key, args.openai_key)
        cur.execute(
            """
            insert into public.user_settings (user_id, openai_api_key_encrypted, preferred_model, tone_hint)
            values (%s, %s, 'gpt-4o-mini', %s)
            """,
            (user_id, encrypted_key, args.tone),
        )
        conn.commit()
    print("      auth.users + user_settings rows inserted")

    # ─── 2. Upload PDF to Supabase Storage ────────────────────────────────────
    print(f"[2/5] Uploading PDF ({pdf_size} bytes)...")
    pdf_storage_path = f"{user_id}/{uuid.uuid4()}.pdf"
    upload_url = f"{supabase_url}/storage/v1/object/pdfs/{pdf_storage_path}"
    res = requests.post(
        upload_url,
        headers={
            "Authorization": f"Bearer {service_key}",
            "Content-Type": "application/pdf",
            "x-upsert": "true",
        },
        data=pdf_path.read_bytes(),
        timeout=60,
    )
    if res.status_code not in (200, 201):
        print(f"      upload failed: {res.status_code} {res.text[:300]}")
        return 1
    print(f"      uploaded to pdfs/{pdf_storage_path}")

    # ─── 3. Create job row ────────────────────────────────────────────────────
    print(f"[3/5] Creating job {job_id[:8]}...")
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(
            """
            insert into public.jobs (id, user_id, status, pdf_storage_path,
                                     target_duration_sec, tone_hint)
            values (%s, %s, 'pending', %s, %s, %s)
            """,
            (job_id, user_id, pdf_storage_path, args.duration, args.tone),
        )
        conn.commit()

    # ─── 4. Hit Modal trigger ─────────────────────────────────────────────────
    print("[4/5] Hitting Modal trigger...")
    r = requests.post(
        modal_endpoint,
        headers={"content-type": "application/json", "x-trigger-secret": trigger_secret},
        json={"job_id": job_id},
        timeout=30,
    )
    print(f"      {r.status_code} {r.text[:200]}")

    # ─── 5. Poll job + events ────────────────────────────────────────────────
    print(f"[5/5] Watching for up to {args.watch_seconds}s. Ctrl-C to stop.")
    seen_event_ids: set[int] = set()
    deadline = time.time() + args.watch_seconds
    final_status: str | None = None

    try:
        while time.time() < deadline:
            with psycopg.connect(dsn) as conn, conn.cursor() as cur:
                cur.execute("select status, error_message, final_video_path from public.jobs where id = %s",
                            (job_id,))
                row = cur.fetchone()
                if not row:
                    print("      job row not found — aborted")
                    break
                status, err, video_path = row

                cur.execute(
                    "select id, stage, kind, payload, created_at from public.job_events "
                    "where job_id = %s order by created_at",
                    (job_id,),
                )
                for ev in cur.fetchall():
                    if ev[0] in seen_event_ids:
                        continue
                    seen_event_ids.add(ev[0])
                    ts = ev[4].strftime("%H:%M:%S")
                    payload_str = str(ev[3])[:120]
                    print(f"      {ts} | {ev[1]:<12} | {ev[2]:<10} | {payload_str}")

            if status in ("done", "failed", "cancelled"):
                final_status = status
                print(f"\n--- final status: {status} ---")
                if err:
                    print(f"    error: {err}")
                if video_path:
                    print(f"    video: {supabase_url}/storage/v1/object/sign/videos/{video_path}")
                break
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n(interrupted)")

    print(f"\nTest run finished. job_id={job_id}")
    print(f"  to investigate: select * from job_events where job_id = '{job_id}' order by created_at;")
    print(f"  to clean up:   delete from jobs where id = '{job_id}'; delete from auth.users where id = '{user_id}';")
    return 0 if final_status == "done" else 2


if __name__ == "__main__":
    sys.exit(main())
