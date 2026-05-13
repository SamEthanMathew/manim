#!/usr/bin/env bash
# One-command local dev setup for the manim monorepo.
# Idempotent — safe to re-run.

set -euo pipefail

echo "==> manim dev-setup"

# --- Tool checks ---
command -v node >/dev/null || { echo "node not found — install Node 20+"; exit 1; }
command -v pnpm >/dev/null || { echo "pnpm not found — run: npm i -g pnpm"; exit 1; }
command -v uv   >/dev/null || { echo "uv not found — https://docs.astral.sh/uv/getting-started/installation/"; exit 1; }

# --- Node deps ---
echo "==> Installing JS deps (pnpm)"
pnpm install --frozen-lockfile || pnpm install

# --- Python deps (modal/) ---
echo "==> Installing Python deps (uv)"
uv sync --project modal

# --- .env scaffold ---
if [ ! -f .env.local ]; then
  cp .env.example .env.local
  echo "==> Created .env.local from template — fill it in before running"
fi

# --- Pre-commit ---
if command -v pre-commit >/dev/null; then
  pre-commit install || true
fi

echo ""
echo "==> Done. Next steps:"
echo "    1. Fill in .env.local (Supabase URL/keys, Modal tokens, BYOK encryption key)"
echo "    2. Run frontend:  pnpm --filter @manim/web dev"
echo "    3. Deploy Modal:  cd modal && modal deploy app.py"
echo "    4. Apply Supabase migrations:  supabase db push"
