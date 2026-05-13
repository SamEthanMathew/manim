"""Invoke deployed Modal functions and print their result.

Usage:
  python scripts/run_smoke.py render_smoke_test
  python scripts/run_smoke.py render_smoke_sandbox
  python scripts/run_smoke.py render_fixture eulers_identity
"""
from __future__ import annotations

import json
import sys

import modal


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_smoke.py <function_name> [args...]")
        return 1

    fn_name = sys.argv[1]
    args = sys.argv[2:]

    fn = modal.Function.from_name("manim", fn_name)
    print(f"Calling {fn_name}({args}) ...")
    result = fn.remote(*args)

    if isinstance(result, dict):
        # Truncate long stderr/stdout fields for terminal display
        for k in ("stdout_tail", "stderr_tail"):
            if k in result and isinstance(result[k], str) and len(result[k]) > 500:
                result[k] = result[k][-500:] + " (truncated)"
        print(json.dumps(result, indent=2))
    else:
        print(result)
    return 0 if (isinstance(result, dict) and result.get("ok")) else 2


if __name__ == "__main__":
    sys.exit(main())
