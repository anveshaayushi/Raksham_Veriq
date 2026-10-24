"""Detector interface + pretrained AASIST adapter (Plan C, brief section 7).

STATUS: DRAFTED, NOT RUN. Written without access to torch, the AASIST repo or its
weights. The adapter follows the clovaai/aasist repo layout AS RECALLED FROM MEMORY
(config/AASIST.conf, models/AASIST.py class Model, models/weights/AASIST.pth, input of
64600 samples, class-1 logit = "bonafide"/real). Every one of those details must be
confirmed on your laptop with:

    python -m voice.detector --selfcheck --repo /path/to/aasist

That prints "loaded" plus one score on random noise. It proves the plumbing runs,
nothing about accuracy.

Plain words: a "detector" takes a ~4 s chunk of audio and returns one number. For
AASIST a HIGHER number means "more like real speech" (native_polarity). Which
number counts as "flag it" is decided only by the calibration file, never here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import List, Optional, Protocol, Sequence

import numpy as np


class Detector(Protocol):
    name: str
    model_version: str
    chunk_samples: int
    native_polarity: str  # "higher_is_real" | "higher_is_fake"

    def score_chunks(self, chunks: Sequence[np.ndarray]) -> List[float]:
        ...


def _file_sha12(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()[:12]


class AasistDetector:
    """Pretrained AASIST (Jung et al., ICASSP 2022; repo licence to be verified: README says MIT)."""

    name = "aasist"
    chunk_samples = 64600  # ~4.04 s at 16 kHz (value recalled from the repo; verify)
    native_polarity = "higher_is_real"

    def __init__(
        self,
        repo_dir: Optional[str] = None,
        weights: Optional[str] = None,
        config: Optional[str] = None,
        device: str = "cpu",
        batch_size: int = 8,
    ) -> None:
        default_repo = Path(__file__).resolve().parent.parent / "external" / "aasist"
        repo = Path(repo_dir or os.environ.get("VERIQ_AASIST_REPO") or default_repo)
        if not repo.is_dir():
            raise FileNotFoundError(
                f"AASIST repo dir not found: {repo}. Clone github.com/clovaai/aasist there, "
                f"or set VERIQ_AASIST_REPO (see voice/README.md)"
            )
        cfg_path = Path(config) if config else repo / "config" / "AASIST.conf"
        w_path = Path(weights) if weights else repo / "models" / "weights" / "AASIST.pth"
        for p in (cfg_path, w_path):
            if not p.is_file():
                raise FileNotFoundError(f"missing AASIST file: {p}")

        import torch  # lazy: keeps the rest of the project importable without torch

        sys.path.insert(0, str(repo))
        try:
            from models.AASIST import Model  # type: ignore
        finally:
            sys.path.remove(str(repo))

        model_cfg = json.loads(cfg_path.read_text())["model_config"]
        self._torch = torch
        self._model = Model(model_cfg).to(device)
        state = torch.load(str(w_path), map_location=device)
        self._model.load_state_dict(state)
        self._model.eval()
        self._device = device
        self._bs = batch_size
        # Version string ties any calibration file to these exact weights.
        self.model_version = f"aasist-pretrained@{_file_sha12(w_path)}"

    def score_chunks(self, chunks: Sequence[np.ndarray]) -> List[float]:
        torch = self._torch
        out: List[float] = []
        with torch.no_grad():
            for i in range(0, len(chunks), self._bs):
                batch = np.stack([np.asarray(c, dtype=np.float32) for c in chunks[i : i + self._bs]])
                t = torch.from_numpy(batch).to(self._device)
                _, logits = self._model(t)
                out.extend(float(v) for v in logits[:, 1].detach().cpu().numpy())
        return out


def _selfcheck(args: argparse.Namespace) -> int:
    try:
        det = AasistDetector(repo_dir=args.repo, weights=args.weights, config=args.config)
    except Exception as e:  # report, don't crash with a traceback wall
        print(f"NOT LOADED: {type(e).__name__}: {e}")
        return 1
    rng = np.random.default_rng(0)
    chunk = (rng.standard_normal(det.chunk_samples) * 0.05).astype(np.float32)
    s = det.score_chunks([chunk])[0]
    print(f"loaded. model_version={det.model_version}. score on random noise={s:.4f} "
          f"(plumbing check only; says nothing about accuracy)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--selfcheck", action="store_true")
    ap.add_argument("--repo")
    ap.add_argument("--weights")
    ap.add_argument("--config")
    a = ap.parse_args()
    raise SystemExit(_selfcheck(a) if a.selfcheck else ap.print_help())
