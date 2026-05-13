-- 0003_storage_buckets.sql
-- Storage bucket creation and RLS for uploaded/generated artifacts.
-- Buckets are private; access via signed URLs only.

-- ─── Create buckets ────────────────────────────────────────────────────────
-- Use insert ... on conflict to make idempotent.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('pdfs',       'pdfs',       false, 20 * 1024 * 1024, array['application/pdf']),
  ('artifacts',  'artifacts',  false, null,             null),
  ('videos',     'videos',     false, 500 * 1024 * 1024, array['video/mp4'])
on conflict (id) do nothing;

-- ─── pdfs: users upload their own; only owner can read ─────────────────────
create policy "users upload own pdfs"
  on storage.objects
  for insert
  with check (
    bucket_id = 'pdfs'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

create policy "users read own pdfs"
  on storage.objects
  for select
  using (
    bucket_id = 'pdfs'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

create policy "users delete own pdfs"
  on storage.objects
  for delete
  using (
    bucket_id = 'pdfs'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

-- ─── artifacts: only service role; users never directly touch ──────────────
-- No policies = no user access.

-- ─── videos: users read their own; service role writes ────────────────────
create policy "users read own videos"
  on storage.objects
  for select
  using (
    bucket_id = 'videos'
    and auth.uid()::text = (storage.foldername(name))[1]
  );

-- ─── Lifecycle reminder (enforced via cron, not policy) ────────────────────
-- Cron job in scripts/cleanup.py:
--   - pdfs   older than 30 days  -> delete
--   - artifacts older than 7 days -> delete
--   - videos older than 30 days   -> delete (free tier)
-- E10 owns the cron registration.
