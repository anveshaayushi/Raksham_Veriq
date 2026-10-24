"""Voice lane: file -> VoiceResult (brief sections 3.3, 7, 20).

Flow: decode (ffmpeg, 16 kHz mono) -> quality gate -> speech-only chunks ->
detector -> aggregate (mean) -> calibration -> three-state result.

Invariants (property-tested in tests/voice_eval):
  * Never raises: any failure becomes state="cant_assess" with a reason.
  * "no_signal" is NOT "genuine". Its reason text says so. The voice lane cannot clear anyone.
  * Without a valid calibration for THIS model, the state is cant_assess (raw score is kept
    in Assessment.raw_score for inspection). No made-up threshold exists in this codebase.
  * Only "flagged" is a review cue (class E, escalates to R4 in the rules).

force_score=True is for the batch evaluator only (brief section 20): even when the gate
rejects a clip, still compute a score so a forced binary pred_label can be reported. The
product path (force_score=False) keeps score=None on gate failure.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import numpy as np

from core.schemas import VoiceResult
from voice.audio import (
    MAX_FILE_BYTES,
    TARGET_SR,
    AudioDecodeError,
    decode_to_mono16k,
    sha256_file,
)
from voice.calibration import Calibration
from voice.gate import GateConfig, run_gate
from voice.vad import speech_mask, speech_samples

NO_SIGNAL_NOTE = "no_manipulation_signal_detected: this does not mean the audio is genuine"
FLAG_NOTE = "score_on_manipulation_side_of_threshold: possible manipulation cues, review only"


@dataclass
class Assessment:
    result: VoiceResult
    pred_label: Optional[str] = None  # "fake" | "real" | None (forced binary, eval only)
    raw_score: Optional[float] = None
    score_kind: str = "raw"
    elapsed_s: float = 0.0


def make_chunks(x: np.ndarray, chunk_len: int, max_chunks: int = 12) -> List[np.ndarray]:
    """Split into fixed-length chunks; tile short audio; evenly subsample if too many."""
    if x.size == 0:
        return []
    if x.size < chunk_len:
        return [np.tile(x, int(np.ceil(chunk_len / x.size)))[:chunk_len]]
    n = x.size // chunk_len
    chunks = [x[i * chunk_len : (i + 1) * chunk_len] for i in range(n)]
    rem = x[n * chunk_len :]
    if rem.size >= chunk_len // 2:
        chunks.append(np.tile(rem, int(np.ceil(chunk_len / rem.size)))[:chunk_len])
    if len(chunks) > max_chunks:
        idx = sorted(set(np.linspace(0, len(chunks) - 1, max_chunks).round().astype(int).tolist()))
        chunks = [chunks[i] for i in idx]
    return chunks


def _cant(fid: str, reasons: List[str], mv: str, speech_s: float = 0.0, **kw) -> Assessment:
    return Assessment(
        VoiceResult(fid, "cant_assess", None, None, round(speech_s, 3), reasons, mv),
        **kw,
    )


def assess_audio_file(
    path: str | Path,
    detector,
    calibration: Optional[Calibration],
    gate_cfg: GateConfig = GateConfig(),
    *,
    file_id: Optional[str] = None,
    force_score: bool = False,
    decode_timeout_s: float = 30.0,
    detector_error: Optional[str] = None,
    max_chunks: int = 12,
) -> Assessment:
    t0 = time.perf_counter()
    mv = getattr(detector, "model_version", "none")
    p = Path(path)
    fid = file_id or p.name
    try:
        a = _assess(p, fid, file_id is None, detector, calibration, gate_cfg, force_score,
                    decode_timeout_s, detector_error, max_chunks, mv)
    except Exception as e:  # last-resort guard: the tool must never crash
        a = _cant(fid, [f"internal_error:{type(e).__name__}"], mv)
    a.elapsed_s = time.perf_counter() - t0
    return a


def _assess(p, fid, auto_id, detector, calibration, gate_cfg, force_score,
            decode_timeout_s, detector_error, max_chunks, mv) -> Assessment:
    if not p.is_file():
        return _cant(fid, ["file_not_found"], mv)
    size = p.stat().st_size
    if size == 0:
        return _cant(fid, ["empty_file"], mv)
    if size > MAX_FILE_BYTES:
        return _cant(fid, ["file_too_large"], mv)
    if auto_id:  # only invent an id when the caller gave none; a caller's file_id is echoed unchanged
        try:
            fid = sha256_file(p)
        except OSError:
            pass

    try:
        x = decode_to_mono16k(p, timeout_s=decode_timeout_s, max_seconds=gate_cfg.max_duration_s)
    except AudioDecodeError as e:
        return _cant(fid, [e.code + (f"({e.detail})" if e.detail else "")], mv)

    gate = run_gate(x, gate_cfg, TARGET_SR)
    if not gate.passed and not force_score:
        return _cant(fid, gate.reasons, mv, gate.speech_s)

    if detector is None:
        why = detector_error or "no detector configured"
        return _cant(fid, gate.reasons + [f"no_detector: {why}"], mv, gate.speech_s)

    mask, flen = speech_mask(x, TARGET_SR)
    sp = speech_samples(x, mask, flen)
    material = sp if sp.size >= TARGET_SR // 4 else x  # forced path may fall back to whole clip
    chunks = make_chunks(material, detector.chunk_samples, max_chunks)
    try:
        scores = detector.score_chunks(chunks)
    except Exception as e:
        return _cant(fid, gate.reasons + [f"detector_error:{type(e).__name__}"], mv, gate.speech_s)
    if not scores or not all(np.isfinite(scores)):
        return _cant(fid, gate.reasons + ["detector_error:non_finite_score"], mv, gate.speech_s)
    raw = float(np.mean(scores))

    usable_cal = calibration is not None and calibration.model_version == mv
    cal_reasons: List[str] = []
    if calibration is None:
        cal_reasons.append("uncalibrated: no calibration file; raw score kept for inspection only")
    elif not usable_cal:
        cal_reasons.append("calibration_model_mismatch: threshold belongs to a different model")

    pred = None
    thr = None
    kind = "raw"
    if usable_cal:
        thr = calibration.threshold
        kind = calibration.score_kind
        pred = "fake" if calibration.is_fake_side(raw) else "real"

    sp_s = round(gate.speech_s, 3)
    if not gate.passed:
        # only reachable when force_score=True (batch evaluator)
        res = VoiceResult(fid, "cant_assess", raw, thr, sp_s, gate.reasons + cal_reasons, mv)
    elif not usable_cal:
        res = VoiceResult(fid, "cant_assess", raw, None, sp_s, cal_reasons, mv)
    elif pred == "fake":
        res = VoiceResult(fid, "flagged", raw, thr, sp_s, [FLAG_NOTE], mv)
    else:
        res = VoiceResult(fid, "no_signal", raw, thr, sp_s, [NO_SIGNAL_NOTE], mv)
    return Assessment(res, pred_label=pred, raw_score=raw, score_kind=kind)
