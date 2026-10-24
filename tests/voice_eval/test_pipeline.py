import shutil

import numpy as np
import pytest

from voice.calibration import Calibration, CalibrationError, load_calibration, save_calibration
from voice.pipeline import NO_SIGNAL_NOTE, assess_audio_file, make_chunks

from helpers import FakeDetector, SR, speechlike, write_wav

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")

CAL = Calibration(threshold=0.0, polarity="higher_is_real", score_kind="raw", model_version="fake-test-v1")


@pytest.fixture
def good(tmp_path):
    return write_wav(tmp_path / "good.wav", speechlike(6.0))


def test_flagged_below_threshold(good):
    a = assess_audio_file(good, FakeDetector(-2.0), CAL)
    assert a.result.state == "flagged"
    assert a.result.score == -2.0 and a.result.threshold == 0.0
    assert a.pred_label == "fake"


def test_no_signal_above_threshold_and_never_claims_genuine(good):
    a = assess_audio_file(good, FakeDetector(3.0), CAL)
    assert a.result.state == "no_signal"
    assert a.pred_label == "real"
    assert a.result.reasons == [NO_SIGNAL_NOTE]
    assert "does not mean the audio is genuine" in a.result.reasons[0]


def test_monotonic_lower_score_never_less_severe(good):
    order = {"no_signal": 0, "flagged": 1}
    prev = -1
    for s in (5.0, 1.0, 0.5, -0.5, -3.0):  # decreasing scores = more fake-like
        st = assess_audio_file(good, FakeDetector(s), CAL).result.state
        assert order[st] >= prev
        prev = order[st]


def test_uncalibrated_abstains_but_keeps_raw_score(good):
    a = assess_audio_file(good, FakeDetector(3.0), None)
    assert a.result.state == "cant_assess"
    assert a.result.score == 3.0 and a.result.threshold is None
    assert a.pred_label is None
    assert a.result.reasons[0].startswith("uncalibrated")


def test_calibration_for_other_model_is_refused(good):
    a = assess_audio_file(good, FakeDetector(3.0, model_version="other-model"), CAL)
    assert a.result.state == "cant_assess"
    assert a.result.reasons[0].startswith("calibration_model_mismatch")
    assert a.pred_label is None


def test_no_detector_abstains(good):
    a = assess_audio_file(good, None, CAL, detector_error="torch missing")
    assert a.result.state == "cant_assess"
    assert any("no_detector" in r and "torch missing" in r for r in a.result.reasons)


def test_detector_exception_becomes_cant_assess(good):
    a = assess_audio_file(good, FakeDetector(raises=True), CAL)
    assert a.result.state == "cant_assess"
    assert a.result.reasons[0].startswith("detector_error")


def test_gate_failure_product_path_has_no_score(tmp_path):
    p = write_wav(tmp_path / "short.wav", speechlike(0.4))
    a = assess_audio_file(p, FakeDetector(-5.0), CAL)
    assert a.result.state == "cant_assess" and a.result.score is None
    assert a.pred_label is None


def test_gate_failure_eval_path_keeps_state_abstain_but_gives_forced_label(tmp_path):
    p = write_wav(tmp_path / "short.wav", speechlike(0.6))
    a = assess_audio_file(p, FakeDetector(-5.0), CAL, force_score=True)
    assert a.result.state == "cant_assess"  # abstention is preserved and reported
    assert a.pred_label == "fake" and a.result.score == -5.0
    assert a.result.reasons[0].startswith("too_short")


def test_bad_inputs_never_raise(tmp_path):
    missing = assess_audio_file(tmp_path / "nope.wav", FakeDetector(), CAL)
    assert missing.result.reasons == ["file_not_found"]
    empty = tmp_path / "empty.wav"
    empty.write_bytes(b"")
    assert assess_audio_file(empty, FakeDetector(), CAL).result.reasons == ["empty_file"]
    junk = tmp_path / "junk.wav"
    junk.write_bytes(np.random.default_rng(1).bytes(5000))
    j = assess_audio_file(junk, FakeDetector(), CAL)
    assert j.result.state == "cant_assess" and j.result.reasons[0].startswith("decode_failed")
    txt = tmp_path / "chat.wav"
    txt.write_text("not audio at all")
    assert assess_audio_file(txt, FakeDetector(), CAL).result.state == "cant_assess"


def test_deterministic(good):
    a = assess_audio_file(good, FakeDetector(1.5), CAL).result
    b = assess_audio_file(good, FakeDetector(1.5), CAL).result
    assert a == b


def test_make_chunks_shapes():
    assert make_chunks(np.zeros(0, dtype=np.float32), 100) == []
    short = make_chunks(np.arange(30, dtype=np.float32), 100)
    assert len(short) == 1 and short[0].size == 100
    many = make_chunks(np.zeros(100 * 50, dtype=np.float32), 100, max_chunks=12)
    assert len(many) == 12 and all(c.size == 100 for c in many)


def test_calibration_roundtrip_and_validation(tmp_path):
    p = tmp_path / "c.json"
    save_calibration(CAL, p)
    assert load_calibration(p) == CAL
    p.write_text('{"threshold": 1.0, "polarity": "sideways", "model_version": "x"}')
    with pytest.raises(CalibrationError):
        load_calibration(p)
    with pytest.raises(CalibrationError):
        load_calibration(tmp_path / "missing.json")
    assert CAL.is_fake_side(-0.1) and not CAL.is_fake_side(0.1)
