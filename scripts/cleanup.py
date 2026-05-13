"""Storage and DB cleanup. Run nightly via cron / GitHub Actions.

Deletes:
  - pdfs    older than 30 days
  - artifacts older than 7 days
  - videos  older than 30 days (free tier; bump for paid users later)
  - job_events older than 90 days (audit log retention)
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone

from supabase import create_client


def main() -> int:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    client = create_client(url, key)
    now = datetime.now(timezone.utc)

    # 1. job_events > 90d
    cutoff = (now - timedelta(days=90)).isoformat()
    res = client.table("job_events").delete().lt("created_at", cutoff).execute()
    print(f"job_events: deleted {_count(res)} rows older than {cutoff}")

    # 2. Storage cleanup — listing the buckets and unlinking old files.
    for bucket, age_days in [("artifacts", 7), ("pdfs", 30), ("videos", 30)]:
        cutoff = (now - timedelta(days=age_days)).isoformat()
        # Supabase storage listing API:
        objs = client.storage.from_(bucket).list("", {"limit": 1000})
        to_delete = [
            o["name"] for o in objs
            if o.get("created_at") and o["created_at"] < cutoff
        ]
        if to_delete:
            client.storage.from_(bucket).remove(to_delete)
        print(f"{bucket}: removed {len(to_delete)} objects older than {cutoff}")

    return 0


def _count(res) -> int:
    return len(res.data) if res.data else 0


if __name__ == "__main__":
    sys.exit(main())
