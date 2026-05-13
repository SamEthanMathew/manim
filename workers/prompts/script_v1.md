Write the narration for one scene of an educational video. Apply the 3b1b style guide that has been provided as system context.

## Inputs for this scene

- **scene_id**: `{scene_id}`
- **concept**: {concept_name}
- **hook (from curriculum planner)**: {hook}
- **beat summary**: {beat_summary}
- **target duration**: {estimated_sec} seconds (~{estimated_sec} × 2.5 = approx word target)
- **tone hint**: {tone_hint}

## Supporting source material from the PDF

{source_context}

## Your output: a single JSON object matching the `ScriptScene` schema:

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
- Cues must be strictly increasing by `at_word_index`.
- 3-6 cues per scene; one cue every ~15-30 words.
- Describe what HAPPENS, not what code to write. The codegen stage produces the Manim.

## Anti-patterns

- ❌ Starting with "In this scene..." or "Now we look at..."
- ❌ Reading equations aloud verbatim — describe what they *do*
- ❌ Bulleted lists in the narration
- ❌ Code-like cue descriptions ("self.play(...)")

Return ONLY the JSON object. No prose around it.
