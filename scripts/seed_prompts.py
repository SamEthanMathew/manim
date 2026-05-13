"""Seed prompts from modal/prompts/*.md into the Supabase `prompts` table.

Idempotent: only inserts when (name, version) doesn't exist yet.

Run:
  SUPABASE_URL=... SUPABASE_SERVICE_ROLE_KEY=... python scripts/seed_prompts.py
"""
from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from supabase import create_client

PROMPTS = [
    ("style_guide",      "workers/prompts/style_guide.md",        1),
    ("curriculum",       "workers/prompts/curriculum_v1.md",      1),
    ("script",           "workers/prompts/script_v1.md",          1),
    ("scene_spec",       "workers/prompts/scene_spec_v1.md",      1),
    ("codegen",          "workers/prompts/codegen_v1.md",         1),
    ("codegen_repair",   "workers/prompts/codegen_repair_v1.md",  1),
]


def main() -> int:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    client = create_client(url, key)

    root = Path(__file__).resolve().parent.parent

    for name, rel, version in PROMPTS:
        path = root / rel
        body = path.read_text(encoding="utf-8")
        sha = hashlib.sha256(body.encode("utf-8")).hexdigest()

        existing = client.table("prompts").select("body_sha").eq("name", name).eq("version", version).execute()
        if existing.data:
            if existing.data[0]["body_sha"] == sha:
                print(f"= {name} v{version}: up to date")
                continue
            print(f"! {name} v{version}: body changed, bumping version")
            # Insert as v+1 instead of clobbering history.
            client.table("prompts").insert({
                "name": name,
                "version": version + 1,
                "body": body,
                "body_sha": sha,
            }).execute()
        else:
            client.table("prompts").insert({
                "name": name,
                "version": version,
                "body": body,
                "body_sha": sha,
            }).execute()
            print(f"+ {name} v{version}: inserted")
    return 0


if __name__ == "__main__":
    sys.exit(main())
