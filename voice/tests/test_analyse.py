"""Tests for voice.analyse(): the app's entry point. Synthetic audio + a fake detector only; no real model is run."""
import json
import shutil

import pytest

import voice
from core.schemas import VoiceResult
from voice import service
from voice.calibration import Calibration
from voice.stub import stub_result

from helpers import FakeDetector, speechlike, write_wav

needs_ffmpeg = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
CAL = Calibration(0.0, "higher_is_real", "raw", "fake-test-v1", "unit test")


@pytest.fixture(autouse=True)
def _isolate_backend():
    service.reset_backend()
    yield
    service.reset_backend()


@pytest.fixture
def clip(tmp_path):
    return write_wav(tmp_path / "c.wav", speechlike(6.0)).read_bytes()


def test_entry_point_exported():
    assert callable(voice.analyse)


# short ids on purpose: Windows limits an env var (pytest stores the test id in one) to 32767 chars
@pytest.mark.parametrize("bad", [b"", b"not audio at all", b"\x00\x01" * 3000, None, "text", 12],
                         ids=["empty", "text_bytes", "junk_6000_bytes", "none", "str", "int"])
def test_bad_input_never_raises_and_abstains(bad):
    service.set_backend(FakeDetector(1.0), CAL)
    r = voice.analyse("PTT-1.opus", bad, "PTT-1.opus")
    assert isinstance(r, VoiceResult)
    assert r.state == "cant_assess" and r.reasons and r.score is None
    assert r.file_id == "PTT-1.opus"


def test_blank_file_id_does_not_crash():
    r = voice.analyse("", b"", "x.opus")
    assert r.state == "cant_assess" and r.file_id


@needs_ffmpeg
def test_file_id_echoed_unchanged_even_if_it_looks_like_a_temp_name(clip):
    service.set_backend(FakeDetector(2.0), CAL)
    for fid in ("PTT-20261017-WA0004.opus", "clip.wav", "A B (1).opus"):
        assert voice.analyse(fid, clip, "whatever.wav").file_id == fid


@needs_ffmpeg
def test_uncalibrated_is_cant_assess_with_no_threshold(clip):
    service.set_backend(FakeDetector(2.0), None)
    r = voice.analyse("a.wav", clip, "a.wav")
    assert r.state == "cant_assess" and r.threshold is None
    assert any("uncalibrated" in x for x in r.reasons)


@needs_ffmpeg
def test_calibrated_paths_are_contract_valid(clip):
    service.set_backend(FakeDetector(3.0), CAL)
    ok = voice.analyse("a.wav", clip, "a.wav")
    assert ok.state == "no_signal" and ok.score == 3.0 and ok.threshold == 0.0
    assert "does not mean" in " ".join(ok.reasons)
    service.set_backend(FakeDetector(-3.0), CAL)
    bad = voice.analyse("a.wav", clip, "a.wav")
    assert bad.state == "flagged" and bad.score == -3.0


@needs_ffmpeg
def test_missing_model_abstains_with_reason(clip):
    service.set_backend(None, None, error="FileNotFoundError: no weights")
    r = voice.analyse("a.wav", clip, "a.wav")
    assert r.state == "cant_assess" and any("no weights" in x for x in r.reasons)


@needs_ffmpeg
def test_temp_files_are_deleted(clip, tmp_path, monkeypatch):
    import tempfile
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    service.set_backend(FakeDetector(1.0), CAL)
    voice.analyse("a.wav", clip, "a.wav")
    assert not [p for p in tmp_path.iterdir() if p.name.startswith("veriq_voice_")]


def test_stub_matches_what_the_app_expects():
    for s in ("A", "B", "C", "FLAGGED"):
        r = stub_result(s, "PTT-1.opus")
        assert r.file_id == "PTT-1.opus" and "stub" in r.model_version.lower()
        json.dumps(r.to_dict())
