"""C-32: kit runner (veriq-eval --report) on a mixed kit, and the app's Kit tab function."""
from __future__ import annotations

import csv
import io
import shutil
import zipfile
from pathlib import Path

import pytest

from eval import cli

ROOT = Path(__file__).resolve().parents[2]
HAS_FFMPEG = shutil.which("ffmpeg") is not None


def _kit(d: Path) -> Path:
    for sub in ("real", "fake", "scam", "genuine"):
        (d / sub).mkdir(parents=True)
    shutil.copy(ROOT / "app" / "demo_media" / "demo_voice_real_human.wav", d / "real" / "r1.wav")
    shutil.copy(ROOT / "app" / "demo_media" / "demo_voice_synthetic_tts.wav", d / "fake" / "f1.wav")
    shutil.copy(ROOT / "app" / "demo_media" / "demo_qr_synthetic.png", d / "fake" / "qr.png")
    (d / "fake" / "broken.opus").write_bytes(b"OggS" + bytes(300))
    (d / "scam" / "s1.txt").write_text("13/10/2026, 6:02 pm - Rahul: Pay 18% tax to withdraw your profit to ramesh.k@upi now\n",
                                       encoding="utf-8")
    (d / "scam" / "s2.txt").write_text("13/10/2026, 6:02 pm - Rahul: Navyug here, pay the onboarding fee to sunita.t@upi\n",
                                       encoding="utf-8")
    (d / "genuine" / "g1.txt").write_text("14/10/2026, 10:00 am - Desk: Please add funds to navyug.brk@validhdfc\n",
                                          encoding="utf-8")
    (d / "genuine" / "notes.docx").write_bytes(b"PK\x03\x04")
    return d


def test_kit_runner_on_a_mixed_kit_never_crashes_and_reports(tmp_path, monkeypatch):
    d = _kit(tmp_path / "kit")
    lab = tmp_path / "labels.csv"
    with open(lab, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows([["file", "label", "claimed_firm", "bank_app_names"],
                                 ["scam/s1.txt", "scam", "Navyug Wealth", "ramesh.k@upi=SHREE GANESH TRADERS"],
                                 ["scam/s2.txt", "scam", "Navyug Wealth", ""],
                                 ["genuine/g1.txt", "genuine", "Navyug Broking Pvt Ltd",
                                  "navyug.brk@validhdfc=NAVYUG BROKING PVT LTD"],
                                 ["real/r1.wav", "real", "", ""], ["fake/f1.wav", "fake", "", ""],
                                 ["fake/qr.png", "fake", "", ""], ["fake/broken.opus", "fake", "", ""]])
    out, rep = tmp_path / "o" / "preds.csv", tmp_path / "o" / "report.md"
    assert cli.main(["--input", str(d), "--labels", str(lab), "--out", str(out), "--report", str(rep),
                     "--detector", "none"]) == 0
    rows = {r["file_id"]: r for r in csv.DictReader(open(out, encoding="utf-8"))}
    assert len(rows) == 8
    assert rows["scam/s1.txt"]["state"] == "flagged" and rows["scam/s1.txt"]["pred_label"] == "fake"
    assert rows["genuine/g1.txt"]["state"] == "no_signal" and rows["genuine/g1.txt"]["pred_label"] == "real"
    assert rows["scam/s2.txt"]["state"] == "cant_assess"  # no name check, no hard cue: abstains, never guesses
    assert "UPI QR payee: omsai.ent@ybl" in rows["fake/qr.png"]["reasons"] and rows["fake/qr.png"]["state"] == "cant_assess"
    assert rows["genuine/notes.docx"]["modality"] == "unknown"
    text = rep.read_text(encoding="utf-8")
    for must in ("False-positive rate", "Abstained", "Confusion matrix", "Failure cases", "Known limits", "## chat"):
        assert must in text
    assert "| fake/scam | 1 | 0 | 1 |" in text and "| real | 0 | 1 | 0 |" in text


def test_chat_timeout_becomes_cant_assess(monkeypatch):
    import time
    from eval import kit
    r = kit.with_timeout(lambda: time.sleep(2), 0.2)
    assert r["state"] == "cant_assess" and r["reasons"][0].startswith("timeout")
    r = kit.with_timeout(lambda: 1 / 0, 1)
    assert r["reasons"] == ["internal_error:ZeroDivisionError"]


def test_kit_zip_safety_and_app_kit_function(tmp_path):
    from app.views.kit import KitError, run_kit, unpack
    d = _kit(tmp_path / "kit")
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        for p in d.rglob("*"):
            if p.is_file():
                z.write(p, "mykit/" + p.relative_to(d).as_posix())
    out = run_kit(b.getvalue())
    assert out["n"] == 8 and "file_id" in out["csv"] and "## chat" in out["report"] and str(tmp_path) not in out["csv"]
    bad = io.BytesIO()
    with zipfile.ZipFile(bad, "w") as z:
        z.writestr("../evil.txt", "x")
    with pytest.raises(KitError, match="Unsafe"):
        unpack(bad.getvalue(), tmp_path / "x")
    bomb = io.BytesIO()
    with zipfile.ZipFile(bomb, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("big.txt", b"\0" * (10 * 1024 * 1024))
    with pytest.raises(KitError, match="zip bomb"):
        unpack(bomb.getvalue(), tmp_path / "y")
    with pytest.raises(KitError, match="Not a valid"):
        unpack(b"PK nope", tmp_path / "z")
