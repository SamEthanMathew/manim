-- 0004_rag_match_function.sql
-- RPC function for pgvector ANN match used by modal/corpus/retriever.py.

create or replace function public.match_rag_documents(
  query_embedding vector(1024),
  match_count int default 5
)
returns table (
  id bigint,
  source text,
  scene_name text,
  description text,
  code text,
  similarity float
)
language sql stable as $$
  select
    rd.id,
    rd.source,
    rd.scene_name,
    rd.description,
    rd.code,
    1 - (rd.embedding <=> query_embedding) as similarity
  from public.rag_documents rd
  where rd.embedding is not null
  order by rd.embedding <=> query_embedding
  limit match_count;
$$;
