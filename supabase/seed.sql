-- seed.sql
-- Seed data for local dev. Production seeds prompts via scripts/seed_prompts.py.

-- Initial prompt versions (v1) — bodies stored as placeholders; the canonical
-- bodies live in modal/prompts/*.md and are pushed by scripts/seed_prompts.py.
insert into public.prompts (name, version, body, body_sha)
values
  ('style_guide', 1, '<<see modal/prompts/style_guide.md>>', 'pending'),
  ('curriculum',  1, '<<see modal/prompts/curriculum_v1.md>>', 'pending'),
  ('script',      1, '<<see modal/prompts/script_v1.md>>', 'pending'),
  ('scene_spec',  1, '<<see modal/prompts/scene_spec_v1.md>>', 'pending'),
  ('codegen',     1, '<<see modal/prompts/codegen_v1.md>>', 'pending'),
  ('codegen_repair', 1, '<<see modal/prompts/codegen_repair_v1.md>>', 'pending')
on conflict (name, version) do nothing;
