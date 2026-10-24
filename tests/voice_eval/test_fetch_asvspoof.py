import csv
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import fetch_asvspoof_sample as F  # noqa: E402


def _fake_zip(path: Path):
    dev_proto = "\n".join(
        [f"LA_0001 LA_D_{i} - - bonafide" for i in range(10)]
        + [f"LA_0002 LA_D_{100 + i} - A07 spoof" for i in range(10)]
    )
    eval_proto = "\n".join(
        [f"LA_0003 LA_E_{i} - - bonafide" for i in range(6)]
        + [f"LA_0004 LA_E_{100 + i} - A16 spoof" for i in range(6)]
    )
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("LA/ASVspoof2019_LA_cm_protocols/ASVspoof2019.LA.cm.dev.trl.txt", dev_proto)
        z.writestr("LA/ASVspoof2019_LA_cm_protocols/ASVspoof2019.LA.cm.eval.trl.txt", eval_proto)
        z.writestr("LA/ASVspoof2019_LA_asv_protocols/ASVspoof2019.LA.asv.dev.gi.trl.txt", "ignore me")
        for i in list(range(10)) + [100 + i for i in range(10)]:
            z.writestr(f"LA/ASVspoof2019_LA_dev/flac/LA_D_{i}.flac", b"fLaC-fake-bytes")
        for i in list(range(6)) + [100 + i for i in range(6)]:
            z.writestr(f"LA/ASVspoof2019_LA_eval/flac/LA_E_{i}.flac", b"fLaC-fake-bytes")


def test_parse_and_pick_are_balanced_and_deterministic():
    rows = F.parse_protocol("LA_1 A_1 - - bonafide\nLA_1 A_2 - A07 spoof\nbad line\nLA_1 A_3 - - bonafide")
    assert rows == [("A_1", "bonafide"), ("A_2", "spoof"), ("A_3", "bonafide")]
    many = [(f"r{i}", "bonafide") for i in range(20)] + [(f"s{i}", "spoof") for i in range(20)]
    a = F.pick(many, 5, seed=1)
    assert a == F.pick(many, 5, seed=1)
    assert sum(l == "bonafide" for _, l in a) == 5 and sum(l == "spoof" for _, l in a) == 5


def test_fetch_from_local_zip_writes_layout_and_labels(tmp_path, monkeypatch):
    zpath = tmp_path / "LA.zip"
    _fake_zip(zpath)
    monkeypatch.setattr(F, "open_zip", lambda url: zipfile.ZipFile(zpath))
    out = tmp_path / "out"
    assert F.main(["--url", "x", "--out", str(out), "--n-per-class", "4"]) == 0
    dev_rows = list(csv.DictReader(open(out / "dev" / "labels.csv", encoding="utf-8")))
    assert len(dev_rows) == 8
    assert {r["label"] for r in dev_rows} == {"real", "fake"}
    assert all((out / "dev" / r["file"]).is_file() for r in dev_rows)
    assert dev_rows[0]["dataset"] == "asvspoof2019_la_dev" and dev_rows[0]["codec"] == "flac"
    assert len(list(csv.DictReader(open(out / "eval" / "labels.csv", encoding="utf-8")))) == 8


def test_dry_run_writes_nothing(tmp_path, monkeypatch):
    zpath = tmp_path / "LA.zip"
    _fake_zip(zpath)
    monkeypatch.setattr(F, "open_zip", lambda url: zipfile.ZipFile(zpath))
    out = tmp_path / "out"
    assert F.main(["--url", "x", "--out", str(out), "--dry-run"]) == 0
    assert not out.exists()
