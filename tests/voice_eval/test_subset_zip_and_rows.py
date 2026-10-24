"""Tests for the zip-reading subset builder and the results-row generator. Synthetic audio only; proves plumbing, not accuracy."""
import csv
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from tests.voice_eval.helpers import speechlike, write_wav

ROOT = Path(__file__).resolve().parents[2]
needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def _fake_la_zip(tmp: Path) -> Path:
    zp = tmp / "LA.zip"
    protocol = []
    with zipfile.ZipFile(zp, "w") as z:
        for i in range(6):
            name = f"LA_D_{i:07d}"
            lab = "bonafide" if i % 2 == 0 else "spoof"
            protocol.append(f"LA_0001 {name} - A0{i} {lab}")
            wav = write_wav(tmp / f"{name}.wav", speechlike(2.0, seed=i))
            flac = tmp / f"{name}.flac"
            subprocess.run(["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-i", str(wav), str(flac)], check=True)
            z.write(flac, f"LA/ASVspoof2019_LA_dev/flac/{name}.flac")
        z.writestr("LA/ASVspoof2019_LA_cm_protocols/ASVspoof2019.LA.cm.dev.trl.txt", "\n".join(protocol) + "\n")
    return zp


@needs_ffmpeg
def test_subset_reads_straight_from_zip(tmp_path):
    zp = _fake_la_zip(tmp_path)
    out = tmp_path / "dev"
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_asvspoof_subset.py"), "--zip", str(zp), "--split", "dev",
                        "--n-real", "2", "--n-fake", "2", "--out", str(out)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    rows = list(csv.DictReader(open(out / "labels.csv", encoding="utf-8")))
    assert len(rows) == 4 and {x["label"] for x in rows} == {"real", "fake"}
    assert all((out / x["file"]).is_file() for x in rows)
    assert not (out / ".tmp").exists()


def test_subset_needs_exactly_one_source(tmp_path):
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_asvspoof_subset.py"), "--split", "dev", "--out", str(tmp_path)],
                       capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 2


def test_wilson_interval_sane():
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_results_rows as m
    lo, hi = m.wilson(5, 100)
    assert 0.01 < lo < 0.05 < hi < 0.12
    assert m.wilson(0, 0) == (None, None)


def test_results_rows_from_csv(tmp_path):
    p = tmp_path / "preds.csv"
    fields = ["file_id", "state", "pred_label", "score", "label", "dataset", "codec", "model_version"]
    with open(p, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for i in range(30):
            w.writerow({"file_id": f"r{i}", "state": "no_signal", "pred_label": "real", "score": 2.0 + i / 10, "label": "real",
                        "dataset": "d", "codec": "clean", "model_version": "t-1"})
            w.writerow({"file_id": f"f{i}", "state": "flagged", "pred_label": "fake", "score": -2.0 - i / 10, "label": "fake",
                        "dataset": "d", "codec": "clean", "model_version": "t-1"})
    out = tmp_path / "rows.md"
    r = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_results_rows.py"), "--run", f"toy:{p}", "--command", "x",
                        "--out", str(out)], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stderr
    text = out.read_text(encoding="utf-8")
    assert "AUC 1.000" in text and "in-distribution" in text and "Wilson" in text
