"""Tests for the NullTTSProvider — silent track generation."""
from __future__ import annotations

import wave
from io import BytesIO

import pytest

from workers.stages.audio import _generate_silent_wav, _uniform_word_timings


def test_silent_wav_has_correct_duration():
    wav_bytes = _generate_silent_wav(2.0, sample_rate=44100)
    with wave.open(BytesIO(wav_bytes), "rb") as w:
        frames = w.getnframes()
        rate = w.getframerate()
    duration = frames / rate
    assert abs(duration - 2.0) < 0.01


def test_silent_wav_is_silent():
    wav_bytes = _generate_silent_wav(0.1)
    with wave.open(BytesIO(wav_bytes), "rb") as w:
        data = w.readframes(w.getnframes())
    assert all(b == 0 for b in data)


def test_uniform_word_timings_distribute_evenly():
    words = ["one", "two", "three", "four"]
    timings = _uniform_word_timings(words, 4.0)
    assert len(timings) == 4
    assert pytest.approx(timings[0].start_sec) == 0.0
    assert pytest.approx(timings[-1].end_sec) == 4.0
    # Adjacent timings touch
    for prev, nxt in zip(timings, timings[1:], strict=False):
        assert prev.end_sec == nxt.start_sec
