Write the narration for one scene of an educational video. Apply the 3b1b style guide that has been provided as system context.

## Inputs for this scene

- **scene_id**: `{scene_id}`
- **concept**: {concept_name}
- **hook (from curriculum planner)**: {hook}
- **beat summary**: {beat_summary}
- **target duration**: {estimated_sec} seconds (~{estimated_sec} * 2.5 = approx word target)
- **tone hint**: {tone_hint}

## Supporting source material from the PDF

{source_context}

## Your output: a single JSON object matching the `ScriptScene` schema

```json
{{
  "scene_id": "{scene_id}",
  "narration_md": "the full narration as a markdown string. May include $...$ for inline math.",
  "visual_cues": [
    {{"at_word_index": <int>, "description": "what happens visually at this word"}}
  ],
  "estimated_duration_sec": <float, refined estimate based on word count / 2.5>
}}
```

## Visual cue requirements

- Anchor each cue to a specific 0-indexed word in `narration_md`.
- Cues must be strictly increasing by `at_word_index`. No two cues share the same index.
- 3-6 cues per scene; one cue every ~15-30 words.
- Describe what HAPPENS, not what code to write. The codegen stage produces the Manim.
- The first cue should land within the first 8 words. Open on a picture, not in silence.

## Equation handling

You will frequently get equations in the source material. Decide on a per-equation basis:

- **Describe, don't read**, when the equation is structural (a definition, a transformation rule, an identity). Tell the viewer what the equation *does* and let the visible math do the rest. Example: instead of "x sub k plus one equals x sub k minus eta times the gradient of f at x sub k," say "we step in the opposite direction of the gradient, scaled by a small factor."
- **Read at most one symbol or term aloud** when that symbol is the conceptual centerpiece of the scene and the viewer needs a name for it. Example: "this constant — we'll call it lambda — is the eigenvalue."
- **Never read every symbol of a multi-symbol equation**. That is the failure mode we are trying to prevent.
- Inline math in the narration uses `$...$` (markdown). Block equations belong on screen as a visual cue, not in the narration string.

## No meta-narration — concretely

The narrator is invisible. Specifically, do not produce:

- Phrases that refer to the video: "in this video," "we will see," "this section explains," "today we look at."
- Phrases that refer to the narrator: "I'll show you," "let me draw," "I want to point out."
- Phrases that refer to upcoming structure: "first we'll do X, then Y, then Z."
- Phrases that explain that an explanation is coming: "let me explain why."

Instead, just *do* the thing. The video happens; nobody announces it.

## Anti-patterns

- Starting with "In this scene..." or "Now we look at..."
- Reading equations aloud verbatim — describe what they *do*
- Bulleted lists in the narration
- Code-like cue descriptions ("self.play(...)")
- Generic excitement ("a beautiful result," "an amazing fact") with no specific reason given.
- A cue at word 0 that describes nothing visual ("scene begins"). Cues describe action.

## Contrastive examples (good vs bad)

### Hook A — eigenvectors

Bad:
> "In this video, we will look at eigenvectors. Eigenvectors are special vectors that, when a matrix is applied to them, scale rather than rotate. Let me show you why this is important."

Why bad: meta-narration ("in this video," "let me show you"), abstract-first, and the importance claim is empty.

Good:
> "Apply a linear transformation to a grid of vectors and watch what happens. Most of them swing off their original line. But a small number of arrows just stretch — they never leave their own track. Those are the ones we want to find."

Why good: opens on a visual action, names a concrete behavior ("never leave their own track"), and lets the term "eigenvector" arrive later.

### Hook B — gradient descent

Bad:
> "Gradient descent is an important optimization algorithm in machine learning. The update rule is x sub k plus one equals x sub k minus eta times the gradient of f. We'll now explore why it works."

Why bad: importance claim is unsupported, the equation is read symbol-by-symbol, and "we'll now explore" is a meta-cue.

Good:
> "Imagine you're standing on a foggy hillside. You can't see the valley, but you can feel which way the ground tilts under your feet. So you take a small step downhill, and then another. That is the whole idea, and the only thing we need to make precise is the word 'downhill'."

Why good: the scene's central abstraction (gradient) is introduced by metaphor first; the formal name is teed up without being demanded yet.

### Hook C — Fourier series

Bad:
> "The Fourier series is a famous result from analysis. Any periodic function can be written as an infinite sum of sines and cosines, as shown by the formula below."

Why bad: dry exposition, the word "famous" stands in for a reason to care, no picture.

Good:
> "Here is a square wave — ugly, with hard corners, the kind of shape that looks like it shouldn't have a clean formula. Now add a single sine. Then a second. A third. Watch the corners snap into place. Every shape, no matter how jagged, is in some sense a chord."

Why good: a specific visual ("square wave," "corners snap into place") leads, and the surprising claim is left ringing instead of explained away.

Return ONLY the JSON object. No prose around it.

<!-- pushed to Supabase prompts table by scripts/seed_prompts.py on next deploy -->
