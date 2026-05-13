"""Stage 7 — Compose.

Stitches per-scene MP4s + per-scene WAV (silent in v1) into final MP4.
Generates an SRT caption file from the narration since there's no real audio yet.

Implementation uses ffmpeg via subprocess. The Modal image has ffmpeg apt-installed.

Pipeline:
  1. Download all scene mp4s and wavs to a temp dir.
  2. For each scene: mux mp4 + wav -> scene_with_audio.mp4 (ffmpeg).
  3. Concat all scene_with_audio.mp4 -> final.mp4 (ffmpeg concat demuxer).
  4. Build SRT from word_timings + visual_cues.
  5. Upload final.mp4 + final.srt; return FinalVideo.
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
from datetime import timedelta
from pathlib import Path

from workers.lib.errors import ComposeError
from workers.lib.schemas import (
    AudioOutput,
    FinalVideo,
    RenderedScene,
    Script,
)
from workers.lib.supabase_client import (
    download_artifact,
    upload_artifact,
    upload_video,
)

log = logging.getLogger(__name__)


async def run_compose(ctx, rendered: list[RenderedScene], audio: list[AudioOutput],
                      script: Script) -> FinalVideo:
    if not rendered:
        raise ComposeError("No rendered scenes — cannot compose final video")
    if len(rendered) != len(audio):
        raise ComposeError(f"Scene/audio count mismatch: {len(rendered)} vs {len(audio)}")

    # Index audio by scene_id for fast lookup.
    audio_by_scene = {a.scene_id: a for a in audio}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        per_scene_paths: list[Path] = []
        for r in rendered:
            a = audio_by_scene.get(r.scene_id)
            if not a:
                raise ComposeError(f"No audio for scene {r.scene_id}")

            mp4_path = tmp_path / f"{r.scene_id}.mp4"
            wav_path = tmp_path / f"{r.scene_id}.wav"
            mux_path = tmp_path / f"{r.scene_id}_muxed.mp4"

            mp4_path.write_bytes(_download_mp4(ctx.supabase, r.mp4_storage_path))
            wav_path.write_bytes(download_artifact(ctx.supabase, a.audio_storage_path))

            _mux_video_with_audio(mp4_path, wav_path, mux_path)
            per_scene_paths.append(mux_path)

        final_mp4_path = tmp_path / "final.mp4"
        _concat_videos(per_scene_paths, final_mp4_path)
        final_bytes = final_mp4_path.read_bytes()

    # Build SRT captions from script.
    srt = _build_srt(script, audio_by_scene)
    srt_path = upload_artifact(ctx.supabase, ctx.job_id, "captions.srt", srt,
                               content_type="application/x-subrip")

    video_path = upload_video(ctx.supabase, ctx.job_id, "final.mp4", final_bytes)

    duration = sum(r.duration_sec for r in rendered)
    fallback_count = sum(1 for r in rendered if r.is_fallback)

    return FinalVideo(
        job_id=ctx.job_id,
        mp4_storage_path=video_path,
        duration_sec=duration,
        scene_count=len(rendered),
        fallback_scene_count=fallback_count,
        resolution=(854, 480),     # Composed at -ql; bump in Week 4 once render speed stabilizes.
        has_audio=False,
        caption_srt_path=srt_path,
    )


# ─── ffmpeg helpers ────────────────────────────────────────────────────────────


def _mux_video_with_audio(video: Path, audio: Path, out: Path) -> None:
    """Mux v + a into a single MP4. -shortest trims to shorter stream."""
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(video),
        "-i", str(audio),
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise ComposeError(f"ffmpeg mux failed: {res.stderr[-500:]}")


def _concat_videos(parts: list[Path], out: Path) -> None:
    """Concat MP4s using ffmpeg's concat demuxer — fast, no re-encode."""
    listfile = out.parent / "concat.txt"
    listfile.write_text("\n".join(f"file '{p}'" for p in parts), encoding="utf-8")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "concat", "-safe", "0",
        "-i", str(listfile),
        "-c", "copy",
        str(out),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise ComposeError(f"ffmpeg concat failed: {res.stderr[-500:]}")


def _download_mp4(client, path: str) -> bytes:
    return _download_with_retry(client.storage.from_("videos"), path)


def _download_with_retry(bucket, path: str, max_attempts: int = 3) -> bytes:
    """Retry storage downloads with exponential backoff on transient timeouts."""
    import time
    last_err: Exception | None = None
    for i in range(max_attempts):
        try:
            return bucket.download(path)
        except Exception as e:
            last_err = e
            if i + 1 < max_attempts:
                time.sleep(2 ** i)
    raise last_err if last_err else RuntimeError("download failed without an error")


# ─── SRT generation ───────────────────────────────────────────────────────────


def _build_srt(script: Script, audio_by_scene: dict[str, AudioOutput]) -> str:
    """Build a caption SRT from the narration. Times are sequential across scenes."""
    lines: list[str] = []
    cue_index = 1
    cursor_sec = 0.0

    for scene in script.scenes:
        audio = audio_by_scene.get(scene.scene_id)
        scene_duration = audio.duration_sec if audio else scene.estimated_duration_sec

        # One caption per ~10 words to keep them readable.
        words = scene.narration_md.split()
        if not words:
            cursor_sec += scene_duration
            continue

        chunk_size = 10
        per_word = scene_duration / max(len(words), 1)

        for i in range(0, len(words), chunk_size):
            chunk = words[i : i + chunk_size]
            start = cursor_sec + i * per_word
            end = cursor_sec + min(i + chunk_size, len(words)) * per_word
            lines.append(f"{cue_index}")
            lines.append(f"{_fmt_srt_ts(start)} --> {_fmt_srt_ts(end)}")
            lines.append(" ".join(chunk))
            lines.append("")
            cue_index += 1

        cursor_sec += scene_duration

    return "\n".join(lines)


def _fmt_srt_ts(seconds: float) -> str:
    td = timedelta(seconds=seconds)
    total_ms = int(td.total_seconds() * 1000)
    hh, rem = divmod(total_ms, 3_600_000)
    mm, rem = divmod(rem, 60_000)
    ss, ms = divmod(rem, 1000)
    return f"{hh:02d}:{mm:02d}:{ss:02d},{ms:03d}"
