"""AST-level safety check for LLM-generated Manim code.

Belt-and-suspenders alongside Modal's sandbox runtime isolation.
A determined adversary will defeat static analysis; this layer kills
the common cases quickly and cheaply.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field

# Allowlisted top-level imports. Anything else triggers SandboxViolation.
ALLOWED_TOP_LEVEL_IMPORTS: frozenset[str] = frozenset({
    "manim",
    "numpy",
    "np",          # alias only valid in `import numpy as np`
    "math",
    "random",
    "itertools",
    "functools",
    "operator",
    "fractions",
    "decimal",
    "typing",
})

# Banned attribute names — even if imported indirectly, calling these is sus.
BANNED_ATTRS: frozenset[str] = frozenset({
    "system", "popen", "spawn",          # os.system, subprocess.Popen, ...
    "eval", "exec", "compile",
    "__import__",
    "open",                              # use Manim's file APIs only
    "urlopen", "request",                # network
    "socket",
    "send", "recv",
})

# Banned module names that may sneak in via `from x import y`.
BANNED_MODULES: frozenset[str] = frozenset({
    "os", "subprocess", "sys", "shutil", "pathlib",
    "socket", "urllib", "http", "requests", "httpx",
    "ftplib", "smtplib", "telnetlib",
    "ctypes", "ctypes.util",
    "pickle", "marshal", "shelve",
    "tempfile",   # writes to fs outside scope
    "importlib", "imp",
})


@dataclass
class SafetyReport:
    ok: bool
    violations: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)

    def fail(self, msg: str) -> None:
        self.ok = False
        self.violations.append(msg)


def check(source: str) -> SafetyReport:
    """Static scan of LLM-generated source. Returns a SafetyReport.

    The render harness should reject sources where report.ok is False and
    feed the violations back into the codegen-repair prompt.
    """
    report = SafetyReport(ok=True)

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        report.fail(f"SyntaxError: {e}")
        return report

    for node in ast.walk(tree):
        _check_node(node, report)

    return report


def _check_node(node: ast.AST, report: SafetyReport) -> None:
    # Imports
    if isinstance(node, ast.Import):
        for alias in node.names:
            name = alias.name.split(".")[0]
            report.imports.append(alias.name)
            if name in BANNED_MODULES:
                report.fail(f"Banned import: {alias.name}")
            elif name not in ALLOWED_TOP_LEVEL_IMPORTS:
                report.fail(f"Disallowed import (not in allowlist): {alias.name}")

    elif isinstance(node, ast.ImportFrom):
        mod = (node.module or "").split(".")[0]
        report.imports.append(node.module or "<from .>")
        if mod in BANNED_MODULES:
            report.fail(f"Banned import: from {node.module}")
        elif mod not in ALLOWED_TOP_LEVEL_IMPORTS:
            report.fail(f"Disallowed import: from {node.module}")

    # Banned attribute references (e.g., something.system, something.eval)
    elif isinstance(node, ast.Attribute):
        if node.attr in BANNED_ATTRS:
            report.fail(f"Banned attribute access: .{node.attr}")

    # Banned bare names (e.g., calling open() or eval())
    elif isinstance(node, ast.Name):
        if node.id in BANNED_ATTRS:
            report.fail(f"Banned name reference: {node.id}")

    # No dynamic execution
    elif isinstance(node, ast.Call):
        fn = node.func
        if isinstance(fn, ast.Name) and fn.id in {"eval", "exec", "compile", "__import__"}:
            report.fail(f"Banned dynamic execution: {fn.id}()")
