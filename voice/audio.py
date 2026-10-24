"""Decode any audio/video file to 16 kHz mono float32 using ffmpeg (brief section 7).

Plain words: phones send voice notes as .opus/.m4a/.mp4. We convert them all to one
simple format first so the rest of the code sees the same thing every time.
Failure never raises past this module's callers as a crash: it raises
AudioDecodeError with a short machine-readable code, which becomes "cant_assess".
"""
from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path

import numpy as np

TARGET_SR = 16000
MAX_FILE_BYTES = 200 * 1024 * 1024


class AudioDecodeError(Exception):
    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


def sha256_file(path: str | Path, bufsize: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(bufsize)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def decode_to_mono16k(
    path: str | Path, *, timeout_s: float = 30.0, max_seconds: float = 180.0
) -> np.ndarray:
    """Return float32 samples in [-1, 1] at 16 kHz mono.

    Decodes at most max_seconds + 1 s so a huge file cannot hog time/memory; the
    caller can tell it was too long because the result exceeds max_seconds.
    Video containers: -vn drops the picture and keeps the audio track only.
    """
    cap = float(max_seconds) + 1.0
    cmd = [
        "ffmpeg", "-nostdin", "-hide_banner", "-loglevel", "error",
        "-i", f"file:{path}",
        "-vn", "-ac", "1", "-ar", str(TARGET_SR),
        "-t", f"{cap}",
        "-f", "f32le", "pipe:1",
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=timeout_s)
    except FileNotFoundError:
        raise AudioDecodeError("ffmpeg_not_found", "install ffmpeg and put it on PATH")
    except subprocess.TimeoutExpired:
        raise AudioDecodeError("decode_timeout", f">{timeout_s}s")
    err = proc.stderr.decode(errors="replace")
    if proc.returncode != 0:
        if "does not contain any stream" in err or "Stream map" in err:
            raise AudioDecodeError("no_audio_stream")
        last = err.strip().splitlines()[-1][:200] if err.strip() else ""
        raise AudioDecodeError("decode_failed", last)
    n = len(proc.stdout) // 4
    if n == 0:
        raise AudioDecodeError("no_audio_stream", "decoder produced zero samples")
    x = np.frombuffer(proc.stdout[: n * 4], dtype="<f4").astype(np.float32)
    if not np.all(np.isfinite(x)):
        raise AudioDecodeError("decode_failed", "non-finite samples")
    return x
