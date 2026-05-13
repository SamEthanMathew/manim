# Schema Contracts

**Owner**: M2 (Architect). All schema changes require an RFC PR with M2 as a required reviewer.

This document defines the wire-format contracts between pipeline stages. Pydantic implementations live in [`workers/lib/schemas.py`](../workers/lib/schemas.py). TypeScript mirrors are generated into [`packages/shared/schemas.ts`](../packages/shared/schemas.ts).

**Versioning**: Each schema has a `schema_version` field. Breaking changes bump the major. M2 maintains a migration note when bumping.

---

## Stage I/O Summary

| Stage | Input schema | Output schema |
|-------|--------------|---------------|
| 0 Ingest | (PDF bytes + metadata) | `IngestedDocument` |
| 1 Curriculum | `IngestedDocument` | `CurriculumPlan` |
| 2 Script | `CurriculumPlan` | `Script` |
| 3 Scene Spec | `ScriptScene` (one at a time, fan-out) | `SceneSpec` |
| 4 Codegen | `SceneSpec` + retrieved examples | `GeneratedScene` (Python source string) |
| 5 Render | `GeneratedScene` + `SceneSpec` | `RenderedScene` (mp4 storage path) |
| 6 Audio | `ScriptScene` | `AudioOutput` (silent WAV path in v1) |
| 7 Compose | list[`RenderedScene`] + list[`AudioOutput`] | `FinalVideo` (mp4 storage path) |

---

## IngestedDocument

The structured representation of an uploaded PDF, math-aware.

```yaml
schema_version: 1
fields:
  title: str                          # best-effort title detection
  sections: list[Section]
  metadata: DocumentMetadata
```

### Section

```yaml
fields:
  id: str                             # stable id, e.g. "sec-0", "sec-1.2"
  level: int                          # 1 = top, 2 = subsection, ...
  title: str
  prose_md: str                       # markdown; may contain $...$ LaTeX inline
  equations: list[str]                # standalone LaTeX blocks (no $ wrappers)
  figures: list[Figure]
```

### Figure

```yaml
fields:
  caption: str
  page: int
  storage_path: str | None            # if extracted, path in Supabase Storage
```

### DocumentMetadata

```yaml
fields:
  page_count: int                     # hard cap 50 in v1
  language: str                       # ISO code, "en" required in v1
  detected_subject: str | None        # math|cs|physics|chemistry|biology|other
  source_filename: str
  ingested_at: datetime
```

---

## CurriculumPlan

The pedagogical reorganization — not just a TOC dump. The planner picks a hook per concept and orders for understanding.

```yaml
schema_version: 1
fields:
  target_duration_sec: int            # default 600 (10 min)
  learning_objectives: list[str]      # 3-5 outcomes for the video
  concept_dag: list[Concept]          # prerequisite graph
  scene_outline: list[SceneOutline]   # ordered list, source of truth for Stage 2
```

### Concept

```yaml
fields:
  concept_id: str                     # stable, e.g. "eigenvalue"
  name: str                           # human-readable
  prerequisites: list[str]            # concept_ids that must come first
```

### SceneOutline

```yaml
fields:
  scene_id: str                       # stable, e.g. "scene-0"
  concept_id: str
  hook: str                           # the concrete puzzle/example that opens
  beat_summary: str                   # 2-3 sentence outline of what happens
  estimated_sec: float                # rough plan, refined in Stage 2
```

---

## Script

Stage 2 output — narration text + visual cue anchors. Narration is what *will be* spoken when TTS lands; for v1 it generates the silent-track duration.

```yaml
schema_version: 1
fields:
  scenes: list[ScriptScene]
```

### ScriptScene

```yaml
fields:
  scene_id: str                       # matches CurriculumPlan.scene_outline[*].scene_id
  narration_md: str                   # what will be spoken; markdown OK
  visual_cues: list[VisualCue]        # English descriptions, NOT code
  estimated_duration_sec: float       # ~ words * 0.4s (avg speaking rate)
```

### VisualCue

```yaml
fields:
  at_word_index: int                  # 0-indexed word in narration_md
  description: str                    # English: "unit circle appears, vector rotates 0 -> pi/2"
```

**Invariant**: `visual_cues[*].at_word_index` is strictly increasing.

---

## SceneSpec

**Critical contract.** This is the bridge between fuzzy English (Stage 2) and concrete Manim code (Stage 4). Stage 3 produces these; Stage 4 consumes them. Schema is strict — codegen retries until it validates.

```yaml
schema_version: 1
fields:
  scene_id: str
  duration_sec: float
  background: Color                   # hex string, default "#000000"
  elements: list[Element]             # declarative — what exists on stage
  timeline: list[Action]              # imperative — what happens, and when
```

### Element (discriminated union by `type`)

All elements have:
```yaml
fields:
  id: str                             # local to scene
  type: str                           # discriminator
```

Element types in v1:
- `MathTex`: `{type: "MathTex", id, latex: str, position: Position, scale: float}`
- `Text`: `{type: "Text", id, text: str, position, scale, font: str | None}`
- `Axes`: `{type: "Axes", id, x_range: [min, max, step], y_range: [...], position, scale}`
- `Vector`: `{type: "Vector", id, components: list[float], color: Color, anchor_id: str | None}`
- `Graph`: `{type: "Graph", id, function: str, x_range: [min, max], axes_id: str}`
- `Circle`: `{type: "Circle", id, radius: float, position, color, fill_opacity: float}`
- `Group`: `{type: "Group", id, member_ids: list[str]}`
- `Image`: `{type: "Image", id, storage_path: str, position, scale}`

### Position

```yaml
fields:
  x: float                            # Manim coords: roughly -7..7 horizontal
  y: float                            # -4..4 vertical
  z: float = 0
```

### Action

```yaml
fields:
  at_t: float                         # seconds from scene start
  duration_sec: float                 # how long the animation runs
  action: ActionKind                  # Create|FadeIn|FadeOut|Transform|Indicate|Write|Wait
  target_id: str | None               # element id, null for Wait
  params: dict                        # action-specific; documented per-kind below
```

#### Action params per `action`

| ActionKind | Required params |
|------------|-----------------|
| Create     | (none)          |
| FadeIn     | `from: Position?` |
| FadeOut    | `to: Position?` |
| Transform  | `to_id: str` (target element to morph into) |
| Indicate   | `color: Color = "#FFFF00"`, `scale_factor: float = 1.2` |
| Write      | (none) — for Text/MathTex |
| Wait       | (none) — `target_id` must be null |

---

## GeneratedScene (Stage 4 -> Stage 5)

```yaml
schema_version: 1
fields:
  scene_id: str
  python_source: str                  # one file, defines class Main(Scene)
  imports: list[str]                  # extracted by AST for safety check
  llm_model: str
  llm_attempt: int                    # 1-based
  generated_at: datetime
```

**Invariant**: Generated code defines a class named `Main` extending `manim.Scene` with a `construct(self)` method. The render harness invokes `manim -ql <file> Main`.

---

## RenderedScene (Stage 5 -> Stage 7)

```yaml
schema_version: 1
fields:
  scene_id: str
  mp4_storage_path: str               # supabase storage URL
  duration_sec: float                 # actual rendered duration via ffprobe
  resolution: [int, int]              # e.g., [1920, 1080]
  is_fallback: bool                   # True if static-slide fallback was used
  render_attempts: int
```

---

## Audio Interface (Stage 6)

The TTS provider is a Protocol. v1 ships `NullTTSProvider` which emits silent WAV. ElevenLabs/OpenAI providers plug in later with zero pipeline rewrites.

### NarrationInput

```yaml
fields:
  text: str                           # narration_md (markdown stripped by adapter)
  voice_id: str | None
  pacing: PacingHints
```

### PacingHints

```yaml
fields:
  estimated_duration_sec: float
  pause_at_word_indices: list[int]    # for visual-cue alignment
  emphasis_word_indices: list[int]
```

### AudioOutput

```yaml
fields:
  scene_id: str
  audio_storage_path: str
  duration_sec: float
  word_timings: list[WordTiming]      # forced alignment; v1 = uniform spacing
  provider: str                       # "null"|"elevenlabs"|"openai"
```

### WordTiming

```yaml
fields:
  word: str
  start_sec: float
  end_sec: float
```

### TTSProvider (Protocol)

```python
class TTSProvider(Protocol):
    async def synthesize(self, n: NarrationInput, scene_id: str) -> AudioOutput: ...
```

Implementations in v1:
- `NullTTSProvider` — generates silent WAV at `pacing.estimated_duration_sec`, fakes uniform word timings.

Implementations deferred:
- `ElevenLabsTTSProvider` — Eleven v3 / multilingual v2, voice cloning.
- `OpenAITTSProvider` — `tts-1-hd`, cheaper fallback.

---

## FinalVideo (Stage 7 output)

```yaml
schema_version: 1
fields:
  job_id: uuid
  mp4_storage_path: str
  duration_sec: float
  scene_count: int
  fallback_scene_count: int           # how many fell back to static slide
  resolution: [int, int]
  has_audio: bool                     # False in v1 (silent + caption track)
  caption_srt_path: str | None        # SRT generated from narration
```

---

## Color

```yaml
type: str                             # hex with leading #, e.g. "#3498DB"
pattern: ^#[0-9A-Fa-f]{6}$
```

---

## Common Invariants Across Schemas

1. All `*_id` fields are strings, stable across pipeline stages for the same logical entity.
2. Floats representing seconds are non-negative.
3. List of items must not contain duplicate ids within the same parent.
4. `scene_id` in `ScriptScene`, `SceneSpec`, `GeneratedScene`, `RenderedScene`, `AudioOutput` must match for the same scene throughout the pipeline.
5. Empty optional fields are `null` (JSON), not omitted.

---

## Schema Change Process (for M2 + engineers)

1. Open RFC PR titled `RFC: schema <Name> v<N+1>`.
2. Update this file with new fields + a migration note.
3. Update `workers/lib/schemas.py` Pydantic models.
4. Regenerate `packages/shared/schemas.ts` (script: `pnpm run codegen:schemas`).
5. Add a `tests/integration/test_schema_migration.py` case if the change is backward-incompatible.
6. M2 reviews. After merge, M1 notifies all engineers in next standup.
