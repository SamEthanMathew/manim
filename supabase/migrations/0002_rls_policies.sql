-- 0002_rls_policies.sql
-- Row-Level Security for user-scoped tables.
-- The service-role key (used by Modal workers) bypasses RLS — that's intentional.

-- ─── user_settings ─────────────────────────────────────────────────────────
alter table public.user_settings enable row level security;

create policy "users read own settings"
  on public.user_settings
  for select
  using (auth.uid() = user_id);

create policy "users insert own settings"
  on public.user_settings
  for insert
  with check (auth.uid() = user_id);

create policy "users update own settings"
  on public.user_settings
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);

-- ─── jobs ──────────────────────────────────────────────────────────────────
alter table public.jobs enable row level security;

create policy "users read own jobs"
  on public.jobs
  for select
  using (auth.uid() = user_id);

create policy "users insert own jobs"
  on public.jobs
  for insert
  with check (auth.uid() = user_id);

create policy "users update own jobs"
  on public.jobs
  for update
  using (auth.uid() = user_id)
  with check (auth.uid() = user_id);
-- delete intentionally not exposed; users hit "cancel" -> status update.

-- ─── job_events (read-only for users) ──────────────────────────────────────
alter table public.job_events enable row level security;

create policy "users read events for own jobs"
  on public.job_events
  for select
  using (
    exists (
      select 1 from public.jobs j
      where j.id = job_events.job_id and j.user_id = auth.uid()
    )
  );
-- inserts only via service role (Modal workers).

-- ─── scenes (read-only for users) ──────────────────────────────────────────
alter table public.scenes enable row level security;

create policy "users read scenes for own jobs"
  on public.scenes
  for select
  using (
    exists (
      select 1 from public.jobs j
      where j.id = scenes.job_id and j.user_id = auth.uid()
    )
  );

-- ─── prompts (read for everyone authenticated, write via service role) ─────
alter table public.prompts enable row level security;

create policy "authenticated read prompts"
  on public.prompts
  for select
  using (auth.role() = 'authenticated' or auth.role() = 'anon');

-- ─── rag_documents (no user access; service role only) ─────────────────────
alter table public.rag_documents enable row level security;
-- No policies = no rows visible to non-service-role.

-- ─── usage_records (users read own) ────────────────────────────────────────
alter table public.usage_records enable row level security;

create policy "users read own usage"
  on public.usage_records
  for select
  using (auth.uid() = user_id);
