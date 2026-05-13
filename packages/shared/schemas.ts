// Auto-mirrored from modal/lib/schemas.py per docs/contracts.md.
// In production, this is regenerated via `pnpm run codegen:schemas`
// from the Pydantic models. Hand-edited in v1 until codegen pipeline wires up.

// ─── Common ───────────────────────────────────────────────────────────────────

export type Color = string; // pattern: ^#[0-9A-Fa-f]{6}$
export type SceneId = string;

export interface Position {
  x: number;
  y: number;
  z?: number;
}

// ─── Stage 0 — IngestedDocument ──────────────────────────────────────────────

export type Subject = "math" | "cs" | "physics" | "chemistry" | "biology" | "other";

export interface Figure {
  caption: string;
  page: number;
  storage_path: string | null;
}

export interface Section {
  id: string;
  level: number;
  title: string;
  prose_md: string;
  equations: string[];
  figures: Figure[];
}

export interface DocumentMetadata {
  page_count: number;
  language: string;
  detected_subject: Subject | null;
  source_filename: string;
  ingested_at: string; // ISO datetime
}

export interface IngestedDocument {
  schema_version: number;
  title: string;
  sections: Section[];
  metadata: DocumentMetadata;
}

// ─── Stage 1 — CurriculumPlan ────────────────────────────────────────────────

export interface Concept {
  concept_id: string;
  name: string;
  prerequisites: string[];
}

export interface SceneOutline {
  scene_id: SceneId;
  concept_id: string;
  hook: string;
  beat_summary: string;
  estimated_sec: number;
}

export interface CurriculumPlan {
  schema_version: number;
  target_duration_sec: number;
  learning_objectives: string[];
  concept_dag: Concept[];
  scene_outline: SceneOutline[];
}

// ─── Stage 2 — Script ────────────────────────────────────────────────────────

export interface VisualCue {
  at_word_index: number;
  description: string;
}

export interface ScriptScene {
  scene_id: SceneId;
  narration_md: string;
  visual_cues: VisualCue[];
  estimated_duration_sec: number;
}

export interface Script {
  schema_version: number;
  scenes: ScriptScene[];
}

// ─── Stage 3 — SceneSpec ─────────────────────────────────────────────────────

interface ElementBase {
  id: string;
  type: string;
}

export interface MathTexElement extends ElementBase {
  type: "MathTex";
  latex: string;
  position: Position;
  scale: number;
}
export interface TextElement extends ElementBase {
  type: "Text";
  text: string;
  position: Position;
  scale: number;
  font: string | null;
}
export interface AxesElement extends ElementBase {
  type: "Axes";
  x_range: [number, number, number];
  y_range: [number, number, number];
  position: Position;
  scale: number;
}
export interface VectorElement extends ElementBase {
  type: "Vector";
  components: number[];
  color: Color;
  anchor_id: string | null;
}
export interface GraphElement extends ElementBase {
  type: "Graph";
  function: string;
  x_range: [number, number];
  axes_id: string;
}
export interface CircleElement extends ElementBase {
  type: "Circle";
  radius: number;
  position: Position;
  color: Color;
  fill_opacity: number;
}
export interface GroupElement extends ElementBase {
  type: "Group";
  member_ids: string[];
}
export interface ImageElement extends ElementBase {
  type: "Image";
  storage_path: string;
  position: Position;
  scale: number;
}

export type Element =
  | MathTexElement
  | TextElement
  | AxesElement
  | VectorElement
  | GraphElement
  | CircleElement
  | GroupElement
  | ImageElement;

export type ActionKind =
  | "Create"
  | "FadeIn"
  | "FadeOut"
  | "Transform"
  | "Indicate"
  | "Write"
  | "Wait";

export interface Action {
  at_t: number;
  duration_sec: number;
  action: ActionKind;
  target_id: string | null;
  params: Record<string, unknown>;
}

export interface SceneSpec {
  schema_version: number;
  scene_id: SceneId;
  duration_sec: number;
  background: Color;
  elements: Element[];
  timeline: Action[];
}

// ─── Stage 5 — RenderedScene ─────────────────────────────────────────────────

export interface RenderedScene {
  schema_version: number;
  scene_id: SceneId;
  mp4_storage_path: string;
  duration_sec: number;
  resolution: [number, number];
  is_fallback: boolean;
  render_attempts: number;
}

// ─── Stage 7 — FinalVideo ────────────────────────────────────────────────────

export interface FinalVideo {
  schema_version: number;
  job_id: string;
  mp4_storage_path: string;
  duration_sec: number;
  scene_count: number;
  fallback_scene_count: number;
  resolution: [number, number];
  has_audio: boolean;
  caption_srt_path: string | null;
}

// ─── Job lifecycle ───────────────────────────────────────────────────────────

export type JobStatus =
  | "pending"
  | "ingesting"
  | "scripting"
  | "awaiting_approval"
  | "rendering"
  | "composing"
  | "done"
  | "failed"
  | "cancelled";

export type JobEventKind = "started" | "progress" | "completed" | "error" | "retry";

export interface Job {
  id: string;
  user_id: string;
  status: JobStatus;
  pdf_storage_path: string;
  target_duration_sec: number;
  approved: boolean;
  final_video_path: string | null;
  error_message: string | null;
  cost_estimate_usd: number | null;
  created_at: string;
  updated_at: string;
}

export interface JobEvent {
  id: number;
  job_id: string;
  stage: string;
  kind: JobEventKind;
  payload: Record<string, unknown>;
  created_at: string;
}
