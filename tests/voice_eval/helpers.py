"""Synthetic test audio + a fake detector. NOT speech, NOT a model: only for exercising plumbing."""
import wave
from pathlib import Path

import numpy as np

SR = 16000


def write_wav(path: Path, x: np.ndarray, sr: int = SR) -> Path:
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())
    return path


def speechlike(seconds: float, seed: int = 0, amp: float = 0.3) -> np.ndarray:
    """Noise bursts (0.25 s on / 0.15 s off). Passes the energy VAD like loud-then-quiet speech would."""
    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    x = rng.standard_normal(n) * 0.001
    t = np.arange(n) / SR
    on = (t % 0.4) < 0.25
    x[on] = rng.standard_normal(on.sum()) * amp
    return np.clip(x, -0.95, 0.95).astype(np.float32)


class FakeDetector:
    """Returns a fixed score. Stands in for a model in tests only."""

    name = "fake"
    chunk_samples = 32000
    native_polarity = "higher_is_real"

    def __init__(self, score=0.0, model_version="fake-test-v1", raises=False):
        self.score = score
        self.model_version = model_version
        self.raises = raises

    def score_chunks(self, chunks):
        if self.raises:
            raise RuntimeError("boom")
        return [float(self.score)] * len(chunks)
