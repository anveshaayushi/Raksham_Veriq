"""Test double of Claude B's draft core/schemas.py: VoiceResult and MediaResult only (as reported 23 Oct)."""
from dataclasses import dataclass, field


@dataclass
class VoiceResult:
    file_id: str
    state: str
    score: float | None
    threshold: float | None
    speech_seconds: float
    reasons: list = field(default_factory=list)
    model_version: str = ""


@dataclass
class MediaResult:
    file_id: str
    modality: str
    state: str
