"""bench/voice/cross_dataset.py end to end on a tiny made-up set, with embeddings supplied through its cache file
(no AASIST needed): the grouped cross-validation, the leave-one-dataset-out heads, the tables and the v2 export run."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import wave
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("sklearn", reason="voice extras not installed")


def _wav(seed: int) -> bytes:
    rng = np.random.default_rng(seed)
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes((rng.standard_normal(1600) * 3000).astype("<i2").tobytes())
    return b.getvalue()


def test_cross_dataset_script_on_cached_embeddings(tmp_path):
    from bench.voice import cross_dataset as X
    rng = np.random.default_rng(0)
    cache, seed = {}, [0]

    def clip(path: Path, fake: int):
        seed[0] += 1
        data = _wav(seed[0])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        emb = rng.normal(0, 1, 160) + (1.5 if fake else 0.0)
        cache[hashlib.sha256(data).hexdigest()] = np.concatenate([[-2.0 if fake else 2.0], emb])

    v = tmp_path / "v"
    rows = []
    for split in ("train", "dev", "test"):
        for spk in range(4):
            for i in range(3):
                for lab in ("real", "fake"):
                    name = f"{split}/{lab}_{split}{spk}_{i}.wav"
                    clip(v / name, lab == "fake")
                    rows.append([name, lab, f"{lab}{split}{spk}", split, "en", 1])
    with open(v / "labels.csv", "w", newline="") as f:
        csv.writer(f).writerows([["file", "label", "source", "split", "lang", "seconds"], *rows])
    for part in ("dev", "eval"):
        d = tmp_path / part
        lines = [["file", "label", "dataset", "codec", "language"]]
        for i in range(12):
            for lab in ("real", "fake"):
                for codec in ("clean", "mp3", "opus"):
                    name = f"{lab}/LA_{part}_{i}" + ("" if codec == "clean" else f"__{codec}") + ".wav"
                    clip(d / name, lab == "fake")
                    lines.append([name, lab, f"asv_{part}", codec, "en"])
        with open(d / "labels.csv", "w", newline="") as f:
            csv.writer(f).writerows(lines)
    out = tmp_path / "out"
    out.mkdir()
    np.savez(out / "embeddings_cache.npz", **cache)
    assert X.main(["--voiceset", str(v), "--asv-dev", str(tmp_path / "dev"), "--asv-eval", str(tmp_path / "eval"),
                   "--aasist", "unused", "--out", str(out), "--export-dir", str(tmp_path / "v2")]) == 0
    r = json.loads((out / "results.json").read_text())
    ae = r["results"]["AE (ASVspoof eval, unseen attacks + speakers)"]
    assert ae["head_v2 trained on V + ASVspoof dev (threshold: grouped CV)"]["all"]["auc"] > 0.9
    assert set(ae["head_v2 trained on V + ASVspoof dev (threshold: grouped CV)"]) == {"all", "clean", "mp3", "opus"}
    assert r["head_v2_cv"]["folds"] == 5 and r["train_n"]["head_v2"] == 2 * 4 * 3 * 2 + 72
    cal = json.loads((tmp_path / "v2" / "head_calibration.json").read_text())
    assert cal["polarity"] == "higher_is_fake" and "+head@" in cal["model_version"]
    assert "| AE (ASVspoof eval" in (out / "table.md").read_text()
