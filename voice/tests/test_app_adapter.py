"""Claude B's side of the app integration: C's adapter calling the REAL voice package (no test double)."""
import pytest

from app.adapters import voice as adapter
from voice import service

from helpers import FakeDetector, speechlike, write_wav
import shutil

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


@pytest.fixture(autouse=True)
def _iso():
    service.reset_backend()
    yield
    service.reset_backend()


def test_adapter_finds_entry_point_and_echoes_file_id_on_junk():
    vr, is_stub = adapter.analyse("PTT-1.opus", b"OggS....", "PTT-1.opus")
    assert is_stub is False  # a real analyse() was called, not the fallback
    assert vr.state == "cant_assess" and vr.score is None and vr.file_id == "PTT-1.opus"


@needs_ffmpeg
def test_adapter_hides_numbers_when_uncalibrated(tmp_path):
    service.set_backend(FakeDetector(2.0), None)
    data = write_wav(tmp_path / "c.wav", speechlike(6.0)).read_bytes()
    vr, _ = adapter.analyse("a.wav", data, "a.wav")
    assert vr.state == "cant_assess" and "no score shown" in adapter.score_display(vr)
