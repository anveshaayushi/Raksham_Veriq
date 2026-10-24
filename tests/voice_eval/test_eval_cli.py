import csv
import json
import shutil

import pytest

from eval import cli, fit_threshold
from eval import metrics as M
from voice.calibration import Calibration, save_calibration

from helpers import FakeDetector, speechlike, write_wav

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def test_metrics_basic():
    assert M.auc([2, 3], [0, 1]) == 1.0
    assert M.eer([2, 3], [0, 1]) == 0.0
    assert M.auc([1], [1]) == 0.5
    assert M.auc([], [1]) is None and M.eer([1], []) is None
    t = M.threshold_for_far(list(range(100)), 0.05)
    assert sum(s < t for s in range(100)) <= 5
    r = M.rates(["real", "real", "fake", "fake"], ["fake", "real", "real", None])
    assert r["false_alarm"] == 0.5 and r["miss"] == 1.0 and r["n_fake"] == 1


def _folder(tmp_path):
    d = tmp_path / "in"
    (d / "real").mkdir(parents=True)
    (d / "fake").mkdir()
    for i in range(3):
        write_wav(d / "real" / f"r{i}.wav", speechlike(5.0, seed=i))
        write_wav(d / "fake" / f"f{i}.wav", speechlike(5.0, seed=10 + i))
    write_wav(d / "short.wav", speechlike(0.3))
    (d / "junk.wav").write_bytes(b"\x00\x01garbage" * 100)
    (d / "chat.txt").write_text("20/10/2026, 8:59 pm - A: hello")
    (d / "pic.png").write_bytes(b"\x89PNG not really")
    (d / "bundle.zip").write_bytes(b"PK")
    (d / "weird.xyz").write_text("?")
    return d


@needs_ffmpeg
def test_cli_no_detector_one_row_per_file_never_crashes(tmp_path, capsys):
    d = _folder(tmp_path)
    out = tmp_path / "o" / "preds.csv"
    rc = cli.main(["--input", str(d), "--out", str(out), "--json", "--detector", "none"])
    assert rc == 0
    rows = list(csv.DictReader(open(out, encoding="utf-8")))
    assert len(rows) == 12  # 6 clips + short + junk + chat + png + zip + .xyz
    assert {r["state"] for r in rows} == {"cant_assess"}
    assert all(r["reasons"] for r in rows)
    mods = {r["file_id"]: r["modality"] for r in rows}
    assert mods["chat.txt"] == "chat" and mods["pic.png"] == "image" and mods["weird.xyz"] == "unknown"
    recs = json.loads(out.with_suffix(".json").read_text())
    assert len(recs) == 12 and isinstance(recs[0]["reasons"], list)
    assert out.with_suffix(".summary.json").exists()


@needs_ffmpeg
def test_cli_with_detector_calibration_and_labels(tmp_path, monkeypatch):
    d = _folder(tmp_path)
    monkeypatch.setattr(cli, "build_detector", lambda args: (FakeDetector(-1.0), None))
    cal = tmp_path / "cal.json"
    save_calibration(Calibration(0.0, "higher_is_real", "raw", "fake-test-v1", "unit test"), cal)
    out = tmp_path / "preds.csv"
    rc = cli.main(["--input", str(d), "--out", str(out), "--calibration", str(cal),
                   "--infer-labels-from-dirs"])
    assert rc == 0
    rows = {r["file_id"]: r for r in csv.DictReader(open(out, encoding="utf-8"))}
    r0 = rows["real/r0.wav"]
    assert r0["state"] == "flagged" and r0["pred_label"] == "fake" and r0["label"] == "real"
    assert r0["score"] != "" and r0["threshold"] != ""
    s = rows["short.wav"]
    assert s["state"] == "cant_assess" and s["pred_label"] == "fake"  # abstains AND forced label present
    summ = json.loads(out.with_suffix(".summary.json").read_text())
    m = summ["metrics_all_labelled"]
    assert m["false_alarm_at_threshold"] == 1.0 and m["miss_at_threshold"] == 0.0
    assert summ["abstention_rate_media"] > 0


def test_cli_bad_input_folder_is_usage_error(tmp_path):
    assert cli.main(["--input", str(tmp_path / "nope"), "--out", str(tmp_path / "p.csv")]) == 2


def test_fit_threshold_refuses_small_or_mixed(tmp_path):
    p = tmp_path / "dev.csv"
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["label", "score", "model_version"])
        w.writeheader()
        for i in range(5):
            w.writerow({"label": "real", "score": i, "model_version": "m"})
    assert fit_threshold.main(["--preds", str(p), "--calibrated-on", "x", "--out", str(tmp_path / "c.json")]) == 2
    with open(p, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["label", "score", "model_version"])
        w.writeheader()
        for i in range(40):
            w.writerow({"label": "real", "score": i, "model_version": "m"})
    assert fit_threshold.main(["--preds", str(p), "--calibrated-on", "unit", "--out", str(tmp_path / "c.json")]) == 0
    assert json.loads((tmp_path / "c.json").read_text())["model_version"] == "m"
