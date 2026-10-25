"""scripts/stt_check.py with a FAKE model: counts, similarity and output files (no real speech-to-text here)."""
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

from voice import transcribe as T

ROOT = Path(__file__).resolve().parents[2]


def _load():
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("stt_check", ROOT / "scripts" / "stt_check.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Fake:
    def transcribe(self, path, **kw):
        return iter([SimpleNamespace(text="Yeh offer sirf aaj ke liye hai")]), SimpleNamespace(language="hi", language_probability=0.9)


def test_stt_check_counts_and_compares_with_the_sentence(tmp_path):
    m = _load()
    (tmp_path / "data" / "hinglish" / "real").mkdir(parents=True)
    (tmp_path / "data" / "hinglish" / "real" / "x_02.wav").write_bytes(b"RIFF" + bytes(100))
    (tmp_path / "data" / "hinglish" / "real" / "x_09.wav").write_bytes(b"RIFF" + bytes(100))
    T.set_model(Fake(), "fake:check")
    try:
        r = m.run(tmp_path)
    finally:
        T.reset_model()
    assert r["clips"] == 2 and r["with_text"] == 2
    sims = {x["sentence"]: x["similarity"] for x in r["rows"]}
    assert sims[2] > 0.7 and sims[9] < sims[2]
    assert "2/2 clips produced text" in m.markdown(r)
