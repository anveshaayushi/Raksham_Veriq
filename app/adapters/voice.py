"""Voice adapter. Claude B owns voice/; this file only calls it.

Claude B, 23 Oct: the AASIST detector runs, but there is NO calibrated threshold yet, so every real result is
`cant_assess` (raw score kept). Until calibration exists, demos use `voice.stub.stub_result("A"|"B"|"C"|"FLAGGED")`.
Rules from B: only `flagged` may push to HUMAN_REVIEW; `no_signal` never clears a payee; `cant_assess` on present
audio means INCONCLUSIVE. Those are applied by Claude A's rules, not here.

Uploads call `voice.analyse(file_id, data, filename)` if B exposes it (entry point still to be confirmed, CR-C4);
otherwise `cant_assess`. This adapter never returns `no_signal` or `flagged` on its own.
"""

from __future__ import annotations

from ..contracts import VoiceResult, get

STUB_VERSION = "stub (no detector connected)"


def _cant(file_id: str, reason: str) -> object:
    return VoiceResult(file_id=file_id, state="cant_assess", score=None, threshold=None, speech_seconds=0.0,
                       reasons=(reason,), model_version=STUB_VERSION)


def analyse(file_id: str, data: bytes, filename: str) -> tuple[object, bool]:
    """Returns (VoiceResult, is_stub)."""
    try:
        import voice as b_voice  # type: ignore  # Claude B
    except ImportError:
        return _cant(file_id, "Voice detector not connected in this build (stub). No analysis was run."), True
    fn = getattr(b_voice, "analyse", None)
    if fn is None:
        return _cant(file_id, "Claude B's voice module is present but has no analyse() entry point yet (CR-C4)."), True
    try:
        return fn(file_id, data, filename), False
    except Exception as e:  # never crash, never invent a score
        return _cant(file_id, f"voice module error ({type(e).__name__})"), True


def demo_stub(scenario: str, file_id: str) -> object | None:
    """Claude B's per-scenario stub result, if voice.stub exists. Returns None when it doesn't."""
    try:
        from voice.stub import stub_result  # type: ignore  # Claude B
    except ImportError:
        return None
    r = stub_result(scenario)
    # keep B's values; only the file id is set to the demo's voice note
    if isinstance(r, dict):
        return {**r, "file_id": file_id}
    try:
        return type(r)(**{**{k: get(r, k) for k in ("state", "score", "threshold", "speech_seconds", "reasons", "model_version")},
                          "file_id": file_id})
    except Exception:
        return r


def score_display(v: object) -> str:
    """No calibrated threshold => no score is shown (Claude B: do not quote voice numbers)."""
    if get(v, "threshold") is None:
        return "no score shown: the detector has no calibrated threshold yet"
    return f"score {get(v, 'score')} vs threshold {get(v, 'threshold')}"
