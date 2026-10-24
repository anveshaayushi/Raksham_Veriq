"""Claude B: voice (synthetic-voice cue) package. Entry point for the app: voice.analyse(file_id, data, filename)."""
from voice.service import analyse  # noqa: F401

__all__ = ["analyse"]
