"""Very simple energy-based voice activity detection (VAD).

Plain words: find the loud-enough parts of the clip so we measure "seconds of
speech", not "seconds of file".

LIMITATION (say this to judges): energy VAD cannot tell speech from other loud
sounds (music, a noisy room). It is a stand-in. Upgrade candidate for the
finale: Silero VAD or webrtcvad, behind the same function signature.
"""
from __future__ import annotations

import numpy as np

FRAME_MS = 30


def speech_mask(
    x: np.ndarray, sr: int = 16000, *, floor_db: float = -45.0, margin_db: float = 12.0
) -> tuple[np.ndarray, int]:
    """Return (boolean mask per frame, frame_len_samples).

    A frame counts as speech if its level is above max(floor_db, noise_floor + margin_db),
    where noise_floor is the 10th-percentile frame level of this clip.
    """
    frame_len = int(sr * FRAME_MS / 1000)
    n = len(x) // frame_len
    if n == 0:
        return np.zeros(0, dtype=bool), frame_len
    frames = x[: n * frame_len].reshape(n, frame_len).astype(np.float64)
    rms = np.sqrt(np.mean(frames**2, axis=1) + 1e-12)
    db = 20.0 * np.log10(rms)
    thr = max(floor_db, float(np.percentile(db, 10)) + margin_db)
    return db > thr, frame_len


def speech_seconds(mask: np.ndarray, frame_len: int, sr: int = 16000) -> float:
    return float(mask.sum()) * frame_len / sr


def speech_samples(x: np.ndarray, mask: np.ndarray, frame_len: int) -> np.ndarray:
    """Concatenate only the speech frames."""
    if mask.size == 0 or not mask.any():
        return np.zeros(0, dtype=np.float32)
    n = mask.size
    frames = x[: n * frame_len].reshape(n, frame_len)
    return frames[mask].reshape(-1).astype(np.float32)
