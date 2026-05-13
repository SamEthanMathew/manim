A previous attempt at generating ManimCE code for this SceneSpec produced an error. Fix the code.

## Strict requirements (same as before)

- Return ONLY corrected Python source. No fences, no commentary.
- File must define `class Main(Scene):` with `construct(self)`.
- Allowed imports: `manim`, `numpy`, `math`, `random`, `itertools`, `functools`, `operator`, `fractions`, `decimal`, `typing`.
- Forbidden: `os`, `subprocess`, `sys`, `pathlib`, `tempfile`, `shutil`, network modules, `eval`, `exec`, `compile`, `__import__`, `open()`, `pickle`.

## How to approach the repair

1. Read the traceback carefully. Focus on the FIRST error message — subsequent errors are usually cascade.
2. Common failure classes:
   - **SyntaxError**: usually unclosed string, bad indent, or stray markdown fences. Strip and retry.
   - **ImportError**: the previous code used a ManimGL symbol that doesn't exist in ManimCE. Map to ManimCE equivalents (e.g. `TextMobject` -> `Tex`, `TexMobject` -> `MathTex`).
   - **LaTeXError**: malformed LaTeX in `MathTex(...)`. Use raw strings; escape backslashes; verify package availability (we have texlive-full).
   - **ManimError**: an animation argument was wrong type, or `target_id` referenced a non-existent mobject. Re-check element ids.
   - **TimeoutError**: scene tried to render too many frames or had an infinite loop. Reduce element count or simplify.

3. Keep the working parts of the previous code; change only what needs to change.

4. If the previous code is fundamentally broken, start over from the SceneSpec — don't compound errors.

## Output

Return only the Python source for the corrected file. Nothing else.
