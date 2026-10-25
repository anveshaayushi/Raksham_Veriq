import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_prompts_have_matched_real_and_fake_texts():
    sys.path.insert(0, str(ROOT / "scripts"))
    import hinglish_build as h
    assert len(h.SENTENCES) == 12 and all(len(t) == 3 and t[0] and t[1] for t in h.SENTENCES)
    assert {t[2] for t in h.SENTENCES} == {"pressure", "ordinary"}


def test_labels_scan(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / "scripts"))
    import hinglish_build as h
    monkeypatch.setattr(h, "BASE", tmp_path)
    (tmp_path / "real").mkdir()
    (tmp_path / "fake").mkdir()
    (tmp_path / "real" / "a_01.opus").write_bytes(b"x")
    (tmp_path / "fake" / "v_01.wav").write_bytes(b"x")
    (tmp_path / "fake" / "notes.txt").write_bytes(b"x")
    assert h.cmd_labels(None) == 0
    text = (tmp_path / "labels.csv").read_text(encoding="utf-8").splitlines()
    assert len(text) == 3 and "real/a_01.opus,real" in text[1]


def test_finish_script_imports_and_skips_cleanly():
    r = subprocess.run([sys.executable, "-c", "import sys; sys.path.insert(0,'scripts'); import b_finish_all"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
