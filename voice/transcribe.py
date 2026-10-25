"""Speech-to-text for voice notes with faster-whisper (declared on the pre-event form). Plugs into CR-8:
for kind="voice" the app puts the transcript into Message.text, keyed by media_ref (see app/adapters/extract.py).

    transcribe(file_id, data: bytes, filename) -> Transcript        # never raises
    python -m voice.transcribe path\\to\\clip.opus                   # prints the Transcript as JSON

Plain words: the transcript lets the rules read what the voice note SAYS (payee, amount, "pay now") the same way they read
typed chat. It is only as good as the speech-to-text: Hinglish (Hindi and English mixed) can come out in Devanagari, in Latin
letters, or half and half, and numbers or names may be wrong. So transcript-derived cues stay medium confidence (never high),
and a transcript never clears or accuses a payee.

Status: written and unit-tested with a FAKE model. NOT yet run with the real faster-whisper model: the weights must be
downloaded once on a machine with internet (the first transcribe() call does it; or run `python -m voice.transcribe clip.wav`).
After that it runs offline. Nothing is stored: audio goes through a private temp folder that is deleted before returning.

Config (environment): VERIQ_WHISPER_MODEL (default "small"; "tiny"/"base" are faster, "medium" is better for Hindi),
VERIQ_WHISPER_LANGUAGE (default: auto-detect; set "hi" or "en" to force), VERIQ_WHISPER_DIR (model cache folder, optional).
"""
from __future__ import annotations

import json
import os
import tempfile
import threading
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

from voice.audio import MAX_FILE_BYTES

_ALLOWED_EXT = {".opus", ".ogg", ".oga", ".m4a", ".mp3", ".wav", ".flac", ".aac", ".amr", ".mp4", ".webm", ".mov", ".wma"}
_lock = threading.Lock()
_state: dict = {"loaded": False, "model": None, "error": None, "name": None}


@dataclass(frozen=True)
class Transcript:
    file_id: str
    text: str                       # "" when nothing could be transcribed
    language: Optional[str]         # detected language code, e.g. "hi", "en"; None if unknown
    language_probability: Optional[float]
    error: Optional[str]            # plain reason when text is empty because of a failure; None otherwise
    model: str                      # e.g. "faster-whisper:small"

    def to_dict(self) -> dict:
        return asdict(self)


def _empty(file_id: str, error: str, model: str = "none") -> Transcript:
    return Transcript(file_id, "", None, None, error, model)


def _load() -> dict:
    with _lock:
        if _state["loaded"]:
            return _state
        name = os.environ.get("VERIQ_WHISPER_MODEL", "small")
        try:
            from faster_whisper import WhisperModel

            kw = {"device": "cpu", "compute_type": "int8"}
            if os.environ.get("VERIQ_WHISPER_DIR"):
                kw["download_root"] = os.environ["VERIQ_WHISPER_DIR"]
            _state.update(model=WhisperModel(name, **kw), error=None, name=f"faster-whisper:{name}")
        except Exception as e:  # missing package / no weights and no internet: degrade, never crash
            _state.update(model=None, error=f"{type(e).__name__}: {e}"[:240], name=f"faster-whisper:{name}")
        _state["loaded"] = True
        return _state


def set_model(model, name: str = "fake", error: Optional[str] = None) -> None:
    """Tests only: inject an object with .transcribe(path, **kw) -> (segments, info)."""
    with _lock:
        _state.update(loaded=True, model=model, error=error, name=name)


def reset_model() -> None:
    with _lock:
        _state.update(loaded=False, model=None, error=None, name=None)


def transcribe(file_id: str, data: bytes, filename: str = "") -> Transcript:
    fid = file_id if isinstance(file_id, str) and file_id.strip() else "unknown-file"
    try:
        return _transcribe(fid, data, filename)
    except Exception as e:  # last-resort guard
        return _empty(fid, f"internal_error:{type(e).__name__}")


def _transcribe(fid: str, data, filename) -> Transcript:
    if not isinstance(data, (bytes, bytearray, memoryview)):
        return _empty(fid, "no_audio_data: expected bytes")
    data = bytes(data)
    if not data:
        return _empty(fid, "empty_file")
    if len(data) > MAX_FILE_BYTES:
        return _empty(fid, "file_too_large")
    st = _load()
    if st["model"] is None:
        return _empty(fid, f"speech_to_text_unavailable: {st['error']}", st["name"] or "none")
    ext = Path(str(filename or "")).suffix.lower()
    if ext not in _ALLOWED_EXT:
        ext = ".bin"
    kw = {"beam_size": 1, "vad_filter": True}
    lang = os.environ.get("VERIQ_WHISPER_LANGUAGE")
    if lang:
        kw["language"] = lang
    with tempfile.TemporaryDirectory(prefix="veriq_stt_") as td:
        p = Path(td) / ("clip" + ext)
        p.write_bytes(data)
        try:
            segments, info = st["model"].transcribe(str(p), **kw)
            text = " ".join(s.text.strip() for s in segments).strip()
        except Exception as e:
            return _empty(fid, f"transcription_failed:{type(e).__name__}", st["name"])
    lp = getattr(info, "language_probability", None)
    return Transcript(fid, text, getattr(info, "language", None), None if lp is None else float(lp), None, st["name"])


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("usage: python -m voice.transcribe <audio file>")
        raise SystemExit(2)
    pth = Path(sys.argv[1])
    try:
        raw = pth.read_bytes()
    except OSError as e:
        print(f"cannot read {pth}: {e}")
        raise SystemExit(1)
    print(json.dumps(transcribe(pth.name, raw, pth.name).to_dict(), indent=2, ensure_ascii=False))
