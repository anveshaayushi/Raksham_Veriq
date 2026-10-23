"""Test double of Claude B's voice/stub.py. "A" is contract-valid; "B" violates A's contract (no_signal without a
threshold) so the app's fallback can be tested."""
from core.schemas import VoiceResult


def stub_result(key: str):
    if key == "A":
        return VoiceResult(file_id="stub-A", state="no_signal", score=0.2, threshold=0.5, speech_seconds=5.0,
                           reasons=["B stub for A"], model_version="voice-stub-b")
    if key == "C":
        return VoiceResult(file_id="stub-C", state="cant_assess", score=None, threshold=None, speech_seconds=0.3,
                           reasons=["B stub for C"], model_version="voice-stub-b")
    return VoiceResult(file_id=f"stub-{key}", state="no_signal", score=-3.1, threshold=None, speech_seconds=5.0,
                       reasons=[f"B stub for {key}"], model_version="voice-stub-b")
