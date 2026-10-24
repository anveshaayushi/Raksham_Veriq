"""Voice paths that earlier tests did not reach (Q1 test completeness): the trained-head installer, the app's voice
adapter fallbacks, the `python -m voice` command, codec copies (voice/augment.py), decoder and service error paths.
Every test checks a behaviour, not just that a line ran: the voice step never crashes, never invents a score and
never clears a payee."""
from __future__ import annotations

import json
import runpy
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
import pytest

from app.adapters import voice as VA
from app.adapters import voice_head as vh
from voice import audio as A
from voice import service

HAS_FFMPEG = shutil.which("ffmpeg") is not None
needs_ffmpeg = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not installed")
pytestmark = pytest.mark.filterwarnings("ignore:.*found in sys.modules:RuntimeWarning")


def wav_bytes(seconds=2.0, sr=16000, freq=180.0):
    t = np.arange(int(sr * seconds)) / sr
    x = (0.2 * np.sin(2 * np.pi * freq * t) * (1 + 0.5 * np.sin(2 * np.pi * 3 * t))).astype(np.float32)
    import io
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    return b.getvalue()


@pytest.fixture(autouse=True)
def _clean_voice_state():
    service.reset_backend()
    vh._state.update(tried=False, active=False, reason="")
    yield
    service.reset_backend()
    vh._state.update(tried=False, active=False, reason="")


# ------------------------------------------------------------------ trained head installer ----
def test_head_installer_is_off_by_default(monkeypatch):
    monkeypatch.delenv("VERIQ_VOICE_HEAD", raising=False)
    st = vh.ensure_installed()
    assert st["active"] is False and "off (default" in st["reason"]
    assert vh.ensure_installed() is st  # tried once only


def test_head_installer_reports_missing_files(monkeypatch, tmp_path):
    monkeypatch.setenv("VERIQ_VOICE_HEAD", "1")
    monkeypatch.setattr(vh, "HEAD", tmp_path / "none.json")
    st = vh.ensure_installed()
    assert st == {"tried": True, "active": False, "reason": "head files missing"}


def test_head_installer_keeps_default_backend_when_aasist_cannot_load(monkeypatch):
    monkeypatch.setenv("VERIQ_VOICE_HEAD", "1")
    import voice.detector as det_mod

    class Broken:
        def __init__(self, *a, **k):
            raise FileNotFoundError("AASIST repo dir not found: x")

    monkeypatch.setattr(det_mod, "AasistDetector", Broken)
    st = vh.ensure_installed()
    assert st["active"] is False and st["reason"].startswith("not active: FileNotFoundError")
    assert service._backend["loaded"] is False  # B's default backend untouched


def test_head_installer_installs_into_b_service(monkeypatch):
    monkeypatch.setenv("VERIQ_VOICE_HEAD", "1")
    import voice.detector as det_mod
    base_version = json.loads(vh.HEAD.read_text())["base_model_version"]

    class Base:
        model_version = base_version
        chunk_samples = 64600

    monkeypatch.setattr(det_mod, "AasistDetector", Base)
    st = vh.ensure_installed()
    assert st["active"] is True and st["reason"].endswith("+head@" + vh.load_head(Base(), lambda c: c)[0].model_version.split("@")[-1])
    assert service._backend["detector"].name == "aasist+veriq-head"
    assert service._backend["calibration"].polarity == "higher_is_fake"


def test_head_embedding_uses_the_base_model_hidden_layer():
    torch = pytest.importorskip("torch", reason="voice extras (torch) not installed")

    class Base:
        model_version = json.loads(vh.HEAD.read_text())["base_model_version"]
        chunk_samples = 64600
        _torch = torch
        _device = "cpu"

        @staticmethod
        def _model(t):
            return t[:, :160] * 0 + 1.0, None

    det, _ = vh.load_head(Base())
    s = det.score_chunks([np.zeros(64600, dtype=np.float32)])
    assert len(s) == 1 and 0.0 < s[0] < 1.0
    assert det.score_chunks([]) == []


# ------------------------------------------------------------------ app adapter fallbacks ----
def test_adapter_without_voice_package_is_a_labelled_stub(monkeypatch):
    monkeypatch.setitem(sys.modules, "voice", None)  # import voice -> ImportError
    vr, stub = VA.analyse("PTT-1.opus", b"x", "PTT-1.opus")
    assert stub and vr.state == "cant_assess" and "not connected" in vr.reasons[0] and vr.score is None


def test_adapter_without_entry_point_and_with_crashing_entry_point(monkeypatch):
    import voice
    monkeypatch.delattr(voice, "analyse")
    vr, stub = VA.analyse("a.opus", b"x", "a.opus")
    assert stub and "no analyse() entry point" in vr.reasons[0]
    monkeypatch.setattr(voice, "analyse", lambda *a: (_ for _ in ()).throw(RuntimeError("boom")), raising=False)
    monkeypatch.setenv("VERIQ_VOICE_HEAD", "0")
    vr, stub = VA.analyse("a.opus", b"x", "a.opus")
    assert stub and vr.state == "cant_assess" and vr.reasons == ["voice module error (RuntimeError)"]


def test_demo_stub_paths(monkeypatch):
    r = VA.demo_stub("A", "PTT-9.opus")
    assert r.file_id == "PTT-9.opus" and "stub" in r.model_version
    import voice.stub as vs
    monkeypatch.setattr(vs, "stub_result", lambda s: {"state": "cant_assess", "file_id": "x"})
    assert VA.demo_stub("A", "f.opus") == {"state": "cant_assess", "file_id": "f.opus"}

    class Odd:  # a result type whose constructor rejects keywords: returned unchanged
        state = "cant_assess"

        def __init__(self, *a):
            pass

    odd = Odd()
    monkeypatch.setattr(vs, "stub_result", lambda s: odd)
    assert VA.demo_stub("A", "f.opus") is odd
    monkeypatch.setitem(sys.modules, "voice.stub", None)
    assert VA.demo_stub("A", "f.opus") is None


def test_score_display_and_observed_text():
    from core.schemas import VoiceResult
    real = VoiceResult("f", "flagged", 0.97, 0.9, 5.0, ["review"], "aasist-pretrained@x+head@y")
    assert VA.score_display(real) == "score 0.97 vs threshold 0.9"
    assert VA.score_display(VoiceResult("f", "cant_assess", 0.2, None, 5.0, ["u"], "aasist")) .startswith("no score")
    assert VA.observed_for_display("voice", "stub result (score 1.0)") == "stub result (numbers withheld: stub value)"
    assert VA.observed_for_display("payee_name", "SUNITA (2)") == "SUNITA (2)"


# ------------------------------------------------------------------ python -m voice ----
def test_voice_cli_usage_unreadable_and_ok(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["voice"])
    with pytest.raises(SystemExit) as e:
        runpy.run_module("voice", run_name="__main__")
    assert e.value.code == 2 and "usage" in capsys.readouterr().out
    monkeypatch.setattr(sys, "argv", ["voice", str(tmp_path / "missing.opus")])
    with pytest.raises(SystemExit) as e:
        runpy.run_module("voice", run_name="__main__")
    assert e.value.code == 1 and "cannot read" in capsys.readouterr().out
    f = tmp_path / "note.wav"
    f.write_bytes(b"")  # empty file: a valid answer (cant_assess), not a crash
    monkeypatch.setattr(sys, "argv", ["voice", str(f)])
    runpy.run_module("voice", run_name="__main__")
    out = json.loads(capsys.readouterr().out)
    assert out["file_id"] == "note.wav" and out["state"] == "cant_assess" and out["reasons"] == ["empty_file"]


# ------------------------------------------------------------------ codec copies ----
def test_available_codecs_without_ffmpeg(monkeypatch):
    from voice import augment

    def no_ffmpeg(*a, **k):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(augment.subprocess, "run", no_ffmpeg)
    assert augment.available_codecs() == []


@needs_ffmpeg
def test_augment_makes_compressed_copies_and_skips_what_it_cannot(tmp_path, capsys):
    from voice import augment
    have = augment.available_codecs()
    if not have:
        pytest.skip("this ffmpeg build has none of opus/mp3/amr-nb encoders")
    src = tmp_path / "in"
    (src / "sub").mkdir(parents=True)
    (src / "sub" / "a.wav").write_bytes(wav_bytes(1.0))
    (src / "notes.txt").write_text("not audio")
    (src / "bad.wav").write_bytes(b"RIFF....garbage")
    out = tmp_path / "out"
    assert augment.main(["--input", str(src), "--out", str(out), "--codecs", f"{have[0]},nosuchcodec"]) == 0
    text = capsys.readouterr().out
    assert "encoder not available" in text and "nosuchcodec" in text and "skip" in text and "wrote 1" in text
    produced = out / have[0] / "sub" / "a.wav"
    with wave.open(str(produced)) as w:
        assert w.getframerate() == 16000 and w.getnchannels() == 1 and w.getnframes() > 8000


# ------------------------------------------------------------------ decoder errors ----
def test_decoder_errors_are_codes_not_crashes(tmp_path, monkeypatch):
    p = tmp_path / "x.wav"
    p.write_bytes(wav_bytes(0.5))

    def missing(*a, **k):
        raise FileNotFoundError("ffmpeg")

    monkeypatch.setattr(A.subprocess, "run", missing)
    with pytest.raises(A.AudioDecodeError) as e:
        A.decode_to_mono16k(p)
    assert e.value.code == "ffmpeg_not_found"

    def slow(*a, **k):
        raise subprocess.TimeoutExpired("ffmpeg", 1)

    monkeypatch.setattr(A.subprocess, "run", slow)
    with pytest.raises(A.AudioDecodeError) as e:
        A.decode_to_mono16k(p)
    assert e.value.code == "decode_timeout"

    class P:
        def __init__(self, rc, out, err):
            self.returncode, self.stdout, self.stderr = rc, out, err

    for proc, code in [(P(1, b"", b"Output file does not contain any stream"), "no_audio_stream"),
                       (P(1, b"", b"Invalid data found when processing input"), "decode_failed"),
                       (P(1, b"", b""), "decode_failed"),
                       (P(0, b"", b""), "no_audio_stream"),
                       (P(0, np.array([np.nan, 0.1], dtype="<f4").tobytes(), b""), "decode_failed")]:
        monkeypatch.setattr(A.subprocess, "run", lambda *a, _p=proc, **k: _p)
        with pytest.raises(A.AudioDecodeError) as e:
            A.decode_to_mono16k(p)
        assert e.value.code == code


# ------------------------------------------------------------------ service error paths ----
def test_service_backend_load_failure_and_bad_calibration_abstain(tmp_path, monkeypatch):
    import voice.detector as det_mod

    class Broken:
        def __init__(self, *a, **k):
            raise ImportError("No module named 'torch'")

    monkeypatch.setattr(det_mod, "AasistDetector", Broken)
    bad = tmp_path / "cal.json"
    bad.write_text("{not json")
    monkeypatch.setenv("VERIQ_VOICE_CALIBRATION", str(bad))
    b = service._load_backend()
    assert b["detector"] is None and "ImportError" in b["error"] and "calibration" in b["error"]
    assert service._load_backend() is b  # cached, including the failure
    vr = service.analyse("n.ogg", wav_bytes(2.0), "n.weird-ext")
    assert vr.state == "cant_assess" and vr.file_id == "n.ogg" and vr.score is None


def test_service_last_resort_guard(monkeypatch):
    monkeypatch.setattr(service, "_analyse", lambda *a: (_ for _ in ()).throw(MemoryError()))
    vr = service.analyse("f.opus", b"x", "f.opus")
    assert vr.state == "cant_assess" and vr.reasons == ["internal_error:MemoryError"]
    monkeypatch.setattr(service, "_cant", lambda *a, **k: (_ for _ in ()).throw(ValueError()))
    vr = service.analyse("f.opus", b"x", "f.opus")
    assert vr.file_id == "unknown-file" and vr.reasons == ["internal_error"]


def test_service_rejects_oversize_before_touching_disk(monkeypatch):
    monkeypatch.setattr(service, "MAX_FILE_BYTES", 10)
    vr = service.analyse("big.opus", b"x" * 11, "big.opus")
    assert vr.reasons == ["file_too_large"] and vr.state == "cant_assess"
