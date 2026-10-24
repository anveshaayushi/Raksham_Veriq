"""voice/detector.py (Claude B's AASIST adapter) without the real AASIST download (Q1 test completeness).

A tiny stand-in "AASIST repo" is written to a temp folder: same layout (config/AASIST.conf, models/AASIST.py with
class Model, models/weights/AASIST.pth) and same output shape (160-number embedding, 2 logits). It is NOT AASIST and
says nothing about accuracy; it proves the adapter code paths (loading, batching, version string, errors, CLI) run.
The real model is exercised by test_real_aasist_if_available when VERIQ_AASIST_REPO points at a real clone.
"""
from __future__ import annotations

import json
import os
import runpy
import sys
from pathlib import Path

import numpy as np
import pytest

torch = pytest.importorskip("torch", reason="voice extras (torch) not installed: pip install -r requirements-voice.txt")

from voice import detector as D  # noqa: E402

pytestmark = pytest.mark.filterwarnings("ignore:.*found in sys.modules:RuntimeWarning")

FAKE_MODEL = '''
import torch
class Model(torch.nn.Module):
    """Stand-in with AASIST's interface only: forward(x[B, 64600]) -> (hidden[B, 160], logits[B, 2])."""
    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.lin = torch.nn.Linear(4, 2)
    def forward(self, x):
        f = torch.stack([x.mean(1), x.std(1), x.abs().amax(1), (x ** 2).mean(1)], 1)
        return f.repeat(1, 40), self.lin(f)
'''


def _forget_models_package():
    for k in [k for k in sys.modules if k == "models" or k.startswith("models.")]:
        del sys.modules[k]


@pytest.fixture()
def fake_repo(tmp_path):
    repo = tmp_path / "aasist"
    (repo / "config").mkdir(parents=True)
    (repo / "models" / "weights").mkdir(parents=True)
    (repo / "config" / "AASIST.conf").write_text(json.dumps({"model_config": {"nb_samp": 64600}}))
    (repo / "models" / "AASIST.py").write_text(FAKE_MODEL)
    _forget_models_package()
    sys.path.insert(0, str(repo))
    try:
        from models.AASIST import Model
        torch.manual_seed(0)
        torch.save(Model({}).state_dict(), repo / "models" / "weights" / "AASIST.pth")
    finally:
        sys.path.remove(str(repo))
        _forget_models_package()
    yield repo
    _forget_models_package()


def test_loads_scores_in_batches_and_versions_by_weights_hash(fake_repo):
    det = D.AasistDetector(repo_dir=str(fake_repo), batch_size=2)
    assert det.chunk_samples == 64600 and det.native_polarity == "higher_is_real"
    assert det.model_version == "aasist-pretrained@" + D._file_sha12(fake_repo / "models" / "weights" / "AASIST.pth")
    rng = np.random.default_rng(1)
    chunks = [rng.standard_normal(64600).astype(np.float32) * 0.1 for _ in range(5)]  # 5 chunks, batch 2: 3 batches
    s = det.score_chunks(chunks)
    assert len(s) == 5 and all(isinstance(v, float) for v in s)
    assert s == det.score_chunks(chunks)  # deterministic (eval mode, no dropout)


def test_env_var_repo_and_explicit_paths(fake_repo, monkeypatch):
    monkeypatch.setenv("VERIQ_AASIST_REPO", str(fake_repo))
    a = D.AasistDetector()
    b = D.AasistDetector(repo_dir=str(fake_repo), config=str(fake_repo / "config" / "AASIST.conf"),
                         weights=str(fake_repo / "models" / "weights" / "AASIST.pth"))
    assert a.model_version == b.model_version


def test_missing_repo_and_missing_files_raise_plain_errors(tmp_path, fake_repo):
    with pytest.raises(FileNotFoundError, match="AASIST repo dir not found"):
        D.AasistDetector(repo_dir=str(tmp_path / "nope"))
    (fake_repo / "models" / "weights" / "AASIST.pth").unlink()
    with pytest.raises(FileNotFoundError, match="missing AASIST file"):
        D.AasistDetector(repo_dir=str(fake_repo))


def test_selfcheck_cli_reports_loaded_and_not_loaded(fake_repo, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(sys, "argv", ["voice.detector", "--selfcheck", "--repo", str(fake_repo)])
    with pytest.raises(SystemExit) as e:
        runpy.run_module("voice.detector", run_name="__main__")
    assert e.value.code == 0 and "loaded. model_version=aasist-pretrained@" in capsys.readouterr().out
    _forget_models_package()
    monkeypatch.setattr(sys, "argv", ["voice.detector", "--selfcheck", "--repo", str(tmp_path / "missing")])
    with pytest.raises(SystemExit) as e:
        runpy.run_module("voice.detector", run_name="__main__")
    assert e.value.code == 1 and "NOT LOADED: FileNotFoundError" in capsys.readouterr().out


def test_cli_without_selfcheck_prints_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["voice.detector"])
    with pytest.raises(SystemExit):
        runpy.run_module("voice.detector", run_name="__main__")
    assert "--selfcheck" in capsys.readouterr().out


@pytest.mark.skipif(not os.environ.get("VERIQ_AASIST_REPO"), reason="real AASIST not configured: set VERIQ_AASIST_REPO")
def test_real_aasist_if_available():
    _forget_models_package()
    det = D.AasistDetector()
    assert det.model_version.startswith("aasist-pretrained@")
    (s,) = det.score_chunks([np.zeros(det.chunk_samples, dtype=np.float32)])
    assert np.isfinite(s)
    _forget_models_package()
