A previous attempt at generating ManimCE code for this SceneSpec produced an error. Fix the code.

## Strict requirements (same as the original codegen)

- Return ONLY corrected Python source. No markdown fences, no commentary.
- File must define `class Main(Scene):` with `construct(self)`.
- Allowed imports: `manim`, `numpy`, `math`, `random`, `itertools`, `functools`, `operator`, `fractions`, `decimal`, `typing`.
- Forbidden: `os`, `subprocess`, `sys`, `pathlib`, `tempfile`, `shutil`, network modules, `eval`, `exec`, `compile`, `__import__`, `open()`, `pickle`.

## How to approach the repair

1. Read the traceback carefully. Focus on the FIRST error message — subsequent errors are usually cascade noise.
2. Keep the working parts of the previous code; change only what needs to change.
3. If the previous code is fundamentally broken (every animation references undefined mobjects, the class name is wrong, etc.), start over from the SceneSpec — don't compound errors.

## Error-class checklist

Match the traceback against this list and apply the most likely fix.

### SyntaxError
- Most likely cause: a stray markdown fence (\`\`\`python or \`\`\`) leaked into the output, or an unclosed string/parenthesis, or bad indentation.
- Fix: strip any non-Python characters from the top and bottom of the file. Verify every `(`, `[`, `{` has a matching close. Confirm indentation is consistent (4 spaces, no tabs).
- Watch for: f-strings with unescaped braces inside LaTeX strings — use raw strings `r"..."` for LaTeX, not f-strings.

### ImportError / NameError / AttributeError on a Manim symbol
- Most likely cause: code used a ManimGL symbol that doesn't exist in ManimCE.
- Common mappings:
  - `TextMobject` -> `Text` (for prose) or `Tex` (for general LaTeX).
  - `TexMobject` -> `MathTex`.
  - `ShowCreation` -> `Create`.
  - `ApplyMethod(obj.shift, ...)` -> `obj.animate.shift(...)`.
  - `CONFIG = {...}` class-level dict -> not supported; pass args to `__init__` instead.
- Fix: replace the symbol with its ManimCE equivalent. If the symbol doesn't exist in ManimCE at all, restructure the animation using `Create`/`FadeIn`/`Transform`/`Indicate`/`Write`.

### LaTeXError / "Failed to compile LaTeX"
- Most likely cause: malformed LaTeX in `MathTex(...)`, or English prose accidentally placed in a `MathTex` call instead of `Text`.
- Fixes:
  - Use raw strings: `MathTex(r"\frac{1}{2}")`, not `MathTex("\frac{1}{2}")`.
  - Escape backslashes when not using a raw string.
  - Move English labels into `Text(...)`. `MathTex("the gradient")` will fail.
  - Check for unbalanced braces in the LaTeX string.
  - Avoid niche packages — assume the standard texlive distribution.

### ManimError / TypeError on an animation argument
- Most likely cause: an animation was passed an undefined or wrong-type mobject, or `target_id` referenced a mobject that was never constructed.
- Fix: confirm every `self.play(<Anim>(x))` references a mobject `x` that has been assigned in `construct` before that line. If `Transform(a, b)` is used, both `a` and `b` must be mobjects (not strings or ids).

### TimeoutError / OOM during render
- Most likely cause: an infinite loop, an animation with too many submobjects, or `run_time` set extremely high.
- Fix: cap any explicit loops to a small bound (e.g. <= 20 iterations). Reduce element count. Confirm no `while True:` slipped in.

### "AST safety check failed: forbidden import" or "forbidden name"
- Most likely cause: the previous code imported a banned module (`os`, `sys`, `subprocess`, etc.) or called a banned builtin (`eval`, `exec`, `open`).
- Fix: remove the import and any code that depended on it. If a file path was being constructed, hard-code the value into the source instead. If randomness was needed, use `random` (which is allowed).

### Validation failure ("class Main not found" / "construct method missing")
- Most likely cause: class was named something else, or the method was named `setup`/`build` instead of `construct`.
- Fix: rename to exactly `class Main(Scene):` and `def construct(self):`.

## Output

Return only the Python source for the corrected file. Nothing else.

<!-- pushed to Supabase prompts table by scripts/seed_prompts.py on next deploy -->
