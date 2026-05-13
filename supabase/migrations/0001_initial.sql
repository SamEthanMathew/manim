-- 0001_initial.sql
-- Core tables for the manim pipeline.
-- Auth users come from Supabase's managed auth.users.

-- ─── Extensions ────────────────────────────────────────────────────────────
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";          -- AES-GCM for BYOK
create extension if not exists "vector";            -- pgvector for RAG

-- ─── User settings (BYOK + preferences) ────────────────────────────────────
create table if not exists public.user_settings (
  user_id uuid primary key references auth.users on delete cascade,
  openai_api_key_encrypted bytea,
  anthropic_api_key_encrypted bytea,
  preferred_model text not null default 'gpt-4o'
    check (preferred_model in ('gpt-4o', 'claude-sonnet-4-6', 'claude-opus-4-7')),
  default_target_duration_sec int not null default 600
    check (default_target_duration_sec between 60 and 1800),
  tone_hint text not null default 'balanced'
    check (tone_hint in ('formal', 'playful', 'technical', 'balanced')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create or replace function public.set_updated_at()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger user_settings_set_updated_at
  before update on public.user_settings
  for each row execute function public.set_updated_at();

-- ─── Jobs ──────────────────────────────────────────────────────────────────
create table if not exists public.jobs (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users on delete cascade,
  status text not null default 'pending' check (status in (
    'pending', 'ingesting', 'scripting', 'awaiting_approval',
    'rendering', 'composing', 'done', 'failed', 'cancelled'
  )),
  pdf_storage_path text not null,
  pdf_page_count int check (pdf_page_count is null or pdf_page_count between 1 and 50),
  target_duration_sec int not null default 600
    check (target_duration_sec between 60 and 1800),
  tone_hint text not null default 'balanced',
  approved boolean not null default false,
  final_video_path text,
  caption_srt_path text,
  scene_count int,
  fallback_scene_count int,
  error_message text,
  cost_estimate_usd numeric(10, 4),
  cost_actual_usd numeric(10, 4),
  prompt_versions jsonb not null default '{}'::jsonb,  -- which prompt versions were used
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  approved_at timestamptz,
  completed_at timestamptz
);

create index if not exists jobs_user_id_created_at_idx
  on public.jobs (user_id, created_at desc);
create index if not exists jobs_status_idx
  on public.jobs (status) where status not in ('done', 'failed', 'cancelled');

create trigger jobs_set_updated_at
  before update on public.jobs
  for each row execute function public.set_updated_at();

-- ─── Job events (append-only audit log + realtime source) ──────────────────
create table if not exists public.job_events (
  id bigserial primary key,
  job_id uuid not null references public.jobs on delete cascade,
  stage text not null check (stage in (
    'control', 'ingest', 'curriculum', 'script', 'scene_spec',
    'codegen', 'render', 'audio', 'compose'
  )),
  kind text not null check (kind in (
    'started', 'progress', 'completed', 'error', 'retry'
  )),
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists job_events_job_id_created_at_idx
  on public.job_events (job_id, created_at);

-- ─── Scenes (per-scene state for fan-out stages) ───────────────────────────
create table if not exists public.scenes (
  id uuid primary key default gen_random_uuid(),
  job_id uuid not null references public.jobs on delete cascade,
  scene_index int not null check (scene_index >= 0),
  scene_id text not null,
  spec jsonb,
  code_path text,
  video_path text,
  audio_path text,
  status text not null default 'pending' check (status in (
    'pending', 'spec_generated', 'code_generated',
    'rendering', 'rendered', 'fallback', 'failed'
  )),
  attempts int not null default 0,
  duration_sec numeric(6, 2),
  is_fallback boolean not null default false,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (job_id, scene_index)
);

create index if not exists scenes_job_id_scene_index_idx
  on public.scenes (job_id, scene_index);

create trigger scenes_set_updated_at
  before update on public.scenes
  for each row execute function public.set_updated_at();

-- ─── Prompts registry (versioned) ──────────────────────────────────────────
create table if not exists public.prompts (
  id bigserial primary key,
  name text not null check (name in (
    'style_guide', 'curriculum', 'script', 'scene_spec', 'codegen', 'codegen_repair'
  )),
  version int not null,
  body text not null,
  body_sha text not null,            -- content hash for cache keys
  metadata jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  unique (name, version)
);

create index if not exists prompts_name_version_idx
  on public.prompts (name, version desc);

-- ─── RAG corpus (3b1b scenes + Manim docs) ─────────────────────────────────
create table if not exists public.rag_documents (
  id bigserial primary key,
  source text not null,              -- e.g. '3b1b/videos/_2019/diffyq/part1.py'
  scene_name text,                   -- class name if applicable
  description text,                  -- LLM-generated one-paragraph summary
  code text not null,                -- ManimCE-translated source
  original_code text,                -- pre-translation (ManimGL) if applicable
  embedding vector(1024),            -- voyage-3 dimension
  metadata jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

create index if not exists rag_documents_embedding_idx
  on public.rag_documents using hnsw (embedding vector_cosine_ops);

create index if not exists rag_documents_source_idx
  on public.rag_documents (source);

-- ─── Usage records (for future billing + observability) ────────────────────
create table if not exists public.usage_records (
  id bigserial primary key,
  user_id uuid references auth.users on delete set null,
  job_id uuid references public.jobs on delete set null,
  kind text not null check (kind in (
    'llm_input_tokens', 'llm_output_tokens', 'embedding_tokens',
    'render_seconds', 'storage_mb_hours', 'pdf_pages'
  )),
  provider text,                     -- 'openai' | 'anthropic' | 'voyage' | 'modal'
  model text,
  units numeric not null,
  cost_usd numeric(10, 6),
  occurred_at timestamptz not null default now()
);

create index if not exists usage_records_user_occurred_idx
  on public.usage_records (user_id, occurred_at desc);
create index if not exists usage_records_job_idx
  on public.usage_records (job_id);

-- ─── Realtime publication (must be enabled for Supabase Realtime) ──────────
-- Note: alter publication runs against the default 'supabase_realtime' publication.
-- These statements are safe to re-run.
do $$
begin
  perform 1 from pg_publication where pubname = 'supabase_realtime';
  if found then
    alter publication supabase_realtime add table public.jobs;
    alter publication supabase_realtime add table public.job_events;
    alter publication supabase_realtime add table public.scenes;
  end if;
exception when duplicate_object then null;
end$$;
