"""Fixed VoiceResult per demo scenario (brief 17.1) for the app's demos.

THESE ARE PLACEHOLDERS, NOT MEASUREMENTS. Under Claude A's contract (core/schemas.py), `no_signal` and `flagged`
REQUIRE a score and a threshold, so the numbers below exist only to be contract-valid. They are arbitrary, every
result carries "stub" in model_version, and every reason says so. The app must never show them as a score.
Scenarios follow the Round 1 storyline: A suspicious, B legitimate broker, C too little speech.
"""
from __future__ import annotations

from core.schemas import VoiceResult

_NOTE = "stub: placeholder numbers for the demo, not a measurement and not from any detector"
_MV = "stub-NOT-A-MODEL"


def stub_result(scenario: str, file_id: str = "stub-voice-note") -> VoiceResult:
    s = str(scenario).upper()
    if s in ("A", "B"):
        return VoiceResult(file_id, "no_signal", 1.0, 0.0, 5.0,
                           ["no manipulation signal found (this does not mean the voice is genuine)", _NOTE], _MV)
    if s == "C":
        return VoiceResult(file_id, "cant_assess", None, None, 0.3,
                           ["speech_below_min: less than 1 second of speech", _NOTE], _MV)
    if s == "FLAGGED":
        return VoiceResult(file_id, "flagged", -1.0, 0.0, 5.0,
                           ["possible manipulation cues, for human review only", _NOTE], _MV)
    raise ValueError("scenario must be A, B, C or FLAGGED")
