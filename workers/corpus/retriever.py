"""3b1b corpus retriever.

Embeds a query (a SceneSpec, serialized) and pgvector-queries rag_documents
for the top-K most similar scenes. Returns a list of dicts ready for the
codegen prompt.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from workers.lib.schemas import SceneSpec

log = logging.getLogger(__name__)


def retrieve_similar(supabase_client, spec: SceneSpec, *, top_k: int = 5) -> list[dict[str, Any]]:
    """Returns up to top_k examples from rag_documents.

    The embedding model is Voyage `voyage-3`. We use it through the
    `VOYAGE_API_KEY` server-side secret (NOT user BYOK), since corpus retrieval
    is not user-funded.
    """
    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key:
        log.warning("VOYAGE_API_KEY not set; returning empty retrieval set")
        return []

    query_text = _serialize_spec_for_embedding(spec)

    try:
        import voyageai
        voyage = voyageai.Client(api_key=api_key)
        result = voyage.embed([query_text], model="voyage-3", input_type="query")
        embedding = result.embeddings[0]
    except Exception as e:
        log.warning("Voyage embedding failed: %s", e)
        return []

    # pgvector RPC; Supabase exposes a `match_rag_documents` SQL fn we'll create.
    # For v1, we fall back to a direct ORDER BY <=> query.
    try:
        rows = supabase_client.rpc(
            "match_rag_documents",
            {"query_embedding": embedding, "match_count": top_k},
        ).execute()
        return rows.data or []
    except Exception:
        # Fallback: client-side ANN approximation via select + cosine.
        # This is slow for the full table; viable only for small corpora.
        log.warning("RPC match_rag_documents missing; falling back to raw select")
        rows = (
            supabase_client.table("rag_documents")
            .select("source, scene_name, description, code, embedding")
            .limit(200)
            .execute()
        )
        if not rows.data:
            return []
        scored = [
            (
                _cosine(embedding, r["embedding"]) if r.get("embedding") else -1.0,
                {k: r[k] for k in ("source", "scene_name", "description", "code")},
            )
            for r in rows.data
        ]
        scored.sort(key=lambda x: -x[0])
        return [d for _, d in scored[:top_k]]


def _serialize_spec_for_embedding(spec: SceneSpec) -> str:
    """Compact representation of the spec for embedding."""
    elem_summary = ", ".join(f"{e.type}" for e in spec.elements)
    action_summary = ", ".join(f"{a.action.value}" for a in spec.timeline)
    return (
        f"Manim scene with elements: {elem_summary}. "
        f"Animations: {action_summary}. "
        f"Duration: {spec.duration_sec}s."
    )


def _cosine(a: list[float], b: list[float]) -> float:
    import math
    if not a or not b or len(a) != len(b):
        return -1.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else -1.0
