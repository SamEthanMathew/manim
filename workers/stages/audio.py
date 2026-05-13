"""Stage 6 — Audio.

V1 ships a silent track. The TTSProvider Protocol is the seam where
ElevenLabsTTSProvider or OpenAITTSProvider plugs in later.

Critical: the pipeline ALWAYS calls TTSProvider.synthesize() — never
conditional code paths. Swap the provider via config; no other changes.
"""
from __future__ import annotations

import logging
import tempfile
import wave
from pathlib import Path

from workers.lib.errors import AudioError
from workers.lib.schemas import (
    AudioOutput,
    NarrationInput,
    PacingHints,
    Script,
    SceneId,
    TTSProvider,
    WordTiming,
)
from workers.lib.supabase_client import upload_artifact

log = logging.getLogger(__name__)

DEFAULT_SAMPLE_RATE = 44100
WORDS_PER_SECOND_AVG = 2.5  # ~150 wpm narration


async def run_audio(ctx, script: Script) -> list[AudioOutput]:
    """Generate one audio track per scene using the configured provider.

    v1: always uses NullTTSProvider. Future: select via user_settings or env.
    """
    provider: TTSProvider = NullTTSProvider(ctx.supabase, ctx.job_id)

    outputs: list[AudioOutput] = []
    for scene in script.scenes:
        narration = NarrationInput(
            text=scene.narration_md,
            voice_id=None,
            pacing=PacingHints(
                estimated_duration_sec=scene.estimated_duration_sec,
                pause_at_word_indices=[c.at_word_index for c in scene.visual_cues],
                emphasis_word_indices=[],
            ),
        )
        try:
            output = await provider.synthesize(narration, scene.scene_id)
        except Exception as e:
            raise AudioError(f"Audio synthesis failed for {scene.scene_id}: {e}") from e
        outputs.append(output)

    return outputs


# ─── NullTTSProvider — v1 silent track ────────────────────────────────────────


class NullTTSProvider:
    """Emits silent WAV sized to estimated_duration_sec.

    Word timings are uniformly distributed across the duration so that
    Stage 7 (compose) can still align visual cues if needed.
    """

    def __init__(self, supabase_client, job_id: str):
        self.supabase = supabase_client
        self.job_id = job_id

    async def synthesize(self, n: NarrationInput, scene_id: SceneId) -> AudioOutput:
        duration = max(0.5, n.pacing.estimated_duration_sec)
        wav_bytes = _generate_silent_wav(duration)

        path = upload_artifact(
            self.supabase, self.job_id,
            f"audio/{scene_id}.wav", wav_bytes,
            content_type="audio/wav",
        )

        words = n.text.split()
        word_timings = _uniform_word_timings(words, duration)

        return AudioOutput(
            scene_id=scene_id,
            audio_storage_path=path,
            duration_sec=duration,
            word_timings=word_timings,
            provider="null",
        )


# ─── Future placeholder providers (interface check only) ──────────────────────


class ElevenLabsTTSProvider:
    """Placeholder so future imports don't break.

    Implementation deferred. When activated, the pipeline still calls
    `await provider.synthesize(...)` identically.
    """

    def __init__(self, api_key: str, voice_id: str):
        raise NotImplementedError("ElevenLabsTTSProvider not enabled in v1")

    async def synthesize(self, n: NarrationInput, scene_id: SceneId) -> AudioOutput:  # pragma: no cover
        raise NotImplementedError


class OpenAITTSProvider:
    """Placeholder for OpenAI tts-1-hd fallback."""

    def __init__(self, api_key: str, voice: str):
        raise NotImplementedError("OpenAITTSProvider not enabled in v1")

    async def synthesize(self, n: NarrationInput, scene_id: SceneId) -> AudioOutput:  # pragma: no cover
        raise NotImplementedError


# ─── Helpers ──────────────────────────────────────────────────────────────────


def _generate_silent_wav(duration_sec: float, sample_rate: int = DEFAULT_SAMPLE_RATE) -> bytes:
    """In-memory silent WAV bytes. PCM 16-bit mono, all zeros."""
    import io
    frame_count = int(duration_sec * sample_rate)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(b"\x00\x00" * frame_count)
    return buf.getvalue()


def _uniform_word_timings(words: list[str], duration_sec: float) -> list[WordTiming]:
    if not words:
        return []
    per_word = duration_sec / len(words)
    return [
        WordTiming(word=w, start_sec=i * per_word, end_sec=(i + 1) * per_word)
        for i, w in enumerate(words)
    ]
