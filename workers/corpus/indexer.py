"""3b1b corpus indexer.

Walks a cloned 3blue1brown/videos repo, extracts every Scene subclass, optionally
translates ManimGL idioms to ManimCE, generates an LLM description, embeds with
Voyage, and upserts into Supabase's rag_documents table.

Run:
  python -m modal.corpus.indexer --repo ./3b1b_videos --upsert
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Iterator

from workers.corpus.manim_gl_to_ce import translate

log = logging.getLogger(__name__)


# ─── Step 1: walk repo, extract Scene subclasses ──────────────────────────────


def find_scene_classes(repo_root: Path) -> Iterator[dict]:
    """Yields dicts of {source, scene_name, code, original_code, docstring}."""
    for py in repo_root.rglob("*.py"):
        if any(part.startswith(".") for part in py.parts):
            continue
        try:
            source = py.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue

        for node in tree.body:
            if isinstance(node, ast.ClassDef) and _is_scene_subclass(node):
                snippet = ast.get_source_segment(source, node) or ""
                if not snippet:
                    continue
                yield {
                    "source": str(py.relative_to(repo_root)),
                    "scene_name": node.name,
                    "code": translate(snippet),
                    "original_code": snippet,
                    "docstring": ast.get_docstring(node) or "",
                }


def _is_scene_subclass(node: ast.ClassDef) -> bool:
    for base in node.bases:
        name = _base_name(base)
        if name and ("Scene" in name or "Slide" in name):
            return True
    return False


def _base_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


# ─── Step 2: emit corpus_raw.json (no LLM, no embedding yet) ──────────────────


def emit_raw(repo_root: Path, out_path: Path) -> int:
    count = 0
    with out_path.open("w", encoding="utf-8") as f:
        for record in find_scene_classes(repo_root):
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


# ─── Step 3: enrich with LLM description + Voyage embedding ───────────────────


def enrich(input_path: Path, output_path: Path,
           voyage_api_key: str, openai_api_key: str,
           voyage_batch: int = 10,
           voyage_request_interval_sec: float = 21.0) -> int:
    """Reads corpus_raw.jsonl, adds description (LLM) and embedding (Voyage).

    Batches Voyage embed calls to respect free-tier rate limits
    (3 RPM + 10k TPM). Defaults: 10 docs per call, ≥21s between calls
    (so we stay strictly under 3 RPM).
    """
    import time
    import openai
    import voyageai

    voyage = voyageai.Client(api_key=voyage_api_key)
    oai = openai.OpenAI(api_key=openai_api_key)

    # ---- pass 1: descriptions (OpenAI, parallel via ThreadPoolExecutor) ----
    from concurrent.futures import ThreadPoolExecutor, as_completed
    records = [json.loads(l) for l in input_path.open("r", encoding="utf-8")]

    def _describe_one(rec):
        desc_prompt = (
            "In one short paragraph, describe what this Manim scene visualizes "
            "and the math/CS concept it teaches:\n\n```python\n"
            f"{rec['code'][:3500]}\n```"
        )
        try:
            resp = oai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": desc_prompt}],
                max_tokens=200,
                temperature=0.3,
            )
            rec["description"] = resp.choices[0].message.content or ""
        except Exception as e:
            log.warning("Description failed for %s: %s", rec["source"], e)
            rec["description"] = rec.get("docstring", "")
        return rec

    with ThreadPoolExecutor(max_workers=8) as pool:
        done = 0
        futures = [pool.submit(_describe_one, r) for r in records]
        for fut in as_completed(futures):
            fut.result()
            done += 1
            if done % 25 == 0 or done == len(records):
                print(f"  descriptions: {done}/{len(records)}")

    # ---- pass 2: batched embeddings (Voyage, rate-limited) ----
    last_call = 0.0
    for i in range(0, len(records), voyage_batch):
        batch = records[i : i + voyage_batch]
        texts = [f"{r['description']}\n\n{r['code'][:2000]}" for r in batch]

        # Throttle to fit 3 RPM (one call ≥21s after the previous one).
        wait = voyage_request_interval_sec - (time.time() - last_call)
        if wait > 0:
            time.sleep(wait)

        try:
            emb = voyage.embed(texts, model="voyage-3", input_type="document")
            for r, v in zip(batch, emb.embeddings, strict=True):
                r["embedding"] = v
            print(f"  batch {i // voyage_batch + 1}: embedded {len(batch)} scenes")
        except Exception as e:
            log.warning("Embedding batch failed for %d scenes: %s", len(batch), e)
            for r in batch:
                r["embedding"] = None
        last_call = time.time()

    # ---- write out ----
    with output_path.open("w", encoding="utf-8") as fout:
        for rec in records:
            fout.write(json.dumps(rec, ensure_ascii=False) + "\n")

    return len(records)


# ─── Step 4: upsert into Supabase ─────────────────────────────────────────────


def upsert_to_supabase(enriched_path: Path, supabase_url: str, service_key: str) -> int:
    from supabase import create_client

    client = create_client(supabase_url, service_key)
    count = 0
    with enriched_path.open("r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            if not rec.get("embedding"):
                continue
            client.table("rag_documents").upsert({
                "source": rec["source"],
                "scene_name": rec["scene_name"],
                "description": rec.get("description"),
                "code": rec["code"],
                "original_code": rec.get("original_code"),
                "embedding": rec["embedding"],
                "metadata": {"docstring": rec.get("docstring", "")},
            }, on_conflict="source,scene_name").execute()
            count += 1
    return count


# ─── CLI ──────────────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True, help="Path to cloned 3b1b/videos")
    parser.add_argument("--raw-out", type=Path, default=Path("corpus_raw.jsonl"))
    parser.add_argument("--enriched-out", type=Path, default=Path("corpus_embedded.jsonl"))
    parser.add_argument("--enrich", action="store_true", help="Run LLM + embedding pass")
    parser.add_argument("--upsert", action="store_true", help="Push to Supabase")
    args = parser.parse_args()

    n_raw = emit_raw(args.repo, args.raw_out)
    print(f"Wrote {n_raw} scenes -> {args.raw_out}")

    if args.enrich:
        voyage_key = os.environ["VOYAGE_API_KEY"]
        openai_key = os.environ["OPENAI_API_KEY"]
        n_enriched = enrich(args.raw_out, args.enriched_out, voyage_key, openai_key)
        print(f"Enriched {n_enriched} scenes -> {args.enriched_out}")

    if args.upsert:
        n_up = upsert_to_supabase(
            args.enriched_out,
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_SERVICE_ROLE_KEY"],
        )
        print(f"Upserted {n_up} rows to rag_documents")

    return 0


if __name__ == "__main__":
    sys.exit(main())
