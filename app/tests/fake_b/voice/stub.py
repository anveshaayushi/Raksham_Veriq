from core.schemas import VoiceResult

_STATES = {"A": "no_signal", "B": "no_signal", "C": "cant_assess", "FLAGGED": "flagged"}


def stub_result(key: str) -> VoiceResult:
    return VoiceResult(file_id=f"stub-{key}", state=_STATES[key], score=-3.1 if key != "C" else None, threshold=None,
                       speech_seconds=0.3 if key == "C" else 5.0, reasons=[f"B stub for {key}"], model_version="voice-stub-b")
