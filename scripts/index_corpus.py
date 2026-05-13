"""One-shot wrapper around workers.corpus.indexer that:
  - Loads .env.local (so VOYAGE/OPENAI/SUPABASE keys come from there)
  - Skips emit_raw (use existing corpus_raw.jsonl)
  - Runs enrich + upsert directly

Usage:
  python scripts/index_corpus.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env.local")

# Also accept the public-prefixed name as the canonical URL
os.environ["SUPABASE_URL"] = os.environ.get("SUPABASE_URL") or os.environ["NEXT_PUBLIC_SUPABASE_URL"]

from workers.corpus.indexer import enrich, upsert_to_supabase  # noqa: E402


def main() -> int:
    raw = ROOT / "corpus_raw.jsonl"
    enriched = ROOT / "corpus_embedded.jsonl"

    if not raw.exists():
        print(f"missing {raw} — run `python -m workers.corpus.indexer --repo 3b1b_videos` first")
        return 1

    line_count = sum(1 for _ in raw.open(encoding="utf-8"))
    print(f"== enrich pass: {line_count} scenes ==")

    n = enrich(
        raw,
        enriched,
        voyage_api_key=os.environ["VOYAGE_API_KEY"],
        openai_api_key=os.environ["OPENAI_API_KEY"],
    )
    print(f"enriched {n} scenes -> {enriched}")

    print("== upsert pass ==")
    up = upsert_to_supabase(
        enriched,
        os.environ["SUPABASE_URL"],
        os.environ["SUPABASE_SERVICE_ROLE_KEY"],
    )
    print(f"upserted {up} rows into public.rag_documents")
    return 0


if __name__ == "__main__":
    sys.exit(main())
