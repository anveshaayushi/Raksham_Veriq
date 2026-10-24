"""Quality gate (brief section 7): decide whether a clip is fit to be scored at all.

Plain words: if the clip is too short, silent, clipped or too long, any score would
be noise. We say "can't assess" instead of guessing. Failing the gate is NOT a
finding about the audio; it only means we abstain.

All thresholds below are PROVISIONAL DEFAULTS chosen by Claude B, not tuned on any
data and not taken from the Round 1 deck. Retune on a dev split and record the
change in RESULTS.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import numpy as np

from voice.vad import speech_mask, speech_seconds


@dataclass(frozen=True)
class GateConfig:
    min_duration_s: float = 1.0
    min_speech_s: float = 1.0
    max_duration_s: float = 180.0  # brief section 19: example cap 3 minutes
    max_clip_fraction: float = 0.01
    clip_level: float = 0.999
    silent_peak: float = 1e-4


@dataclass
class GateReport:
    passed: bool
    reasons: List[str] = field(default_factory=list)
    duration_s: float = 0.0
    speech_s: float = 0.0
    clip_fraction: float = 0.0


def run_gate(x: np.ndarray, cfg: GateConfig = GateConfig(), sr: int = 16000) -> GateReport:
    if x.size == 0:
        return GateReport(False, ["empty_audio"])
    dur = x.size / sr
    mask, flen = speech_mask(x, sr)
    sp = speech_seconds(mask, flen, sr)
    clip = float(np.mean(np.abs(x) >= cfg.clip_level))
    rep = GateReport(True, [], dur, sp, clip)
    if dur < cfg.min_duration_s:
        rep.reasons.append(f"too_short({dur:.2f}s<{cfg.min_duration_s}s)")
    if dur > cfg.max_duration_s:
        rep.reasons.append(f"exceeds_max_duration(>{cfg.max_duration_s:.0f}s)")
    if float(np.max(np.abs(x))) < cfg.silent_peak:
        rep.reasons.append("silent")
    if clip > cfg.max_clip_fraction:
        rep.reasons.append(f"clipping({clip:.3f}>{cfg.max_clip_fraction})")
    if sp < cfg.min_speech_s and "silent" not in rep.reasons:
        rep.reasons.append(f"speech_below_min({sp:.2f}s<{cfg.min_speech_s}s)")
    rep.passed = not rep.reasons
    return rep
