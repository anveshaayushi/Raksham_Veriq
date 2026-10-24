"""VERIQ's trained voice head on top of AASIST (FINALE, Claude C; trained by bench/voice/train_eval.py).

Plain words: AASIST turns ~4 s of audio into 160 numbers (an "embedding"). We trained a small logistic-regression
classifier on those numbers (train split of bench/voice/make_set.py: real FSDD speakers vs Kokoro TTS voices, all
Opus-compressed) and fixed its threshold on a separate dev split (<= 5% of genuine dev clips flagged).
Held-out test results are in bench/voice/results.json (they are small, synthetic and in-domain: see README).

It plugs into Claude B's pipeline through B's own Detector interface (voice.detector.Detector) and calibration file
format (voice.calibration), via voice.service.set_backend(). B's quality gate, chunking and three-state logic are
unchanged. A voice flag is still only a review cue in the rules: it never clears and never accuses a payee.

OFF BY DEFAULT since 25 Oct (Q2): on ASVspoof 2019 LA eval clips it never saw, this head scored AUC 0.457 and flagged
54% of genuine clips (results/asvspoof/HEAD_V1_CROSS_DATASET_ROWS.md): it learned our FSDD-vs-Kokoro set, not
"synthetic speech" in general. Turn it on only to demo the in-domain result: VERIQ_VOICE_HEAD=1. With it off, B's
default backend is used and uncalibrated AASIST abstains ("can't assess").
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
HEAD = ROOT / "bench" / "voice" / "head.json"
CAL = ROOT / "bench" / "voice" / "head_calibration.json"


class HeadDetector:
    """voice.detector.Detector protocol: name, model_version, chunk_samples, native_polarity, score_chunks()."""

    name = "aasist+veriq-head"
    native_polarity = "higher_is_fake"

    def __init__(self, base, params: dict, head_sha12: str, embed_fn=None):
        self.base = base
        self.chunk_samples = base.chunk_samples
        self.model_version = f"{base.model_version}+head@{head_sha12}"
        self._mean = np.asarray(params["mean"], dtype=np.float64)
        self._scale = np.asarray(params["scale"], dtype=np.float64)
        self._coef = np.asarray(params["coef"], dtype=np.float64)
        self._b = float(params["intercept"])
        self._embed = embed_fn or self._aasist_embed

    def _aasist_embed(self, chunks):
        torch = self.base._torch
        with torch.no_grad():
            t = torch.from_numpy(np.stack([np.asarray(c, dtype=np.float32) for c in chunks])).to(self.base._device)
            hidden, _ = self.base._model(t)
        return hidden.cpu().numpy()

    def score_chunks(self, chunks):
        if not len(chunks):
            return []
        z = (np.asarray(self._embed(chunks), dtype=np.float64) - self._mean) / self._scale
        return [float(v) for v in 1.0 / (1.0 + np.exp(-(z @ self._coef + self._b)))]


def load_head(base, embed_fn=None):
    """(HeadDetector, Calibration) or raises with a plain reason."""
    from voice.calibration import load_calibration

    raw = HEAD.read_bytes()
    det = HeadDetector(base, json.loads(raw), hashlib.sha256(raw).hexdigest()[:12], embed_fn)
    cal = load_calibration(CAL)
    if cal.model_version != det.model_version:
        raise ValueError(f"calibration is for {cal.model_version}, loaded model is {det.model_version}")
    return det, cal


_state = {"tried": False, "active": False, "reason": ""}


def ensure_installed() -> dict:
    """Install the trained head into Claude B's voice service once. Never raises."""
    if _state["tried"]:
        return _state
    _state["tried"] = True
    if os.environ.get("VERIQ_VOICE_HEAD", "0") != "1":
        _state["reason"] = "off (default; set VERIQ_VOICE_HEAD=1 to use the in-domain head)"
        return _state
    if not (HEAD.is_file() and CAL.is_file()):
        _state["reason"] = "head files missing"
        return _state
    try:
        from voice import service
        from voice.detector import AasistDetector

        det, cal = load_head(AasistDetector())
        service.set_backend(det, cal)
        _state.update(active=True, reason=det.model_version)
    except Exception as e:  # no torch / no AASIST weights / version mismatch: keep B's default backend
        _state["reason"] = f"not active: {type(e).__name__}: {str(e)[:160]}"
    return _state
