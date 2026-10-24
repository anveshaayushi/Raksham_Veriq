"""voice.analyse(): the one function the app calls for an uploaded voice note (CR-C4).

    analyse(file_id: str, data: bytes, filename: str) -> core.schemas.VoiceResult

Guarantees (each one is tested in voice/tests/test_analyse.py):
  * NEVER raises. Every failure becomes state "cant_assess" with at least one plain-English reason.
  * file_id is echoed back unchanged (it equals the chat's media_ref).
  * Until a calibration file exists FOR THE LOADED MODEL, the state is "cant_assess"; the raw score is kept in
    `score` with `threshold` None. The app hides such scores. Only a calibrated threshold can produce
    "no_signal" or "flagged", and "no_signal" never means "genuine".
  * Uploaded bytes are written to a private temp folder that is deleted before returning.

Backend (model + calibration) loads lazily on the first call and is cached, including a failed load, so a missing
model does not cost seconds on every call. Paths:
  AASIST repo: env VERIQ_AASIST_REPO, else <repo>/external/aasist
  calibration: env VERIQ_VOICE_CALIBRATION, else <repo>/voice/calibration.json (absent = uncalibrated)
"""
from __future__ import annotations

import os
import tempfile
import threading
from pathlib import Path
from typing import Optional

from core.schemas import VoiceResult
from voice.audio import MAX_FILE_BYTES
from voice.calibration import Calibration, CalibrationError, load_calibration
from voice.gate import GateConfig
from voice.pipeline import assess_audio_file

ROOT = Path(__file__).resolve().parent.parent
_ALLOWED_EXT = {".opus", ".ogg", ".oga", ".m4a", ".mp3", ".wav", ".flac", ".aac", ".amr", ".mp4", ".webm", ".mov", ".wma"}
_lock = threading.Lock()
_backend: dict = {"loaded": False, "detector": None, "error": None, "calibration": None}


def _cant(file_id: str, reason: str, model_version: str = "none") -> VoiceResult:
    return VoiceResult(file_id, "cant_assess", None, None, 0.0, [reason], model_version)


def _load_backend() -> dict:
    with _lock:
        if _backend["loaded"]:
            return _backend
        _backend.update(detector=None, error=None, calibration=None)
        try:
            from voice.detector import AasistDetector

            _backend["detector"] = AasistDetector()
        except Exception as e:  # missing torch / repo / weights: abstain, do not crash
            _backend["error"] = f"{type(e).__name__}: {e}"[:240]
        cal_path = Path(os.environ.get("VERIQ_VOICE_CALIBRATION") or ROOT / "voice" / "calibration.json")
        if cal_path.is_file():
            try:
                _backend["calibration"] = load_calibration(cal_path)
            except CalibrationError as e:
                _backend["error"] = ((_backend["error"] or "") + f" | calibration: {e}")[:300]
        _backend["loaded"] = True
        return _backend


def set_backend(detector, calibration: Optional[Calibration] = None, error: Optional[str] = None) -> None:
    """For tests and for the eval tools: inject a detector/calibration instead of loading from disk."""
    with _lock:
        _backend.update(loaded=True, detector=detector, calibration=calibration, error=error)


def reset_backend() -> None:
    with _lock:
        _backend.update(loaded=False, detector=None, error=None, calibration=None)


def analyse(file_id: str, data: bytes, filename: str = "") -> VoiceResult:
    fid = file_id if isinstance(file_id, str) and file_id.strip() else "unknown-file"
    try:
        return _analyse(fid, data, filename)
    except Exception as e:  # last-resort guard
        try:
            return _cant(fid, f"internal_error:{type(e).__name__}")
        except Exception:
            return VoiceResult("unknown-file", "cant_assess", None, None, 0.0, ["internal_error"], "none")


def _analyse(fid: str, data, filename) -> VoiceResult:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        return _cant(fid, "no_audio_data: expected bytes")
    data = bytes(data)
    if len(data) == 0:
        return _cant(fid, "empty_file")
    if len(data) > MAX_FILE_BYTES:
        return _cant(fid, "file_too_large")
    ext = Path(str(filename or "")).suffix.lower()
    if ext not in _ALLOWED_EXT:
        ext = ".bin"  # ffmpeg sniffs the real format; the name is never used as a path
    b = _load_backend()
    with tempfile.TemporaryDirectory(prefix="veriq_voice_") as td:
        p = Path(td) / ("clip" + ext)
        p.write_bytes(data)
        a = assess_audio_file(p, b["detector"], b["calibration"], GateConfig(), file_id=fid,
                              detector_error=b["error"])
    return a.result
