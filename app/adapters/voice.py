"""Voice adapter.

Uses Claude B's module when importable (ASSUMED signature, see CHANGES_REQUESTED.md CR-C4):
    voice.analyse(file_id: str, data: bytes, filename: str) -> VoiceResult
Otherwise returns `cant_assess` with the reason "voice module not connected (stub)". The stub never returns
`no_signal`, so a missing detector can never look like a clean voice check.
"""

from __future__ import annotations

from ..contracts import VoiceResult

STUB_VERSION = "stub (no detector connected)"


def analyse(file_id: str, data: bytes, filename: str) -> tuple[object, bool]:
    """Returns (VoiceResult, is_stub)."""
    try:
        import voice as b_voice  # type: ignore  # Claude B

        if hasattr(b_voice, "analyse"):
            return b_voice.analyse(file_id, data, filename), False
    except ImportError:
        pass
    except Exception as e:  # present but failing: never crash, never invent a score
        return VoiceResult(file_id=file_id, state="cant_assess", score=None, threshold=None, speech_seconds=0.0,
                           reasons=(f"voice module error ({type(e).__name__})",), model_version=STUB_VERSION), True
    return VoiceResult(file_id=file_id, state="cant_assess", score=None, threshold=None, speech_seconds=0.0,
                       reasons=("Voice detector not connected in this v0 skeleton (stub). No analysis was run.",),
                       model_version=STUB_VERSION), True
